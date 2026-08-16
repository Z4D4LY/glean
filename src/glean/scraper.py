"""Web scraper using requests and BeautifulSoup."""

import re
import time
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ftfy import fix_text
from markdownify import markdownify as markdownify_html

from .config import load_settings
from .exceptions import ScraperError
from .models import ScrapedData

_MAX_IMAGES = 20
_MAX_LINKS = 50
_NOISE_TAGS = [
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "button",
]
_NOISE_WORDS = [
    "cookie",
    "popup",
    "modal",
    "navbar",
    "menu",
    "footer",
    "header",
    "subscribe",
    "newsletter",
    "signup",
    "login",
    "loading",
    "advert",
    "sponsored",
    "sidebar",
    "breadcrumb",
    "pagination",
    "floating",
    "cursor",
    "w-nav",
    "w-form",
    "skip",
    "sr-only",
    "screen-reader",
    "visually-hidden",
]


class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )

    def scrape(self, url: str) -> ScrapedData:
        settings = load_settings()
        try:
            response = self.session.get(url, timeout=settings["request_timeout"])
            response.raise_for_status()
            html = response.text or ""
        except requests.RequestException as e:
            raise ScraperError(str(e)) from e

        if len(html) > settings["max_content_length"]:
            html = html[: settings["max_content_length"]]

        html = fix_text(html)

        soup = BeautifulSoup(html, "html.parser")
        metadata = self._extract_metadata(soup)
        title = self._extract_title(soup)
        images = self._extract_images(soup, url)
        links = self._extract_links(soup, url)

        self._remove_noise(soup)
        content = self._extract_markdown(soup)

        return ScrapedData(
            url=url,
            title=title,
            content=content,
            images=images,
            links=links,
            metadata=metadata,
            scraped_at=time.time(),
        )

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for tag in ["description", "keywords", "author", "robots"]:
            meta = soup.find("meta", attrs={"name": tag})
            if meta and meta.get("content"):
                metadata[tag] = meta["content"]
        for tag in ["title", "description", "image", "url"]:
            meta = soup.find("meta", attrs={"property": f"og:{tag}"})
            if meta and meta.get("content"):
                metadata[f"og:{tag}"] = meta["content"]
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.text.strip()
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag["lang"]
        return metadata

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find("title")
        return title_tag.text.strip() if title_tag else "Untitled"

    def _remove_noise(self, soup: BeautifulSoup) -> None:
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        tags_to_remove: list[Any] = []
        for tag in soup.find_all(True):
            class_value = tag.get("class")
            id_value = tag.get("id") or ""
            if isinstance(class_value, list):
                class_text = " ".join(class_value).lower()
            elif class_value:
                class_text = str(class_value).lower()
            else:
                class_text = ""
            combined = f"{class_text} {str(id_value).lower()}"
            if any(word in combined for word in _NOISE_WORDS):
                tags_to_remove.append(tag)
        for tag in tags_to_remove:
            tag.decompose()

    def _extract_markdown(self, soup: BeautifulSoup) -> str:
        body = soup.body if soup.body else soup
        markdown_text = markdownify_html(str(body), heading_style="ATX", bullets="-")
        markdown_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown_text)
        markdown_text = re.sub(r"\[\]\([^)]*\)", "", markdown_text)
        markdown_text = re.sub(
            r"\[([^\]]*)\]\((?:#|javascript:)[^)]*\)", r"\1", markdown_text
        )
        markdown_text = re.sub(r' "(?:[^"\\]|\\.)*"\)', ")", markdown_text)
        markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text)
        return fix_text(markdown_text).strip()

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        images: list[str] = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            src = str(src).strip()
            if src.startswith("data:"):
                continue
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            if src not in images:
                images.append(src)
        return images[:_MAX_IMAGES]

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            if not href.startswith("http"):
                href = urljoin(base_url, href)
            if href not in links:
                links.append(href)
        return links[:_MAX_LINKS]
