#!/usr/bin/env python3
"""Unit tests for glean.

These tests run fully offline: the network layer and the LLM client are
mocked, so no live HTTP request or API call is ever made.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glean.client import WebClient
from glean.models import MODES, ScrapedData
from glean.scraper import WebScraper
from glean.storage import StorageManager
from glean.ui import Display

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def html_sample() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Test Page</title>
        <meta name="description" content="A sample page for testing">
        <meta name="keywords" content="test, sample, scraping">
        <meta property="og:title" content="OG Test Title">
        <meta property="og:image" content="https://example.com/og.png">
    </head>
    <body>
        <nav><a href="/nav">Nav link</a></nav>
        <header><h1>Main Heading</h1></header>
        <h2>Sub Heading</h2>
        <p>First paragraph of real content.</p>
        <p>Second paragraph with more text.</p>
        <ul>
            <li>List item one</li>
            <li>List item two</li>
        </ul>
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>Alpha</td><td>1</td></tr>
            <tr><td>Beta</td><td>2</td></tr>
        </table>
        <img src="/images/pic.jpg" alt="pic">
        <img data-src="https://example.com/lazy.png" alt="lazy">
        <a href="/about">About</a>
        <a href="https://external.com/x">External</a>
        <a href="#anchor">Skip</a>
        <a href="javascript:void(0)">Noop</a>
        <footer><p>Footer text</p></footer>
    </body>
    </html>
    """


@pytest.fixture
def scraper() -> WebScraper:
    return WebScraper()


@pytest.fixture
def temp_storage(tmp_path) -> StorageManager:
    with patch("glean.storage.get_save_dir", return_value=tmp_path):
        storage = StorageManager()
        storage.save_dir = tmp_path
        yield storage


# ---------------------------------------------------------------------------
# WebScraper: parsing (no network)
# ---------------------------------------------------------------------------


def test_extract_metadata(scraper, html_sample):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sample, "html.parser")
    meta = scraper._extract_metadata(soup)
    assert meta["title"] == "Test Page"
    assert meta["description"] == "A sample page for testing"
    assert meta["keywords"] == "test, sample, scraping"
    assert meta["og:title"] == "OG Test Title"
    assert meta["og:image"] == "https://example.com/og.png"
    assert meta["language"] == "en"


def test_extract_text_content_strips_nav_and_footer(scraper, html_sample):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sample, "html.parser")
    title, content = scraper._extract_text_content(soup)
    assert title == "Test Page"
    assert "First paragraph of real content." in content
    assert "Second paragraph" in content
    assert "Nav link" not in content
    assert "Footer text" not in content
    assert "Sub Heading" in content


def test_extract_images_resolves_relative_and_data_src(scraper, html_sample):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sample, "html.parser")
    base = "https://example.com/page"
    images = scraper._extract_images(soup, base)
    assert "https://example.com/images/pic.jpg" in images
    assert "https://example.com/lazy.png" in images


def test_extract_links_resolves_relative_and_skips_junk(scraper, html_sample):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sample, "html.parser")
    base = "https://example.com/page"
    links = scraper._extract_links(soup, base)
    assert "https://example.com/about" in links
    assert "https://external.com/x" in links
    assert not any(link.startswith("#") for link in links)
    assert not any(link.startswith("javascript:") for link in links)


def test_extract_images_limited_to_20():
    scraper = WebScraper()
    from bs4 import BeautifulSoup

    imgs = "".join(f'<img src="https://x.com/{i}.png">' for i in range(50))
    soup = BeautifulSoup(f"<html><body>{imgs}</body></html>", "html.parser")
    result = scraper._extract_images(soup, "https://x.com")
    assert len(result) == 20


# ---------------------------------------------------------------------------
# WebScraper: scrape() with mocked network
# ---------------------------------------------------------------------------


def test_scrape_simple_mocked(scraper, html_sample):
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = html_sample

    with patch.object(scraper.session, "get", return_value=fake_response):
        data = scraper.scrape("https://example.com/page")

    assert isinstance(data, ScrapedData)
    assert data.url == "https://example.com/page"
    assert data.title == "Test Page"
    assert "First paragraph" in data.content
    assert len(data.images) > 0
    assert len(data.links) > 0


