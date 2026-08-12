"""Interactive mode classes for the AI Web Scraper CLI."""

from abc import ABC, abstractmethod
from pathlib import Path

from .client import AIWebClient
from .models import ScrapedData
from .scraper import WebScraper
from .storage import StorageManager
from .ui import Display


class BaseMode(ABC):
    def __init__(
        self,
        client: AIWebClient,
        scraper: WebScraper,
        storage: StorageManager,
        display: Display,
    ):
        self.client = client
        self.scraper = scraper
        self.storage = storage
        self.display = display

    @abstractmethod
    def run(self) -> str | None:
        pass

    @abstractmethod
    def get_help(self) -> str:
        pass

    def _scrape_and_show(self, url: str) -> ScrapedData | None:
        self.display.show_spinner("Scraping...")
        try:
            data = self.scraper.scrape(url)
            self.display.hide_spinner()
            self.display.print_scraped_data(data, preview=True)
            return data
        except Exception as e:
            self.display.hide_spinner()
            self.display.print_box("Error", f"Scraping failed: {str(e)}", "red")
            self.display.pause()
            return None

    def _save_prompt(self, data: ScrapedData) -> str | None:
        if self.display.confirm("\nSave result?"):
            name = self.display.prompt("Filename (optional)")
            filepath = self.storage.save(data, name if name else None)
            self.display.print_box("Saved", f"Saved to: {filepath}", "green")
            return Path(filepath).name
        return None

    def _summarize_and_save(self, data: ScrapedData, saved_name: str | None = None):
        self.display.show_spinner("Generating summary...")
        content = self._prepare_content(data.content, max_chars=10000)
        messages = [
            {
                "role": "system",
                "content": "You are a web content summarizer. Provide a clear and concise summary.",
            },
            {"role": "user", "content": f"Summarize this web content:\n\n{content}"},
        ]
        summary = self.client.chat(messages)
        data.summary = summary
        self.display.print_ai_response(summary, "AI Summary")
        if saved_name:
            if self.display.confirm("Update file with summary?"):
                filepath = self.storage.save(data, saved_name)
                self.display.print_box("Saved", f"File updated: {filepath}", "green")
        else:
            if self.display.confirm("Save summary?"):
                name = self.display.prompt("Filename (optional)")
                filepath = self.storage.save(data, name if name else None)
                self.display.print_box("Saved", f"Saved to: {filepath}", "green")
        self.display.pause()

    def _prepare_content(self, content: str, max_chars: int = 15000) -> str:
        lines = content.splitlines()
        seen = set()
        deduped = []
        for line in lines:
            clean = line.strip()
            if clean and clean not in seen:
                seen.add(clean)
                deduped.append(clean)
        return "\n".join(deduped)[:max_chars]

    def _start_chat(self, data: ScrapedData) -> str | None:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant answering questions about a scraped web page. "
                    "The content is already extracted and provided to you below. "
                    "Answer questions using only this provided text. "
                    "Do not say you cannot access the page — you already have its full content."
                ),
            }
        ]
        content = self._prepare_content(data.content)
        messages.append(
            {"role": "user", "content": f"Here is the page content:\n\n{content}"}
        )
        messages.append(
            {
                "role": "assistant",
                "content": "I've analyzed the content. Ask me questions!",
            }
        )
        self.display.print_box(
            "Chat with Content",
            "Ask questions about the scraped page. Type /back to return",
            "cyan",
        )
        while True:
            question = self.display.prompt("Your question")
            if not question:
                continue
            if question.lower() == "/back":
                return None
            if question.lower() == "/exit":
                return "exit"
            self.display.show_spinner("AI thinking...")
            messages.append({"role": "user", "content": question})
            response = self.client.chat_stream(messages)
            messages.append({"role": "assistant", "content": response})
            self.display.print_ai_response(response, "Answer")


class ScrapeMode(BaseMode):
    def run(self) -> str | None:
        url = self.display.prompt("URL to scrape")
        if not url:
            return None
        data = self._scrape_and_show(url)
        if not data:
            return None
        saved_name = self._save_prompt(data)
        if self.display.confirm("\nUse AI on this content?"):
            return self._ai_menu(data, saved_name)
        return None

    def _ai_menu(self, data: ScrapedData, saved_name: str | None = None) -> str | None:
        items = [
            ("1", "AI Summary", "Generate a concise summary of the page"),
            ("2", "Chat with Content", "Ask questions about the scraped content (RAG)"),
            ("0", "Back", "Return to main menu"),
        ]
        self.display.print_menu("AI Menu", items, "magenta")
        choice = self.display.prompt("Choice (0-2, q to quit)")
        if choice in ("0", "q", "quit", "exit"):
            return None
        if choice == "1":
            self._summarize_and_save(data, saved_name)
            return None
        if choice == "2":
            return self._start_chat(data)
        return None

    def get_help(self) -> str:
        return "Simple URL scraping.\n\nCommands:\n  /help  - This help\n  /exit  - Quit\n  /clear - Clear screen"


class SummarizeMode(BaseMode):
    def run(self) -> str | None:
        url = self.display.prompt("URL to summarize")
        if not url:
            return None
        data = self._scrape_and_show(url)
        if not data:
            return None
        self._summarize_and_save(data)
        return None

    def get_help(self) -> str:
        return "Automatic page summary.\n\nCommands:\n  /help  - This help\n  /exit  - Quit"


class ChatMode(BaseMode):
    def run(self) -> str | None:
        url = self.display.prompt("URL for RAG conversation")
        if not url:
            return None
        data = self._scrape_and_show(url)
        if not data:
            return None
        return self._start_chat(data)

    def get_help(self) -> str:
        return "Conversation with scraped content (RAG).\n\nCommands:\n  /back  - Back to menu\n  /exit  - Quit\n  /help  - This help"


class ConfigMode(BaseMode):
    def run(self) -> str | None:
        from .config import get_save_dir, load_config, load_settings

        cfg = load_config()
        settings = load_settings()
        save_dir = get_save_dir()
        key_display = "****" if cfg["api_key"] else "not set"

        text = (
            f"\nCurrent Configuration:\n\n"
            f"API:\n"
            f"   - Base URL: {cfg['base_url']}\n"
            f"   - Model: {cfg['model']}\n"
            f"   - API Key: {key_display}\n"
            f"   - Temperature: {cfg['temperature']}\n\n"
            f"Scraping:\n"
            f"   - Timeout: {settings['request_timeout']}s\n"
            f"   - Max Content: {settings['max_content_length']} bytes\n\n"
            f"Storage:\n"
            f"   - Directory: {save_dir}\n"
        )
        self.display.print_box("Configuration", text, "cyan")
        if self.display.confirm("\nChange settings?"):
            self.display.print_box(
                "Info", "Edit the .env file to change configuration", "yellow"
            )
        self.display.pause()
        return None

    def get_help(self) -> str:
        return "View and modify configuration.\n\nCommands:\n  /help  - This help\n  /exit  - Quit"
