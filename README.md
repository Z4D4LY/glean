# Glean

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/Z4D4LY/glean/actions/workflows/ci.yml/badge.svg)](https://github.com/Z4D4LY/glean/actions/workflows/ci.yml)

CLI web scraper with AI features — summarization and RAG chat.

Powered by any OpenAI-compatible API (Ollama, vLLM, OpenAI, etc.).

## Features

- **Simple scraping** — HTTP + BeautifulSoup content extraction
- **AI summarization** — Automatic page summaries via LLM
- **RAG chat** — Conversational Q&A over scraped content
- **Configuration** — View current scraper/API settings
- **24 unit tests** — Fully offline, network and LLM mocked
- **No Selenium/Playwright** — Lightweight, pure-HTTP scraping

## Installation

```bash
pip install -e .
```

## Usage

```bash
glean
```

Or via module:

```bash
python -m glean
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Default: Local Ollama

Make sure [Ollama](https://ollama.ai) is running with a model:

```bash
ollama run qwen2.5:14b
```

### Alternative: Hosted API

Edit `.env` to point to any OpenAI-compatible endpoint.

## Tests

```bash
pip install -e .[dev]
python -m pytest tests/ -v
```

All 24 tests run fully offline (network and LLM are mocked).

## Project Structure

```
glean/
├── src/
│   └── glean/
│       ├── __init__.py
│       ├── __main__.py         # Module entry point
│       ├── app.py              # Application controller
│       ├── cli.py              # CLI entry point
│       ├── client.py           # OpenAI-compatible LLM client
│       ├── config.py           # Lazy config loader (.env)
│       ├── models.py           # Data models & mode registry
│       ├── modes.py            # Interactive mode classes
│       ├── scraper.py          # Web scraping engine
│       ├── storage.py          # Save/load manager
│       └── ui.py               # Rich terminal UI
├── tests/
│   ├── test_scraper.py         # 20 unit tests for core classes
│   └── test_modes.py           # 4 tests for interactive modes
├── .env.example
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml
└── ruff.toml
```

## License

MIT