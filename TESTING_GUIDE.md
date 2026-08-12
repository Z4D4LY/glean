# Manual Testing Guide — AI Web Scraper

This document describes the complete procedure for manually testing all application features.

---

## 1. Prerequisites

```bash
# Clone the project
cd ai-web-scraper

# Install in development mode
pip install -e .[dev]

# Verify dependencies (Ollama must be running for AI modes)
ollama serve &
ollama pull qwen2.5:14b  # or the model configured in .env
```

Expected `.env` file at the project root:
```env
API_BASE_URL=http://localhost:11434/v1
MODEL=qwen2.5:14b
API_KEY=ollama
TEMPERATURE=0.6
REQUEST_TIMEOUT=30
MAX_CONTENT_LENGTH=1000000
SAVE_DIR=~/.ai-web-scraper/scraped
```

---

## 2. Entry Points to Verify

| Command | Description | Expected Result |
|----------|-------------|------------------|
| `ai-web-scraper` | CLI installed via `pip install -e .` | Main menu displayed |
| `python -m ai_web_scraper` | Module execution | Main menu displayed |

**Test**: Launch each command, type `0` → should quit cleanly with "Goodbye".

---

## 3. Main Menu — Navigation

On startup, the menu displays 4 modes + Quit:

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MAIN MENU                                     │
├────┬──────────────────────────────────────────┬──────────────────────┤
│ #  │ Mode                                     │ Description          │
├────┼──────────────────────────────────────────┼──────────────────────┤
│ 1  │ Simple Scraping                          │ Extract content...   │
│ 2  │ AI Summary                               │ Automatic page...    │
│ 3  │ Chat with Content                        │ RAG conversation     │
│ 4  │ Configuration                            │ Scraper settings     │
│ 0  │ Quit                                     │                      │
└────┴──────────────────────────────────────────┴──────────────────────┘
```

**Exit shortcuts** (work at any prompt):
- `0` — return to menu / quit
- `q` / `quit` / `exit` — same

---

## 4. Test Cases by Mode

### 4.1 Mode 1 — Simple Scraping

**Objective**: Extract raw content from a URL.

**Steps**:
1. Type `1` → Enter
2. URL: `https://httpbin.org/html` → Enter
3. Wait for "Scraping..." spinner
4. Result displayed in green panel (URL, Title, Content ~3600 chars)
5. **Save?** → `y` → filename: `test_simple` → Enter
   - Message "Saved to: .../test_simple.json"
6. **Use AI?** → `y` → AI Menu appears
7. Choose `1` (Summary) → Wait for "Generating summary..."
   - AI summary displayed
   - **Update file?** → `n`
8. Return to main menu → `0` to quit

**Verifications**:
- [ ] HTML content parsed (no raw tags)
- [ ] JSON file created in `~/.ai-web-scraper/scraped/`
- [ ] AI summary coherent (mentions "Perth", "Moby-Dick", "blacksmith")

---

### 4.2 Mode 2 — AI Summary

**Objective**: Automatic page summarization.

**Steps**:
1. Type `2` → Enter
2. URL: `https://httpbin.org/html` → Enter
3. Wait for scraping + "Generating summary..."
4. Summary displayed in cyan panel
5. **Save summary?** → `y` → name: `test_summary`
6. Verify the JSON file contains the `summary` field

---

### 4.3 Mode 3 — Chat with Content (RAG)

**Objective**: Contextual conversation about a scraped page.

**Steps**:
1. Type `3` → Enter
2. URL: `https://httpbin.org/html` → Enter
3. Chat interface:
   ```
   ╭──────────────────────────────────────────────────────────────────────╮
   │ Chat with Content                                                    │
   │ Ask questions about the scraped page. Type /back to return           │
   ╰──────────────────────────────────────────────────────────────────────╯
   ```
4. Question: `Who is Perth?` → Enter
   - AI response: description of the blacksmith, his tragic past
5. Question: `What happened to his feet?` → Enter
   - Response: lost to frostbite in a barn
6. Type `/back` → Return to main menu

**Verifications**:
- [ ] Context preserved between questions
- [ ] `/back` works (not `exit` which would quit the app)

---

### 4.4 Mode 4 — Configuration

**Objective**: Display current configuration.

**Steps**:
1. Type `4` → Enter
2. Panel displays:
   - API: Base URL, Model, API Key (masked), Temperature
   - Scraping: Timeout, Max Content
   - Storage: Directory
3. **Change settings?** → `n` (app says to edit `.env`)
4. `0` → Return to menu

---

## 5. Cross-Cutting Tests

### 5.1 Error Handling

| Scenario | Action | Expected Result |
|----------|--------|------------------|
| Invalid URL | Mode 1 → `not-a-url` | Red panel "Error: Invalid URL" |
| HTTP 404 | Mode 1 → `https://httpbin.org/status/404` | Red panel "Scraping failed: 404" |
| Timeout | Mode 1 → slow URL (e.g. `http://10.255.255.1/`) | Red panel after configured timeout |

### 5.2 Global Keyboard Shortcuts

At **any prompt**:
- `Ctrl+C` → Clean quit ("Goodbye!")
- `q` / `quit` / `exit` → Equivalent to `0` (back/quit)
- Empty input → Re-displays prompt (per field)

### 5.3 Data Persistence

1. Scrape (Mode 1) + Save
2. Quit the app (`0` at main menu)
3. Relaunch `ai-web-scraper`
4. Verify the `test_simple.json` file exists in `~/.ai-web-scraper/scraped/`

---

## 6. Non-Regression Checklist

Before validating a release, run:

```bash
# 1. Unit tests (24 tests)
python -m pytest tests/ -v

# 2. Lint
ruff check .

# 3. Build & install check
pip install -e .[dev]
ai-web-scraper --help  # or just launch and quit

# 4. Smoke test (scriptable)
python -c "
from ai_web_scraper.app import AIWebScraper
app = AIWebScraper()
assert len(app.modes) == 4
print('✅ All modes registered')
"
```

---

## 7. Recommended Test URLs

| Type | URL | Notes |
|------|-----|-------|
| Simple HTML | `https://httpbin.org/html` | Moby-Dick content, ~3.6KB |
| JSON | `https://httpbin.org/json` | Structured content |
| Large page | `https://httpbin.org/bytes/100000` | Test max content length |
| 404 | `https://httpbin.org/status/404` | HTTP error test |
| Redirect | `https://httpbin.org/redirect/3` | Redirect following test |
| Robots.txt | `https://httpbin.org/robots.txt` | Text file test |

---

## 8. Generated Files (Location)

```
~/.ai-web-scraper/
├── scraped/
│   ├── test_simple.json           # Mode 1 save
│   ├── test_summary.json          # Mode 2 save
│   └── ...
└── config.json                    # Persistent settings (if implemented)
```

---

## 9. Global Success Indicators

- [ ] Both entry points launch the app
- [ ] All 4 modes accessible and functional
- [ ] Scraping + Save + AI (summary/chat) chained without crashes
- [ ] Config displays correct values from `.env`
- [ ] `q`/`quit`/`exit`/`0` work everywhere
- [ ] `Ctrl+C` quits cleanly
- [ ] Unit tests: 24 passed
- [ ] `ruff check .` : clean

---

*Document generated for AI Web Scraper v1.0.0 — Complete manual testing procedure*