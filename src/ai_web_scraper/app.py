"""Main application controller."""

from .client import AIWebClient
from .models import MODES
from .modes import ChatMode, ConfigMode, ScrapeMode, SummarizeMode
from .scraper import WebScraper
from .storage import StorageManager
from .ui import Display


class AIWebScraper:
    def __init__(self):
        self.display = Display()
        self.client = AIWebClient()
        self.scraper = WebScraper()
        self.storage = StorageManager()

        shared = [self.client, self.scraper, self.storage, self.display]
        self.modes = {
            "scrape": ScrapeMode(*shared),
            "summarize": SummarizeMode(*shared),
            "chat": ChatMode(*shared),
            "config": ConfigMode(*shared),
        }
        self.running = True

    def run(self):
        self._print_welcome()
        while self.running:
            self._main_menu()

    def _print_welcome(self):
        from rich import box
        from rich.panel import Panel
        from rich.text import Text

        text = Text()
        text.append("╔══════════════════════════════════════════╗\n")
        text.append("║   AI WEB SCRAPER                       ║\n", style="bold cyan")
        text.append("╚══════════════════════════════════════════╝\n")
        text.append("\nWelcome! Choose a mode below:\n", style="white")
        self.display.console.print(Panel(text, border_style="cyan", box=box.DOUBLE))

    def _main_menu(self):
        items = [
            (str(i + 1), mode.name, mode.description) for i, mode in enumerate(MODES)
        ]
        items.append(("0", "Quit", "Exit the application"))
        self.display.print_menu("MAIN MENU", items, "cyan")
        choice = self.display.prompt("Your choice (0-4, q to quit)")
        if choice in ("0", "q", "quit", "exit"):
            self.display.print_box("Goodbye", "See you soon!", "green")
            self.running = False
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(MODES):
                result = self.modes[MODES[idx].key].run()
                if result == "exit":
                    self.running = False
            else:
                self.display.print_box("Error", "Invalid choice", "red")
                self.display.pause()
        except ValueError:
            self.display.print_box("Error", "Invalid choice", "red")
            self.display.pause()
