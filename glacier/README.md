# Glacier

### Your personal AI desktop assistant for Windows

Glacier is a Python-based desktop assistant that brings conversational AI, voice interaction, computer and file tools, browser automation, personal memory, reminders, and productivity workflows into one Windows application. It combines a desktop dashboard with a tool-using AI agent, so you can ask questions in natural language and—when enabled—let Glacier carry out supported actions on your PC.

> **Project status:** This README describes the code and scripts included in this repository archive. Optional integrations such as Playwright, Telegram, email, MCP servers, and an OpenAI-compatible local model require separate setup.

---

## Contents

- [What Glacier can do](#what-glacier-can-do)
- [Highlights](#highlights)
- [How it works](#how-it-works)
- [Technology](#technology)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Run Glacier](#run-glacier)
- [Optional integrations](#optional-integrations)
- [Local API](#local-api)
- [Skills and extensibility](#skills-and-extensibility)
- [Project structure](#project-structure)
- [Safety and privacy](#safety-and-privacy)
- [Troubleshooting](#troubleshooting)
- [Run tests](#run-tests)
- [Contributing](#contributing)
- [License](#license)

---

## What Glacier can do

Glacier exposes **120 registered tools** across the categories below. The tools available at runtime depend on your configuration, installed optional dependencies, permissions, and connected services.

| Area | Capabilities |
|---|---|
| **AI conversation** | Natural-language chat, conversation history, tool selection, and feedback. |
| **Voice** | Microphone input, speech-to-text, spoken responses, wake-word listening, and follow-up listening. |
| **Desktop & system** | Open or close apps, inspect running apps, volume and brightness controls, media keys, clipboard, screen lock, system status, and process information. |
| **File management** | Search and list files, read supported documents, create folders, copy/move/rename, write/edit, zip/unzip, organize Downloads, and undo supported organization actions. |
| **Browser automation** | Open pages, inspect page structure and links, read content, manage tabs, scroll, click, type, and take browser screenshots. Requires the optional browser setup for automation. |
| **Web & information** | Web search, webpage reading, Wikipedia, YouTube, weather, news, currency, unit conversion, dictionary, date/time, and calculator tools. |
| **Research** | Multi-source research workflows that can produce a cited report in the configured reports folder. |
| **Memory & knowledge** | Save and recall facts, search personal notes, index folders, and retrieve relevant passages from indexed documents. |
| **Productivity** | Notes, to-dos, calendar events, contacts, reminders, timers, scheduled tasks, and page monitoring. |
| **Vision & screen** | Capture or inspect screenshots, describe images, extract text with OCR, and inspect screen content. |
| **Communication** | Read/search email, send email, interact with WhatsApp Desktop, and communicate with Glacier through Telegram when configured. |
| **Developer tools** | Git status/diff/log/commit, PowerShell and Python tools, MCP tool discovery/calls, and a local skill system. |
| **Proactive assistance** | Scheduled morning digest and system alerts such as low battery or high resource usage, depending on configuration. |

### Voice-first interaction

- Talk to Glacier using the microphone.
- Use the configured wake word (the default wake-word list includes variations of “Glacier”).
- Glacier can speak its responses using text-to-speech.
- Speech recognition uses the configured speech engine; the default configuration selects Whisper.
- Configure the voice, speech rate, language, and follow-up listening duration in `.env`.

### Work with files and your own knowledge

- Search configured drives and folders using the file index.
- Read supported formats such as PDF, DOCX, XLSX, and CSV where the relevant reader is available.
- Index selected folders and search their contents through the local knowledge index.
- Save personal facts, notes, tasks, contacts, and calendar entries in Glacier's local data store.

### Automate supported browser and desktop actions

- Use browser tools to navigate and interact with pages when Playwright and a supported browser are installed.
- Use desktop tools for supported application, keyboard, mouse, and system actions.
- Computer-control and other sensitive actions are gated by the project's confirmation and safety logic.

---

## Highlights

- **Desktop dashboard:** A dark, aurora-inspired interface built with HTML and displayed through `pywebview`.
- **AI tool calling:** The assistant can choose from a registry of tools rather than only generating text.
- **Gemini integration:** Uses the Google GenAI SDK and a Gemini API key as the primary AI configuration.
- **Alternative model endpoint:** Can be configured to use an OpenAI-compatible endpoint; an installed Ollama service can be detected when enabled.
- **Local application data:** SQLite stores app data such as memory, reminders, notes, tasks, contacts, and indexed knowledge.
- **Extensible skills:** Add Markdown instructions or Python tools in the `skills/` directory.
- **Optional remote channels:** Telegram bot and a token-protected local HTTP API.
- **Diagnostics:** `doctor.py` and `doctor.bat` help check the installation and configuration.

---

## How it works

At a high level, a request moves through the following components:

```mermaid
flowchart TD
    U[User: dashboard, keyboard, or microphone] --> UI[Desktop UI / Voice listener]
    UI --> B[Glacier brain and conversation manager]
    B --> L[Configured language model]
    L --> R[Tool registry]
    R --> T[Desktop, files, browser, web, memory, productivity, and communication tools]
    T --> D[(Local SQLite data and indexes)]
    T --> X[Connected services and optional integrations]
    T --> B
    B --> O[Text response / spoken response / dashboard update]
```

The desktop interface is in `ui/glacier_dashboard.html`. The Python-to-dashboard bridge is implemented in `api.py`, while `brain.py`, `engines.py`, `registry.py`, and the modules under `tools/` handle the assistant logic and actions.

---

## Technology

| Component | Technology found in the project |
|---|---|
| Main language | Python |
| Desktop window | `pywebview` |
| Dashboard | HTML, CSS, and JavaScript |
| Primary AI provider | Google GenAI SDK (Gemini) |
| Optional model backend | OpenAI-compatible API; Ollama auto-detection is supported by configuration |
| Local persistence | SQLite |
| Voice output | `edge-tts` |
| Speech recognition | `faster-whisper` and `SpeechRecognition` dependencies |
| System and desktop utilities | `psutil`, `pyautogui`, `pystray`, `pycaw`, and Windows-related libraries |
| Browser automation | Playwright (optional) |
| Document handling | PyPDF, python-docx, and openpyxl |
| Image handling | Pillow |
| Optional tool integration | MCP package and Node.js-based MCP servers |

---

## Requirements

- Windows PC (the included launcher scripts and several desktop-control dependencies are Windows-oriented).
- Python **3.12 recommended**. The installer also checks for Python 3.13.
- A Google Gemini API key for the primary AI provider.
- Microphone and speakers/headphones for voice features.
- Internet connection for Gemini and online services.

Optional, depending on the features you want:

- Google Chrome, Microsoft Edge, or a Playwright-managed Chromium browser.
- Node.js for MCP servers.
- Git for Git-related tools.
- Ollama or another OpenAI-compatible model endpoint for an alternative/local model backend.
- Telegram bot credentials for phone-based interaction.
- Email credentials (for example, a Gmail App Password) for email tools.

---

## Installation

### 1. Get the project

Download or clone the repository, then open the `glacier` project directory—the directory containing `install.bat`, `requirements.txt`, and `main_gui.py`.

### 2. Run the installer

Double-click:

```text
install.bat
```

The installer:

1. Looks for Python 3.12, then Python 3.13, then `python` on PATH.
2. Creates a virtual environment in `.venv` if one does not already exist.
3. Installs the packages in `requirements.txt`.
4. Offers to install Playwright and Chromium for browser automation.
5. Creates `.env` from `.env.example` if `.env` does not exist, then opens it for configuration.
6. Runs the diagnostic script.

### 3. Add your Gemini API key

Get a key from [Google AI Studio](https://aistudio.google.com/apikey). In the `.env` file, set:

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
```

Save the file. Do not share this key or commit `.env` to version control.

### 4. Launch Glacier

Double-click:

```text
run.bat
```

The desktop dashboard should open. On first launch, allow the application a little time to initialize its background services and voice components.

> **Alternative:** To use the keyboard/voice terminal instead of the desktop dashboard, use `run_console.bat` as described below.

---

## Configuration

All runtime configuration is read from `.env` in the project directory. Start with `.env.example`; only add the settings you need.

### Core settings

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Primary Gemini API key. |
| `MODEL_NAME` | Preferred model name. |
| `MODEL_FALLBACKS` | Optional comma-separated fallback model list. |
| `USER_NAME` | Name used when personalizing responses. |
| `USER_ADDRESS` | Preferred form of address. |
| `ASSISTANT_NAME` | Assistant display name. |

### Voice settings

| Variable | Purpose |
|---|---|
| `VOICE_ENABLED` | Enable or disable spoken responses. |
| `TTS_VOICE` | Text-to-speech voice. |
| `TTS_RATE` / `TTS_PITCH` | Speech rate and pitch adjustments. |
| `STT_ENGINE` | Speech-recognition backend selection. |
| `WHISPER_MODEL` | Whisper model size, such as `base` or `small`. |
| `STT_LANGUAGE` | Speech-recognition language hint. |
| `ALWAYS_LISTEN` | Enable wake-word listening. |
| `FOLLOWUP_SECONDS` | Follow-up listening window after a response. |
| `MIC_DEVICE` | Optional microphone device selection. |

### Tools, paths, and safety

| Variable | Purpose |
|---|---|
| `SEARCH_DRIVES` | Drives/folders included in file search; the example file documents the `|` separator. |
| `DISABLED_TOOLS` | Disable selected tools by name. |
| `DISABLED_CATEGORIES` | Disable complete tool categories. |
| `USE_RECYCLE_BIN` | Prefer recoverable deletion through the Recycle Bin. |
| `CONFIRM_TTL_SECONDS` | Lifetime of a pending confirmation. |
| `MAX_TOOL_OUTPUT` | Limit tool output size. |

### Optional integrations and automation

| Variable | Purpose |
|---|---|
| `OPENAI_COMPAT_BASE_URL` | Base URL for an OpenAI-compatible model service. |
| `OPENAI_COMPAT_MODEL` | Model identifier for that service. |
| `OPENAI_COMPAT_API_KEY` | API key for that service, if required. |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token. |
| `TELEGRAM_ALLOWED_CHAT_ID` | Restrict Telegram commands to an allowed chat ID. |
| `EMAIL_ADDRESS` | Email account used by the email integration. |
| `EMAIL_APP_PASSWORD` | Email app password; do not use or store your normal account password. |
| `API_SERVER_ENABLED` | Enable the local API server. |
| `API_SERVER_PORT` | Local API server port (default: `8765`). |
| `HOME_CITY` | City used for location-based digest information. |
| `DIGEST_ENABLED` / `DIGEST_TIME` | Configure the scheduled digest. |
| `START_HIDDEN` | Start the desktop window hidden when supported by the launcher. |
| `BROWSER_CHANNEL` | Browser channel selection. |

The full list of supported defaults and additional settings is maintained in `config.py` and `.env.example`.

---

## Run Glacier

### Desktop dashboard

```bat
run.bat
```

Launches `main_gui.py` using the virtual environment. When the tray integration is enabled, closing the window hides it in the system tray; use the tray menu to reopen or quit Glacier.

### Console mode

```bat
run_console.bat
```

Useful for debugging and keyboard-based interaction. The underlying entry point is `main.py`.

You can also activate the environment manually and run:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

For voice input in console mode:

```powershell
python main.py --voice
```

### Diagnostics

```bat
doctor.bat
```

Or, from an activated virtual environment:

```powershell
python doctor.py
```

### Start with Windows

The project includes an autostart helper:

```powershell
.\.venv\Scripts\python.exe setup_autostart.py
```

To remove the configured autostart entry:

```powershell
.\.venv\Scripts\python.exe setup_autostart.py --remove
```

Review the helper's behavior and your Windows startup settings before enabling automatic launch.

---

## Optional integrations

### Browser automation (Playwright)

During installation, answer `y` when the installer asks whether to install Playwright. Or run:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

The browser tools also use the configured browser channel. Browser automation is optional; basic chat does not require it.

### Ollama or another OpenAI-compatible model service

Glacier's configuration supports an OpenAI-compatible endpoint. For an Ollama service running locally, a typical configuration is:

```dotenv
OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1
OPENAI_COMPAT_MODEL=llama3.2
OPENAI_COMPAT_API_KEY=ollama
```

Make sure the model service is installed, running, and that the selected model has been downloaded. Other compatible providers can be configured by changing the base URL, model, and API key as appropriate.

### Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Add its token to `TELEGRAM_BOT_TOKEN` in `.env`.
3. Set `TELEGRAM_ALLOWED_CHAT_ID` to the chat ID allowed to control this Glacier instance.
4. Start a conversation with the bot and test the connection.

Keep the token private and restrict access to the intended chat.

### Email

Configure `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD`. For Gmail, use an App Password where supported and ensure the account's required security settings are enabled. Never put your normal email password in the project configuration.

### MCP servers

The optional MCP dependency is listed in `requirements-optional.txt`. MCP server processes may also require Node.js or other server-specific runtimes. Only connect MCP servers you trust, because their tools may expose external capabilities to the assistant.

---

## Local API

Glacier includes an optional HTTP API server. It binds to **`127.0.0.1`** and is disabled by default.

Enable it in `.env`:

```dotenv
API_SERVER_ENABLED=true
API_SERVER_PORT=8765
```

Available endpoints:

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/health` | No token required | Basic health response. |
| `POST` | `/ask` | Bearer token or `X-Glacier-Token` | Send `{ "text": "..." }` and receive a reply. |
| `POST` | `/v1/chat/completions` | Bearer token or `X-Glacier-Token` | OpenAI-style chat-completion request shape. |
| `POST` | `/chat/completions` | Bearer token or `X-Glacier-Token` | Alias for the chat-completions route. |

The API token is generated automatically and stored at:

```text
data/api_token.txt
```

Example request:

```bash
curl http://127.0.0.1:8765/ask \
  -H "Authorization: Bearer YOUR_GLACIER_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Summarize my reminders"}'
```

**Security note:** The API is designed to listen on loopback. Do not expose it directly to a public network or change its bind address without adding appropriate authentication, access controls, and transport security.

---

## Skills and extensibility

Glacier can load custom skills from the `skills/` directory.

- **Markdown skill files** (`.md` or `SKILL.md`) provide instructions that Glacier can use when handling a task.
- **Python skill files** (`.py`) can register additional tools using the project's `registry` decorator.
- `skills/example_skill.py` is included as a starting example.

A minimal Python tool follows this pattern:

```python
from registry import tool


@tool(category="custom", label="Example tool")
def example_tool(message: str) -> str:
    """Return a simple example response."""
    return f"You said: {message}"
```

Restart Glacier after adding a skill. Review custom code before placing it in the skills folder; Python skills execute locally with the permissions of the current user.

More details: [`skills/README.md`](skills/README.md).

---

## Project structure

```text
Glacier/
├── .env.example             # Configuration template (copy to .env)
├── install.bat              # Windows installer
├── run.bat                  # Launch desktop dashboard
├── run_console.bat          # Launch console mode
├── doctor.bat               # Run diagnostics
├── main_gui.py              # Desktop application entry point
├── main.py                  # Console / voice entry point
├── api.py                   # Dashboard-to-Python bridge
├── brain.py                 # Assistant conversation and tool orchestration
├── engines.py               # Model/provider integration
├── config.py                # Runtime configuration
├── registry.py              # Tool registration and execution
├── safety.py                # Confirmation and safety checks
├── services.py              # Background service startup
├── voice.py                 # Speech input/output and wake listener
├── memory.py                # Facts and document knowledge retrieval
├── fileindex.py              # File indexing and search
├── docreader.py              # Supported document reading
├── db.py                     # SQLite schema and database helpers
├── scheduler.py              # Reminders, scheduled tasks, and digest
├── channels/
│   ├── api_server.py         # Local HTTP API
│   └── telegram_bot.py       # Telegram channel
├── tools/                    # Built-in assistant tools by category
├── skills/                   # Custom Markdown/Python skills
├── tests/                    # Core and end-to-end tests
├── ui/
│   └── glacier_dashboard.html
├── requirements.txt          # Core Python dependencies
└── requirements-optional.txt # Optional dependencies
```

Runtime data is written to the configured data directory (by default, `data/`). It includes the SQLite database, logs, indexes, reports, and generated API token.

---

## Safety and privacy

Glacier can interact with files, applications, browser pages, communication services, and system controls. Treat it as software with real permissions on your computer.

The project includes safeguards such as:

- Confirmation gates for designated sensitive actions.
- Blocked paths and checks for secret-bearing locations.
- A configurable disabled-tools and disabled-categories mechanism.
- Recycle Bin behavior for supported file deletion operations.
- Redaction of configured secrets in logs.
- Handling of external web, email, file, and clipboard content as untrusted input in relevant workflows.
- A Telegram allowed-chat setting and token authentication for the local API's POST routes.

These safeguards reduce risk; they do **not** make every action risk-free. Review commands, file paths, browser actions, messages, and generated code before approving them. Keep API keys, bot tokens, app passwords, and `data/api_token.txt` private.

### Important: clean up secrets before sharing this project

The supplied archive contains a `.env` file in addition to `.env.example`. If `.env` contains real API keys, bot tokens, email app passwords, or other credentials, **revoke/rotate those credentials** if the archive has been shared, then remove `.env` from the distributable copy. Share `.env.example` instead.

Do not distribute the local `.venv/`, `__pycache__/`, runtime `data/`, logs, personal databases, browser profiles, or generated reports. These are machine-specific, can make archives unnecessarily large, and may contain private information.

---

## Troubleshooting

| Problem | What to try |
|---|---|
| Python is not detected | Install Python 3.12, enable **Add Python to PATH**, reopen the terminal, and run `install.bat` again. |
| Dashboard does not open | Run `doctor.bat`; then try `run_console.bat` to see startup errors. Check that `ui/glacier_dashboard.html` exists. |
| Gemini requests fail | Check `GEMINI_API_KEY`, internet connectivity, model availability, and provider quota. |
| Microphone is not detected | Check Windows microphone permissions and the selected input device; review `STT_ENGINE`, `MIC_DEVICE`, and `WHISPER_MODEL`. |
| Browser tools are unavailable | Install Playwright and its Chromium browser, or verify the configured Chrome/Edge channel. |
| Telegram does not respond | Verify the bot token, allowed chat ID, network access, and that the bot has been started. |
| Local API returns 401 | Read the token from `data/api_token.txt` and send it as a Bearer token or `X-Glacier-Token` header. |
| A tool is unavailable | Check `DISABLED_TOOLS`, `DISABLED_CATEGORIES`, optional dependencies, and the tool's required credentials. |

Application diagnostics and logs are stored in the configured data directory. Review `errors.log` for failures and `audit.log` for tool activity; redact private information before sharing logs.

---

## Run tests

Activate the virtual environment from the project directory, then run:

```powershell
.\.venv\Scripts\Activate.ps1
python tests/test_core.py
python tests/test_e2e.py
```

The end-to-end tests include the assistant tool loop and local API behavior. Some integration tests may depend on the local environment and installed optional packages.

---

## Contributing

Contributions that improve reliability, safety, accessibility, documentation, and test coverage are welcome.

1. Create a branch for your change.
2. Keep optional integrations optional where practical.
3. Add or update tests for behavior changes.
4. Never commit `.env`, credentials, personal databases, logs, or machine-specific virtual environments.
5. Document new configuration variables and safety implications.
6. Run the test scripts before submitting your change.

---

## License

No license file or explicit license declaration was present in the supplied project archive. Add a `LICENSE` file and update this section before publishing or accepting external contributions. Until then, do not assume the project is open-source or that others have permission to redistribute it.

---

<p align="center">
  <strong>Glacier — one assistant, many useful workflows.</strong><br>
  Built to bring AI closer to your everyday desktop work.
</p>
