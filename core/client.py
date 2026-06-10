"""
TDrive Telegram Client Wrapper.

Provides a secure and resilient interface to Telethon,
implementing rate limiting, retries, and error handling.
"""

import asyncio
import logging
import random
from pathlib import Path
from typing import Any, Optional, Union

from telethon import TelegramClient, errors
from telethon.tl.types import Message

from core.transmission.ratelimiter import RateLimiter

logger = logging.getLogger(__name__)

class TelegramError(Exception):
    """Base exception for Telegram operations."""
    pass

class TDriveClient:
    """
    Wrapper for Telethon Client with TDrive-specific safety and logic.
    """

    def __init__(
        self,
        session_path: Path,
        api_id: int,
        api_hash: str,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initializes the TDriveClient.
        """
        self.client = TelegramClient(str(session_path), api_id, api_hash)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def connect(self):
        """Connects to Telegram."""
        if not self.client.is_connected():
            await self.client.connect()

    async def disconnect(self):
        """Disconnects from Telegram."""
        await self.client.disconnect()

    async def is_user_authorized(self) -> bool:
        """Checks if the user is authorized."""
        return await self.client.is_user_authorized()

    async def _execute_with_retry(self, func, *args, **kwargs):
        """
        Executes a Telethon function with FloodWait handling and exponential backoff.
        """
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with self.rate_limiter.semaphore:
                    await self.rate_limiter.wait()
                    return await func(*args, **kwargs)
            except errors.FloodWaitError as e:
                logger.warning(f"FloodWait encountered. Sleeping for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except (errors.RpcMcgetFailError, errors.ServerError) as e:
                if attempt == max_retries - 1:
                    raise TelegramError(f"Telegram server error after {max_retries} attempts: {str(e)}")
                
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Telegram server error. Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected Telegram error: {str(e)}")
                raise TelegramError(str(e))

    async def send_document(
        self,
        entity: Union[str, int],
        file: Union[str, bytes, Path],
        caption: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> Message:
        """
        Uploads a document to a Telegram entity.
        """
        return await self._execute_with_retry(
            self.client.send_file,
            entity,
            file,
            caption=caption,
            progress_callback=progress_callback
        )

    async def download_document(
        self,
        message: Message,
        file: Union[str, Path],
        progress_callback: Optional[Any] = None
    ) -> str:
        """
        Downloads a document from a Telegram message.
        """
        return await self._execute_with_retry(
            self.client.download_media,
            message,
            file=file,
            progress_callback=progress_callback
        )

    async def get_message(self, entity: Union[str, int], message_id: int) -> Optional[Message]:
        """
        Retrieves a message by ID.
        """
        messages = await self._execute_with_retry(
            self.client.get_messages,
            entity,
            ids=message_id
        )
        return messages

    async def delete_messages(self, entity: Union[str, int], message_ids: list[int]):
        """
        Deletes messages from a Telegram entity.
        """
        await self._execute_with_retry(
            self.client.delete_messages,
            entity,
            message_ids
        )

    async def validate_channel(self, entity: Union[str, int]) -> bool:
        """
        Verifies that the entity (channel) exists and is accessible.
        """
        try:
            await self._execute_with_retry(self.client.get_entity, entity)
            return True
        except Exception as e:
            logger.error(f"Channel validation failed for {entity}: {str(e)}")
            return False
