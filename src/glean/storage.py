"""Storage manager for saving and loading scraped data."""

import json
import time
from datetime import datetime
from pathlib import Path

from .config import get_save_dir
from .models import ScrapedData


class StorageManager:
    def __init__(self):
        self.save_dir = get_save_dir()
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save(self, data: ScrapedData, name: str | None = None) -> str:
        if not name:
            name = f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        if not name.endswith(".json"):
            name += ".json"
        safe_name = Path(name).name
        filepath = self.save_dir / safe_name
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data_dict = {
            "url": data.url,
            "title": data.title,
            "content": data.content,
            "images": data.images,
            "links": data.links,
            "metadata": data.metadata,
            "scraped_at": data.scraped_at,
            "summary": data.summary,
        }
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        return str(filepath)

    def load(self, name: str) -> ScrapedData | None:
        if not name.endswith(".json"):
            name += ".json"
        filepath = self.save_dir / Path(name).name
        if not filepath.exists():
            return None
        try:
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        return ScrapedData(
            url=data.get("url", ""),
            title=data.get("title", "Untitled"),
            content=data.get("content", ""),
            images=data.get("images", []),
            links=data.get("links", []),
            metadata=data.get("metadata", {}),
            scraped_at=data.get("scraped_at", time.time()),
            summary=data.get("summary"),
        )
