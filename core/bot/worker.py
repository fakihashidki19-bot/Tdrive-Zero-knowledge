"""
TDrive Telegram Bot Worker.

Listens for commands via the Telegram Bot API and executes 
actions via the BotBridge.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict
from telethon import TelegramClient, events, functions, types
from core.session import SessionManager
from core.bot.bridge import BotBridge
from core.feature_registry import FeatureRegistry, FeatureID

logger = logging.getLogger(__name__)

class TDriveBotWorker:
    def __init__(self, sm: SessionManager):
        self.sm = sm
        self.bridge = BotBridge(sm)
        self.registry = FeatureRegistry(sm)
        self.client = None
        self.username = None
        self._running = False
        self.payload_registry: Dict[str, str] = {} 

    def _register_payload(self, payload: str) -> str:
        """Registers a payload and returns a short ID (8 chars)."""
        for kid, val in self.payload_registry.items():
            if val == payload:
                return kid
        
        reg_id = uuid.uuid4().hex[:8]
        self.payload_registry[reg_id] = payload
        return reg_id

    def _get_payload(self, reg_id: str) -> Optional[str]:
        """Retrieves payload from registry."""
        return self.payload_registry.get(reg_id)

    def validate_callback_data(self, data: bytes) -> bool:
        """
        Validates if callback data is safe for Telegram.
        Rules: max 64 bytes, ASCII only.
        """
        if len(data) > 64:
            logger.warning(f"[BOT WARNING] invalid_callback_data=too_long bytes={len(data)}")
            return False
        
        try:
            data.decode('ascii')
        except UnicodeDecodeError:
            logger.warning(f"[BOT WARNING] invalid_callback_data=non_ascii data={data!r}")
            return False
            
        return True

    def _is_uuid(self, val: str) -> bool:
        """Checks if a string is a UUID."""
        return len(val) == 36 and val.count("-") == 4

    def is_connected(self) -> bool:
        """Returns True if the bot client is connected and authorized."""
        return self.client and self.client.is_connected() and self._running

    async def _register_commands(self):
        """Registers bot commands with Telegram (Bot Menu)."""
        if not self.client:
            return
            
        logger.info("BotWorker: Registering commands with Telegram...")
        commands = [
            types.BotCommand(command="start", description="Initialize TDrive Bot"),
            types.BotCommand(command="list", description="Browse files"),
            types.BotCommand(command="search", description="Search files by name"),
            types.BotCommand(command="download", description="Generate download ticket"),
            types.BotCommand(command="trash", description="View deleted files"),
            types.BotCommand(command="restore", description="Restore file from trash"),
            types.BotCommand(command="status", description="Check system health"),
            types.BotCommand(command="help", description="Show help menu"),
        ]
        
        try:
            await self.client(functions.bots.SetBotCommandsRequest(
                commands=commands,
                scope=types.BotCommandScopeDefault(),
                lang_code=""
            ))
            logger.info("BotWorker: Bot commands registered successfully.")
        except Exception as e:
            logger.error(f"BotWorker: Failed to register commands: {e}")

    async def _send_list(self, event, path, page=1, edit=False):
        """Helper to fetch and display file list with buttons."""
        if path and path != "/" and not path.startswith("/") and not self._is_uuid(path):
            orig_path = path
            path = f"/{path}"
            logger.info(f"[BOT] path_normalized: {orig_path} -> {path}")

        result = await self.bridge.handle_list_files(path, page=page)
        
        if not result["success"]:
            msg = f"❌ **Error:** `{result.get('error')}`"
            if edit: await event.edit(msg)
            else: await event.respond(msg)
            return

        files = result["data"]
        current_path = result["path"]
        display_name = result["display_name"]
        pagination = result["pagination"]
        
        if not files and page == 1:
            msg = f"📂 **Folder:** `{display_name}`\n`({current_path})`\n\n_This folder is empty._"
            if edit: await event.edit(msg)
            else: await event.respond(msg)
            return

        msg = f"📂 **Folder:** `{display_name}`\n`({current_path})`"
        
        buttons = []
        for f in files:
            if f["is_folder"]:
                target_folder = f"{current_path.rstrip('/')}/{f['filename']}"
                reg_id = self._register_payload(target_folder)
                
                cb_data = f"list:{reg_id}:1".encode()
                if self.validate_callback_data(cb_data):
                    buttons.append([types.KeyboardButtonCallback(
                        text=f"📁 {f['filename']}",
                        data=cb_data
                    )])
            else:
                size_str = self._format_size(f["size"])
                reg_id = self._register_payload(f['file_id'])
                
                cb_data = f"download:{reg_id}".encode()
                if self.validate_callback_data(cb_data):
                    buttons.append([types.KeyboardButtonCallback(
                        text=f"⬇️ {f['filename']} ({size_str})",
                        data=cb_data
                    )])

        nav_buttons = []
        if pagination["total_pages"] > 1:
            path_id = self._register_payload(current_path)
            
            if pagination["current_page"] > 1:
                prev_data = f"list:{path_id}:{pagination['current_page'] - 1}".encode()
                if self.validate_callback_data(prev_data):
                    nav_buttons.append(types.KeyboardButtonCallback(
                        text="⬅️ Previous",
                        data=prev_data
                    ))
            
            nav_buttons.append(types.KeyboardButtonCallback(
                text=f"📄 {pagination['current_page']}/{pagination['total_pages']}",
                data=b"noop"
            ))

            if pagination["current_page"] < pagination["total_pages"]:
                next_data = f"list:{path_id}:{pagination['current_page'] + 1}".encode()
                if self.validate_callback_data(next_data):
                    nav_buttons.append(types.KeyboardButtonCallback(
                        text="Next ➡️",
                        data=next_data
                    ))
        
        if nav_buttons:
            buttons.append(nav_buttons)

        max_cb_bytes = max([len(b[0].data) for b in buttons if hasattr(b[0], 'data')] + [0])
        logger.info(f"[BOT] folder={current_path} items={len(files)} buttons={len(buttons)} page={page} callback_bytes={max_cb_bytes}")

        try:
            if edit:
                await event.edit(msg, buttons=buttons)
            else:
                await event.respond(msg, buttons=buttons)
        except Exception as e:
            logger.error(f"BotWorker: Failed to send list: {e}")
            if "ButtonDataInvalidError" in str(e):
                await event.respond("⚠️ **Error:** Telegram rejected the button data. Please contact administrator.")

    async def start(self):
        """Starts the bot client."""
        config = self.sm.load_config()
        bot_token = config.get("bot_token")
        
        if not bot_token:
            logger.warning("BotWorker: No bot_token found in config. Bot will not start.")
            self.username = None
            return

        if not self.registry.is_enabled(FeatureID.BOT_INTERFACE):
            logger.info("BotWorker: Bot Interface is disabled in settings.")
            self.username = None
            return

        logger.info("BotWorker: Starting Telegram Bot...")
        
        self.client = TelegramClient(
            str(self.sm.config_dir / "tdrive_bot.session"),
            config["api_id"],
            config["api_hash"]
        )

        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await event.respond(
                "👋 **Welcome to TDrive Personal Bot!**\n\n"
                "I am your secure gateway to your files on Telegram.\n\n"
                "**Commands:**\n"
                "📂 `/list` - Browse root files\n"
                "🔍 `/search <query>` - Find a file\n"
                "📊 `/status` - Check Agent health\n"
                "🗑️ `/trash` - View deleted items\n"
                "❓ `/help` - Show all commands"
            )

        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            await event.respond(
                "📖 **TDrive Bot Help**\n\n"
                "📂 `/list [path]` - List files in a path\n"
                "🔍 `/search <query>` - Search for files\n"
                "📥 `/download <file_id>` - Get a download ticket\n"
                "🗑️ `/trash` - List items in trash bin\n"
                "♻️ `/restore <file_id>` - Restore item from trash\n"
                "📊 `/status` - System health check\n"
                "🚀 `/start` - Restart welcome message"
            )

        @self.client.on(events.NewMessage(pattern='/status'))
        async def status_handler(event):
            status = await self.bridge.handle_system_status()
            if status["success"]:
                msg = (
                    f"🖥️ **System Status:**\n"
                    f"• State: `{status['state']}`\n"
                    f"• Access: `{status['mode']}`\n"
                    f"• Info: {status['message']}"
                )
                await event.respond(msg)
            else:
                await event.respond(f"❌ Error: {status.get('error')}")

        @self.client.on(events.NewMessage(pattern='/list'))
        async def list_handler(event):
            parts = event.message.text.split(' ', 1)
            path = parts[1] if len(parts) > 1 else "/"
            await self._send_list(event, path, page=1)

        @self.client.on(events.CallbackQuery(data=lambda x: x.decode().startswith('list:')))
        async def list_callback_handler(event):
            data = event.data.decode().split(':')
            reg_id = data[1]
            page = int(data[2])
            
            path = self._get_payload(reg_id)
            if not path:
                logger.warning(f"[BOT] list_callback: reg_id {reg_id} not found in registry")
                await event.answer("⚠️ Session expired or folder not found. Please use /list again.", alert=True)
                return

            await self._send_list(event, path, page=page, edit=True)

        @self.client.on(events.CallbackQuery(data=lambda x: x.decode().startswith('download:')))
        async def download_callback_handler(event):
            reg_id = event.data.decode().split(':')[1]
            file_id = self._get_payload(reg_id)
            
            if not file_id:
                logger.warning(f"[BOT] download_callback: reg_id {reg_id} not found in registry")
                await event.answer("⚠️ Session expired or file not found.", alert=True)
                return

            result = self.bridge.generate_secure_ticket(file_id)
            if result["success"]:
                await event.answer(f"Ticket: {result['ticket']}", alert=True)
            else:
                await event.answer(f"Error: {result.get('error')}", alert=True)

        @self.client.on(events.CallbackQuery(data=b'noop'))
        async def noop_callback_handler(event):
            await event.answer()

        @self.client.on(events.NewMessage(pattern='/trash'))
        async def trash_handler(event):
            result = await self.bridge.handle_list_trash()
            if not result["success"]:
                await event.respond(f"❌ Error: {result.get('error')}")
                return
            files = result["data"]
            if not files:
                await event.respond("🗑️ **Trash Bin is empty.**")
                return
            msg = "🗑️ **Deleted Items:**\n\n"
            for f in files:
                icon = "📁" if f["is_folder"] else "📄"
                msg += f"{icon} `{f['filename']}`\n"
                msg += f"   └ ID: `{f['file_id'][:8]}...` (Restore with `/restore {f['file_id'][:8]}`)\n"
            if len(msg) > 4000:
                msg = msg[:4000] + "\n\n_...list truncated_"
            await event.respond(msg)

        @self.client.on(events.NewMessage(pattern='/search'))
        async def search_handler(event):
            parts = event.message.text.split(' ', 1)
            if len(parts) < 2:
                await event.respond("🔍 Usage: `/search <query>`")
                return
            query = parts[1]
            result = await self.bridge.handle_search_files(query)
            if not result["success"]:
                await event.respond(f"❌ Error: {result.get('error')}")
                return
            files = result["data"]
            if not files:
                await event.respond(f"🔍 No files found matching `{query}`.")
                return
            msg = f"🔍 **Search Results for** `{query}`:\n\n"
            for f in files:
                icon = "📁" if f["is_folder"] else "📄"
                msg += f"{icon} `{f['filename']}`\n"
                msg += f"   └ Path: `{f['virtual_path']}`\n"
                msg += f"   └ ID: `{f['file_id'][:8]}...`\n"
            if len(msg) > 4000:
                msg = msg[:4000] + "\n\n_...list truncated_"
            await event.respond(msg)

        @self.client.on(events.NewMessage(pattern='/restore'))
        async def restore_handler(event):
            parts = event.message.text.split(' ', 1)
            if len(parts) < 2:
                await event.respond("♻️ Usage: `/restore <file_id>`")
                return
            file_id_prefix = parts[1]
            trash_result = await self.bridge.handle_list_trash()
            if not trash_result["success"]:
                await event.respond(f"❌ Error: {trash_result.get('error')}")
                return
            target_id = None
            for f in trash_result["data"]:
                if f["file_id"].startswith(file_id_prefix):
                    target_id = f["file_id"]
                    break
            if not target_id:
                await event.respond(f"❌ File ID `{file_id_prefix}` not found in trash.")
                return
            result = await self.bridge.handle_restore_file(target_id)
            if result["success"]:
                await event.respond(f"✅ **Restored:** `{target_id[:8]}...` has been returned to its original location.")
            else:
                await event.respond(f"❌ Error: {result.get('error')}")

        @self.client.on(events.NewMessage(pattern='/download'))
        async def download_handler(event):
            parts = event.message.text.split(' ', 1)
            if len(parts) < 2:
                await event.respond("📥 Usage: `/download <file_id>`")
                return
            file_id = parts[1]
            result = self.bridge.generate_secure_ticket(file_id)
            if result["success"]:
                await event.respond(
                    f"📥 **Download Ticket Generated**\n\n"
                    f"Ticket: `{result['ticket']}`\n\n"
                    f"_Note: This is a stub._"
                )
            else:
                await event.respond(f"❌ Error: {result.get('error')}")

        try:
            await self.client.start(bot_token=bot_token)
            me = await self.client.get_me()
            self.username = me.username
            self._running = True
            logger.info(f"BotWorker: Bot @{self.username} is now online.")
            await self._register_commands()
            await self.client.run_until_disconnected()
        except Exception as e:
            logger.error(f"BotWorker: Critical error: {e}")
            self.username = None
        finally:
            self._running = False
            self.username = None

    def _format_size(self, size: int) -> str:
        """Helper to format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    async def stop(self):
        """Stops the bot client."""
        if self.client:
            await self.client.disconnect()
            self._running = False
            self.username = None
