"""Main application controller."""

from .client import WebClient
from .models import MODES
from .modes import ChatMode, ConfigMode, ScrapeMode, SummarizeMode
from .scraper import WebScraper
from .storage import StorageManager
from .ui import Display


class Glean:
    def __init__(self):
        self.display = Display()
        self.client = WebClient()
        self.scraper = WebScraper()
        self.storage = StorageManager()

        self.modes = {
            "scrape": ScrapeMode(
                client=self.client,
                scraper=self.scraper,
                storage=self.storage,
                display=self.display,
            ),
            "summarize": SummarizeMode(
                client=self.client,
                scraper=self.scraper,
                storage=self.storage,
                display=self.display,
            ),
            "chat": ChatMode(
                client=self.client,
                scraper=self.scraper,
                storage=self.storage,
                display=self.display,
            ),
            "config": ConfigMode(
                client=self.client,
                scraper=self.scraper,
                storage=self.storage,
                display=self.display,
            ),
        }
        self.running = True

    def run(self):
        self._print_welcome()
        while self.running:
            self._main_menu()

    def _print_welcome(self):
        from rich.panel import Panel
        from rich.text import Text

        text = Text()
        text.append("GLEAN\n\n", style="bold cyan")
        text.append("Welcome! Choose a mode below:\n", style="white")
        self.display.console.print(Panel(text, border_style="cyan"))

    def _main_menu(self):
        items = [
            (str(i + 1), mode.name, mode.description) for i, mode in enumerate(MODES)
        ]
        items.append(("0", "Quit", "Exit the application"))
        max_opt = len(MODES)
        self.display.print_menu("MAIN MENU", items, "cyan")
        choice = self.display.prompt(f"Your choice (0-{max_opt}, q to quit)")
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
