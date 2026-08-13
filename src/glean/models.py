"""Data models for the Glean."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScrapedData:
    url: str
    title: str
    content: str
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    scraped_at: float = field(default_factory=time.time)
    summary: str | None = None


@dataclass
class Mode:
    key: str
    name: str
    description: str


MODES = [
    Mode(
        key="scrape", name="Simple Scraping", description="Extract content from a URL"
    ),
    Mode(key="summarize", name="AI Summary", description="Automatic page summary"),
    Mode(key="chat", name="Chat with Content", description="RAG conversation"),
    Mode(key="config", name="Configuration", description="Scraper settings"),
]