def test_scrape_respects_max_content_length(scraper):
    big_html = "<html><body><p>" + ("x" * 5000) + "</p></body></html>"
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = big_html

    with (
        patch(
            "glean.scraper.load_settings",
            return_value={"request_timeout": 30, "max_content_length": 100},
        ),
        patch.object(scraper.session, "get", return_value=fake_response),
    ):
        data = scraper.scrape("https://example.com")

    assert len(data.content) <= 200


def test_scrape_propagates_request_errors(scraper):
    import requests

    with (
        patch.object(
            scraper.session, "get", side_effect=requests.RequestException("boom")
        ),
        pytest.raises(Exception, match="boom"),
    ):
        scraper.scrape("https://example.com")


# ---------------------------------------------------------------------------
# StorageManager
# ---------------------------------------------------------------------------


def test_storage_save_and_load_roundtrip(temp_storage, html_sample):
    data = ScrapedData(
        url="https://example.com",
        title="Test",
        content="Hello world",
        images=["https://example.com/a.png"],
        links=["https://example.com/b"],
        metadata={"lang": "en"},
        summary="A summary",
    )
    path = temp_storage.save(data, "demo")
    assert Path(path).exists()

    loaded = temp_storage.load("demo")
    assert loaded is not None
    assert loaded.url == data.url
    assert loaded.title == data.title
    assert loaded.content == data.content
    assert loaded.summary == "A summary"


def test_storage_load_missing_returns_none(temp_storage):
    assert temp_storage.load("does_not_exist") is None


# ---------------------------------------------------------------------------
# WebClient (mocked LLM)
# ---------------------------------------------------------------------------


def test_ai_client_chat_returns_content():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content="hi there"))]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_completion

    with patch("glean.client.OpenAI", return_value=fake_client):
        client = WebClient()
        out = client.chat([{"role": "user", "content": "hello"}])

    assert out == "hi there"
    fake_client.chat.completions.create.assert_called_once()


def test_ai_client_chat_stream_concatenates_chunks():
    def fake_stream(**kwargs):
        for c in ["Bon", "jour", " !"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=c))]
            yield chunk

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = fake_stream

    with patch("glean.client.OpenAI", return_value=fake_client):
        client = WebClient()
        out = client.chat_stream([{"role": "user", "content": "hi"}])

    assert out == "Bonjour !"


# ---------------------------------------------------------------------------
# Modes sanity
# ---------------------------------------------------------------------------


def test_modes_registered():
    keys = {m.key for m in MODES}
    assert keys == {
        "scrape",
        "summarize",
        "chat",
        "config",
    }


# ---------------------------------------------------------------------------
# Robustness / hardening
# ---------------------------------------------------------------------------


def test_storage_save_prevents_path_traversal(temp_storage):
    data = ScrapedData(url="u", title="t", content="c")
    path = temp_storage.save(data, "../../evil.json")
    assert Path(path).parent == temp_storage.save_dir
    assert Path(path).name == "evil.json"


def test_storage_load_tolerates_missing_keys(temp_storage):
    legacy = {
        "url": "https://old.example",
        "title": "Legacy",
        "content": "old content",
        "scraped_at": 123.0,
    }
    (temp_storage.save_dir / "legacy.json").write_text(
        json.dumps(legacy), encoding="utf-8"
    )
    loaded = temp_storage.load("legacy")
    assert loaded is not None
    assert loaded.url == "https://old.example"
    assert loaded.images == []
    assert loaded.links == []
    assert loaded.metadata == {}


def test_storage_load_returns_none_on_corrupt_json(temp_storage):
    (temp_storage.save_dir / "broken.json").write_text("{not valid", encoding="utf-8")
    assert temp_storage.load("broken") is None


def test_scrape_invalid_url_raises(scraper):
    import requests

    with (
        patch.object(
            scraper.session,
            "get",
            side_effect=requests.exceptions.MissingSchema("Invalid URL"),
        ),
        pytest.raises(Exception, match="Invalid URL"),
    ):
        scraper.scrape("not-a-valid-url")


def test_scrape_empty_body(scraper):
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = ""
    with patch.object(scraper.session, "get", return_value=fake_response):
        data = scraper.scrape("https://example.com/empty")
    assert data.title == "Untitled"
    assert data.content == ""


def test_scrape_http_error_raises(scraper):
    import requests

    with (
        patch.object(
            scraper.session,
            "get",
            side_effect=requests.exceptions.HTTPError("404"),
        ),
        pytest.raises(Exception, match="404"),
    ):
        scraper.scrape("https://example.com/missing")


