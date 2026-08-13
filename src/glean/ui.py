"""Display utilities using Rich for CLI output."""

import threading
import time
from datetime import datetime
from types import TracebackType

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .models import ScrapedData


class _SpinnerManager:
    def __init__(self, console: Console):
        self._console = console
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, text: str):
        self.stop()
        self._stop.clear()
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        def animate():
            i = 0
            while not self._stop.is_set():
                self._console.print(
                    f"\r[cyan]{frames[i % len(frames)]} {text}[/cyan]", end=""
                )
                i += 1
                time.sleep(0.1)

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread is None:
            return
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._console.print("\r\033[K", end="")
        self._thread = None


class Spinner:
    def __init__(self, display: "Display", text: str):
        self._display = display
        self._text = text

    def __enter__(self):
        self._display.show_spinner(self._text)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        self._display.hide_spinner()


class Display:
    def __init__(self):
        self.console = Console()
        self._spinner = _SpinnerManager(self.console)

    def show_spinner(self, text: str = "Processing..."):
        self._spinner.start(text)

    def hide_spinner(self):
        self._spinner.stop()

    def spinner(self, text: str = "Processing..."):
        return Spinner(self, text)

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
            table.add_row(key, desc, detail)
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
