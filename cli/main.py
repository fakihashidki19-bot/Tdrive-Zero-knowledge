"""
TDrive CLI Entry Point.
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cli.commands import init, login, upload, download, ls, rm, doctor, maintenance, backup

console = Console()

app = typer.Typer(
    help="TDrive: Telegram-Backend Personal Cloud Storage",
    rich_markup_mode="rich"
)

from core.session import SessionManager
try:
    SessionManager().cleanup_tmp()
except Exception:
    pass

# Add command groups
app.add_typer(init.app, name="init")
app.add_typer(login.app, name="login")
app.add_typer(ls.app, name="ls")
app.add_typer(doctor.app, name="doctor")
app.add_typer(maintenance.app, name="maintenance")
app.add_typer(backup.app, name="backup")

@app.command(name="upload")
def upload_cmd(
    path: str = typer.Argument(..., help="Path to file or folder"),
    virtual_path: str = typer.Option("/", "--vpath", help="Virtual folder path in TDrive")
):
    """[bold green]Upload[/bold green] a file to TDrive."""
    asyncio.run(upload.handle_upload(path, virtual_path))

@app.command(name="download")
def download_cmd(
    file_id: str = typer.Argument(..., help="File ID or SHA256"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path")
):
    """[bold blue]Download[/bold blue] a file from TDrive."""
    asyncio.run(download.handle_download(file_id, output))

@app.command(name="rm")
def rm_cmd(file_id: str = typer.Argument(..., help="File ID to delete")):
    """[bold red]Remove[/bold red] a file from TDrive and Telegram."""
    asyncio.run(rm.handle_rm(file_id))

@app.command(name="verify-instance")
def verify_instance_cmd(
    reset: bool = typer.Option(False, "--reset", help="Force regenerate the instance fingerprint lock")
):
    """[bold cyan]Authorize[/bold cyan] the current environment/instance."""
    from core.integrity import IntegrityGuard
    guard = IntegrityGuard()
    
    status = guard.get_integrity_status()
    if status["state"] == "FULL_ACCESS" and not reset:
        console.print("[bold green]Instance is already verified and authorized.[/bold green]")
        return

    if guard.is_ci_environment():
        console.print("[bold yellow]Warning:[/bold yellow] CI environment detected. Manual verification is temporary.")
    
    password = typer.prompt("Enter Master Password to authorize this machine", hide_input=True)
    
    if guard.verify_instance(password, reset=reset):
        console.print("[bold green]Success![/bold green] Instance fingerprint verified and locked.")
        console.print("[dim]This machine is now authorized to perform write operations.[/dim]")
    else:
        console.print("[bold red]Error:[/bold red] Verification failed. Check your password or run 'tdrive init' first.")

if __name__ == "__main__":
    app()
