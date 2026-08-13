#!/usr/bin/env python3
"""Tests for the interactive mode classes (Config) and wiring.

Network and the real TTY UI are fully mocked, so these run offline and headless.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glean.app import Glean
from glean.client import WebClient
from glean.modes import ConfigMode
from glean.scraper import WebScraper
from glean.storage import StorageManager


class FakeDisplay:
    def __init__(self, prompts=None):
        self.boxes = []
        self.prints = []
        self.confirms = []
        self._prompts = list(prompts or [])

    def prompt(self, text):
        if self._prompts:
            return self._prompts.pop(0)
        return ""

    def confirm(self, text):
        self.confirms.append(text)
        return False

    def pause(self, text="\nPress Enter..."):
        return None

    def print_box(self, title, content="", style="cyan"):
        self.boxes.append((title, content))

    def print_menu(self, *args, **kwargs):
        pass

    def print_scraped_data(self, *args, **kwargs):
        pass

    def print_ai_response(self, *args, **kwargs):
        pass

    @property
    def console(self):
        return self

    def print(self, *args, **kwargs):
        self.prints.append(args)


@pytest.fixture
def temp_storage(tmp_path):
    with patch("glean.storage.get_save_dir", return_value=tmp_path):
        storage = StorageManager()
        storage.save_dir = tmp_path
        yield storage


# ---------------------------------------------------------------------------
# ConfigMode
# ---------------------------------------------------------------------------


def test_config_mode_runs(temp_storage):
    display = FakeDisplay()
    mode = ConfigMode(
        client=MagicMock(spec=WebClient),
        scraper=MagicMock(spec=WebScraper),
        storage=temp_storage,
        display=display,
    )
    with patch("builtins.input", return_value=""):
        mode.run()
    texts = [f"{b[0]} {b[1]}" for b in display.boxes]
    assert any("Configuration" in t for t in texts)


# ---------------------------------------------------------------------------
# Glean wiring
# ---------------------------------------------------------------------------


def test_app_builds_all_modes():
    with (
        patch("glean.storage.get_save_dir", return_value=Path("/tmp")),
        patch("glean.app.Display"),
    ):
        app = Glean()
    assert set(app.modes.keys()) == {
        "scrape",
        "summarize",
        "chat",
        "config",
    }


def test_main_menu_invalid_choice_does_not_crash():
    display = FakeDisplay(prompts=["99"])
    with (
        patch("glean.storage.get_save_dir", return_value=Path("/tmp")),
        patch("glean.app.Display", return_value=display),
        patch("builtins.input", return_value=""),
    ):
        app = Glean()
        app._main_menu()
    texts = [f"{b[0]} {b[1]}" for b in display.boxes]
    assert any("invalid" in t.lower() for t in texts)


def test_main_menu_exit_stops_app():
    display = FakeDisplay(prompts=["0"])
    with (
        patch("glean.storage.get_save_dir", return_value=Path("/tmp")),
        patch("glean.app.Display", return_value=display),
        patch("builtins.input", return_value=""),
    ):
        app = Glean()
        app._main_menu()
    assert app.running is False
