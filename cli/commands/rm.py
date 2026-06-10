import typer
from rich.console import Console
from core.session import SessionManager
from core.db.session import DatabaseSession
from core.db.manager import DBManager
from core.client import TDriveClient

console = Console()

async def handle_rm(file_id: str):
    sm = SessionManager()
    config = sm.load_config()
    if not config:
        console.print("[red]Error: TDrive not initialized.[/red]")
        return

    db_path = sm.config_dir / "tdrive.db"
    db_session = DatabaseSession(str(db_path))
    
    tg_client = TDriveClient(
        sm.config_dir / "tdrive.session", 
        config["api_id"], 
        config["api_hash"]
    )
    
    await tg_client.connect()
    
    try:
        with db_session.get_session() as session:
            db = DBManager(session)
            file_record = db.get_file(file_id)
            if not file_record:
                console.print(f"[red]File {file_id} not found.[/red]")
                return
            
            chunks = db.get_chunks(file_id)
            msg_ids = [c.msg_id for c in chunks]
            
            if msg_ids:
                console.print(f"Deleting {len(msg_ids)} chunks from Telegram...")
                await tg_client.delete_messages(config["channel_id"], msg_ids)
            
            db.delete_file(file_id)
            console.print("[bold green]File successfully removed.[/bold green]")
            
    except Exception as e:
        console.print(f"[red]Error during removal: {str(e)}[/red]")
    finally:
        await tg_client.disconnect()