# ---------------------------------------------------------------------------
# WebClient error handling (mocked LLM)
# ---------------------------------------------------------------------------


def test_ai_client_chat_raises_on_api_error():
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RuntimeError("connection refused")

    with patch("glean.client.OpenAI", return_value=fake_client):
        client = WebClient()
        with pytest.raises(Exception, match="connection refused"):
            client.chat([{"role": "user", "content": "hi"}])


def test_ai_client_chat_stream_raises_on_api_error():
    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = RuntimeError("boom")

    with patch("glean.client.OpenAI", return_value=fake_client):
        client = WebClient()
        with pytest.raises(Exception, match="boom"):
            client.chat_stream([{"role": "user", "content": "hi"}])


def test_ai_client_chat_never_returns_none():
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=MagicMock(content=None))]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_completion

    with patch("glean.client.OpenAI", return_value=fake_client):
        client = WebClient()
        assert client.chat([{"role": "user", "content": "hi"}]) == ""


# ---------------------------------------------------------------------------
# Parsing edge cases
# ---------------------------------------------------------------------------


def test_extract_images_skips_data_uris(scraper):
    from bs4 import BeautifulSoup

    html = (
        "<html><body>"
        '<img src="data:image/png;base64,iVBORw0KGgo=">'
        '<img src="/real.jpg">'
        '<img src="https://x.com/a.png">'
        "</body></html>"
    )
    soup = BeautifulSoup(html, "html.parser")
    imgs = scraper._extract_images(soup, "https://example.com")
    assert "https://example.com/real.jpg" in imgs
    assert "https://x.com/a.png" in imgs
    assert all(not i.startswith("data:") for i in imgs)


def test_extract_images_includes_extensionless_urls(scraper):
    from bs4 import BeautifulSoup

    html = (
        '<html><body><img src="/cdn/image/abc123"><img src="/photo.jpg"></body></html>'
    )
    soup = BeautifulSoup(html, "html.parser")
    imgs = scraper._extract_images(soup, "https://example.com")
    assert "https://example.com/cdn/image/abc123" in imgs
    assert "https://example.com/photo.jpg" in imgs


def test_scrape_malformed_html_does_not_crash(scraper):
    garbage = "<html><body><p>Unclosed paragraph<div><span>no end"
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = garbage
    with patch.object(scraper.session, "get", return_value=fake_response):
        data = scraper.scrape("https://example.com/broken")
    assert data.title == "Untitled"
    assert "Unclosed paragraph" in data.content


def test_scrape_page_without_paragraphs(scraper):
    html = "<html><head><title>Only Title</title></head><body><div>no p tags</div></body></html>"
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = html
    with patch.object(scraper.session, "get", return_value=fake_response):
        data = scraper.scrape("https://example.com")
    assert data.title == "Only Title"
    assert data.content == "no p tags"


def test_extract_links_keeps_query_strings(scraper):
    from bs4 import BeautifulSoup

    html = '<html><body><a href="/search?q=python">link</a><a href="https://x.com/p?a=1">ext</a></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    links = scraper._extract_links(soup, "https://example.com")
    assert "https://example.com/search?q=python" in links
    assert "https://x.com/p?a=1" in links


# ---------------------------------------------------------------------------
# Display robustness (non-interactive / piped stdin)
# ---------------------------------------------------------------------------


def test_display_confirm_falls_back_to_input_on_rich_failure():
    display = Display.__new__(Display)

    with patch("glean.ui.Confirm.ask", side_effect=Exception("no TTY")):
        with patch("builtins.input", return_value="y"):
            assert display.confirm("Continue?") is True
        with patch("builtins.input", return_value="n"):
            assert display.confirm("Continue?") is False
        with patch("builtins.input", side_effect=EOFError):
            assert display.confirm("Continue?") is False


def test_display_prompt_falls_back_to_input_on_rich_failure():
    display = Display.__new__(Display)

    with patch("glean.ui.Prompt.ask", side_effect=Exception("no TTY")):
        with patch("builtins.input", return_value="  hello  "):
            assert display.prompt("URL?") == "hello"
        with patch("builtins.input", side_effect=EOFError):
            assert display.prompt("URL?") == ""


def test_display_pause_swallows_eof():
    display = Display.__new__(Display)
    with patch("builtins.input", side_effect=EOFError):
        display.pause()
