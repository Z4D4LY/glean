"""Web scraper using requests and BeautifulSoup."""

import time
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import load_settings
from .models import ScrapedData


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
            if len(html) > settings["max_content_length"]:
                html = html[: settings["max_content_length"]]

            soup = BeautifulSoup(html, "html.parser")
            metadata = self._extract_metadata(soup)
            title, content = self._extract_text_content(soup)

            images = self._extract_images(soup, url)
            links = self._extract_links(soup, url)

            return ScrapedData(
                url=url,
                title=title,
                content=content,
                images=images,
                links=links,
                metadata=metadata,
                scraped_at=time.time(),
            )

        except requests.RequestException as e:
            raise Exception(f"Scraping error: {str(e)}") from e

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        metadata = {}
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

    def _extract_text_content(self, soup: BeautifulSoup) -> tuple[str, str]:
        title_tag = soup.find("title")
        title = title_tag.text.strip() if title_tag else "Untitled"
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        content = self._extract_by_tags(soup, "p")
        if not content:
            content = self._extract_by_tags(
                soup, ["div", "article", "section", "td", "li", "blockquote", "span", "pre"]
            )
        if not content:
            content = soup.get_text(separator="\n")
            content = "\n".join(line.strip() for line in content.splitlines() if line.strip())
        headings = soup.find_all(["h1", "h2", "h3"])
        headings_text = "\n".join(
            f"{h.name.upper()}: {h.get_text().strip()}"
            for h in headings
            if h.get_text().strip()
        )
        if headings_text:
            content = f"{headings_text}\n\n{content}"
        return title, content

    @staticmethod
    def _extract_by_tags(soup, tag_names) -> str:
        tags = soup.find_all(tag_names)
        return "\n".join(
            t.get_text().strip() for t in tags if t.get_text().strip()
        )

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        images = []
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
        return images[:20]

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links = []
        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            if not href.startswith("http"):
                href = urljoin(base_url, href)
            if href not in links:
                links.append(href)
        return links[:50]
