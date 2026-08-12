"""Display utilities using Rich for CLI output."""

import threading
import time
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .models import ScrapedData


class Display:
    def __init__(self):
        self.console = Console()
        self._spinner_stop = threading.Event()
        self._spinner_thread: threading.Thread | None = None

    def clear_line(self):
        self.console.print("\r\033[K", end="")

    def show_spinner(self, text: str = "Processing..."):
        self._spinner_stop.clear()
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def animate():
            i = 0
            while not self._spinner_stop.is_set():
                self.console.print(
                    f"\r[cyan]{frames[i % len(frames)]} {text}[/cyan]", end=""
                )
                i += 1
                time.sleep(0.1)

        self._spinner_thread = threading.Thread(target=animate, daemon=True)
        self._spinner_thread.start()

    def hide_spinner(self):
        if self._spinner_thread is None:
            return
        self._spinner_stop.set()
        if self._spinner_thread.is_alive():
            self._spinner_thread.join(timeout=0.5)
        self.clear_line()
        self._spinner_thread = None

    def print_box(self, title: str, content: str = "", style: str = "cyan"):
        if content:
            text = Text()
            text.append(f"{title}\n", style=f"bold {style}")
            text.append(content, style="white")
        else:
            text = Text(title, style=f"bold {style}")
        self.console.print(Panel(text, border_style=style, box=box.ROUNDED))

    def print_menu(
        self, title: str, items: list[tuple[str, str, str]], style: str = "cyan"
    ):
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="bold yellow")
        table.add_column(style="white")
        table.add_column(style="dim cyan")
        for key, desc, detail in items:
            table.add_row(
                f"[bold yellow]{key}[/bold yellow]",
                f"[white]{desc}[/white]",
                f"[dim cyan]{detail}[/dim cyan]",
            )
        self.console.print(
            Panel(table, title=title, border_style=style, box=box.ROUNDED)
        )

    def prompt(self, text: str) -> str:
        try:
            return Prompt.ask(f"[bold yellow]{text}[/bold yellow]")
        except Exception:
            try:
                return input(f"{text} ").strip()
            except EOFError:
                return ""

    def pause(self, text: str = "\nPress Enter...") -> None:
        try:
            input(text)
        except EOFError:
            return

    def confirm(self, text: str) -> bool:
        try:
            return Confirm.ask(f"[bold yellow]{text}[/bold yellow]")
        except Exception:
            try:
                answer = input(f"{text} [y/N] ").strip().lower()
            except EOFError:
                return False
            return answer in ("y", "yes", "1")

    def print_ai_response(self, response: str, title: str = "AI"):
        self.hide_spinner()
        print()
        self.console.print(
            Panel(
                response,
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    def print_scraped_data(self, data: ScrapedData, preview: bool = True):
        content_preview = (
            data.content[:500] + "..."
            if preview and len(data.content) > 500
            else data.content
        )
        text = Text()
        text.append(f"URL: {data.url}\n", style="cyan")
        text.append(f"Title: {data.title}\n", style="bold green")
        text.append(
            f"Scraped: {datetime.fromtimestamp(data.scraped_at).strftime('%Y-%m-%d %H:%M:%S')}\n",
            style="yellow",
        )
        text.append(f"\nContent ({len(data.content)} chars):\n", style="bold white")
        text.append(content_preview, style="white")
        if data.images:
            text.append(f"\n\nImages ({len(data.images)}):", style="bold magenta")
        if data.links:
            text.append(f"\nLinks ({len(data.links)})", style="bold blue")
        if data.summary:
            text.append("\n\nAI Summary:\n", style="bold cyan")
            text.append(
                data.summary[:300] + "..." if len(data.summary) > 300 else data.summary,
                style="cyan",
            )
        self.console.print(Panel(text, border_style="green", box=box.ROUNDED))
