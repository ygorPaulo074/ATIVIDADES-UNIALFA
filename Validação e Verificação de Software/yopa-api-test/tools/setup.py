"""
Initial configuration wizard for AI-ChatBot.
Generates .env and, optionally, Dockerfile + docker-compose.yml.
Run from the project root: python tools/setup.py
"""
import json
import os
import secrets
import shutil
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).parent))
from deployment_scripts import (
    create_sql_scripts,
    generate_dockerfile,
    generate_docker_compose,
)

# ── Catalog ────────────────────────────────────────────────────────────────────

DEPLOY_OPTIONS = {"1": "local", "2": "docker"}

AUTH_MODE_OPTIONS = {"1": "standalone", "2": "internal"}

PROVIDERS = {
    "1": {
        "name": "OpenAI",
        "validate_url": "https://api.openai.com/v1/models",
        "auth_type": "bearer",
        "models": [
            ("gpt-4o",        "multimodal, best cost-benefit"),
            ("gpt-4o-mini",   "lightweight and cheap variant of 4o"),
            ("o3",            "reasoning model"),
            ("o4-mini",       "lightweight reasoning"),
            ("gpt-5",         "latest, advanced general use"),
            ("gpt-5-mini",    "economical variant of GPT-5"),
            ("gpt-5-nano",    "ultra-lightweight variant of GPT-5"),
        ],
    },
    "2": {
        "name": "Anthropic",
        "validate_url": "https://api.anthropic.com/v1/models",
        "auth_type": "anthropic",
        "models": [
            ("claude-sonnet-4-6", "balanced speed/capability"),
            ("claude-opus-4-6",   "most powerful, complex tasks"),
            ("claude-haiku-4-5",  "fastest and cheapest"),
        ],
    },
    "3": {
        "name": "Google",
        "validate_url": None,
        "auth_type": "google",
        "models": [
            ("gemini/gemini-2.0-flash", "fast and efficient"),
            ("gemini/gemini-2.5-pro",   "huge context window, multimodal"),
        ],
    },
    "4": {
        "name": "Mistral",
        "validate_url": "https://api.mistral.ai/v1/models",
        "auth_type": "bearer",
        "models": [
            ("mistral/mistral-large-latest", "most capable"),
            ("mistral/mistral-small-latest", "lightweight"),
            ("mistral/codestral-latest",     "code-specialized"),
        ],
    },
    "5": {
        "name": "DeepSeek",
        "validate_url": "https://api.deepseek.com/v1/models",
        "auth_type": "bearer",
        "models": [
            ("deepseek/deepseek-chat",     "DeepSeek-V3, cost-competitive"),
            ("deepseek/deepseek-reasoner", "reasoning model"),
        ],
    },
    "6": {
        "name": "Cohere",
        "validate_url": "https://api.cohere.ai/v1/models",
        "auth_type": "bearer",
        "models": [
            ("command-r-plus", "strong in RAG and semantic search"),
            ("command-r",      "lighter variant"),
        ],
    },
    "7": {
        "name": "Groq",
        "validate_url": "https://api.groq.com/openai/v1/models",
        "auth_type": "bearer",
        "models": [
            ("groq/llama-3.3-70b-versatile", "Llama 3.3 70B — fast and capable"),
            ("groq/llama-3.1-8b-instant",    "Llama 3.1 8B — ultra-fast, low latency"),
            ("groq/mixtral-8x7b-32768",      "Mixtral 8x7B — long context"),
            ("groq/gemma2-9b-it",            "Gemma 2 9B — efficient instruction-tuned"),
        ],
    },
}

STORAGE_OPTIONS = {"1": "local", "2": "database", "3": "webhook"}

ANALYZER_LANGUAGE_OPTIONS = {
    "1": ("pt", "Portuguese"),
    "2": ("es", "Spanish"),
    "3": ("fr", "French"),
    "4": ("de", "German"),
    "5": ("it", "Italian"),
    "6": ("ja", "Japanese"),
    "7": ("zh", "Chinese"),
}

LOG_LEVEL_OPTIONS = {"1": "DEBUG", "2": "INFO", "3": "WARNING", "4": "ERROR"}


# ── Terminal colors ────────────────────────────────────────────────────────────

_RST  = "\033[0m"
_BOLD = "\033[1m"
_DIM  = "\033[2m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"
_GRN  = "\033[32m"
_RED  = "\033[31m"
_YLW  = "\033[33m"
_MAG  = "\033[35m"

_DOT   = f"{_BLUE}●{_RST}"
_DONE  = f"{_GRN}◆{_RST}"
_WARN  = f"{_YLW}▲{_RST}"
_LINE  = f"{_DIM}│{_RST}"
_UNSEL = f"{_DIM}○{_RST}"
_ARROW = f"{_CYAN}›{_RST}"


# ── Animated corner spinner ────────────────────────────────────────────────────

_SPIN_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
_TOTAL_STEPS = 15


class _CornerSpinner:
    """Animated blue dot progress bar rendered in the top-right corner."""

    def __init__(self) -> None:
        self._step  = 0
        self._frame = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_step(self, step: int) -> None:
        with self._lock:
            self._step = step

    def finish(self) -> None:
        with self._lock:
            self._step = _TOTAL_STEPS
        time.sleep(0.35)
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.8)
        self._clear()

    def _loop(self) -> None:
        while self._running:
            self._render()
            with self._lock:
                self._frame += 1
            time.sleep(0.1)

    def _render(self) -> None:
        cols = shutil.get_terminal_size((80, 24)).columns
        with self._lock:
            step = self._step
            frame_idx = self._frame % len(_SPIN_FRAMES)

        spin = f"{_CYAN}{_SPIN_FRAMES[frame_idx]}{_RST}"
        bar_w = 12
        filled = round(bar_w * step / _TOTAL_STEPS)
        bar = f"{_CYAN}{'●' * filled}{_DIM}{'○' * (bar_w - filled)}{_RST}"
        label = f"{_DIM}{step}/{_TOTAL_STEPS}{_RST}"
        # visible char count (no ANSI): 1 spinner + 1 space + bar_w + 2 spaces + label digits
        visible = 2 + bar_w + 2 + len(f"{step}/{_TOTAL_STEPS}")
        col = max(1, cols - visible)
        sys.stdout.write(f"\033[s\033[1;{col}H{spin} {bar}  {label}\033[u")
        sys.stdout.flush()

    def _clear(self) -> None:
        cols = shutil.get_terminal_size((80, 24)).columns
        sys.stdout.write(f"\033[s\033[1;1H{' ' * cols}\033[u")
        sys.stdout.flush()


_spinner = _CornerSpinner()
_step_counter = [0]


# ── UI helpers ─────────────────────────────────────────────────────────────────

def _header() -> None:
    print(f"\n  {_BLUE}{_BOLD}●  AI-ChatBot{_RST}  {_DIM}Setup wizard — run once before starting the server.{_RST}\n")


def _step(title: str, hint: str = "") -> None:
    _spinner.set_step(_step_counter[0])
    _step_counter[0] += 1
    print(f"\n  {_DOT}  {_BOLD}{title}{_RST}")
    if hint:
        print(f"  {_LINE}  {_DIM}{hint}{_RST}")


def _done(label: str, value: str) -> None:
    print(f"  {_DONE}  {_DIM}{label}{_RST}  {value}")


def _opt(n: str | int, label: str, desc: str = "") -> None:
    desc_part = f"  {_DIM}{desc}{_RST}" if desc else ""
    print(f"  {_LINE}  {_UNSEL}  {_DIM}{n}.{_RST}  {label}{desc_part}")


def _ask(label: str, default: str = "") -> str:
    hint = f"  {_DIM}({default}){_RST}" if default else ""
    val = input(f"  {_LINE}  {_ARROW}  {label}{hint}  ").strip()
    return val or default


def _err(msg: str) -> None:
    print(f"  {_RED}✗{_RST}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_WARN}  {msg}")


def _ok(msg: str) -> None:
    print(f"  {_GRN}✓{_RST}  {msg}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def validate_api_key(provider_num: str, api_key: str) -> tuple[bool, str]:
    p = PROVIDERS[provider_num]
    auth_type = p["auth_type"]
    url = p["validate_url"]

    if auth_type == "google":
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        headers: dict = {}
    elif auth_type == "anthropic":
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    else:
        headers = {"Authorization": f"Bearer {api_key}"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return True, ""
        if r.status_code in (401, 403):
            return False, "Invalid API key."
        return False, f"Unexpected status: {r.status_code}."
    except requests.exceptions.ConnectionError:
        return False, "Connection failed. Check your internet."
    except requests.exceptions.Timeout:
        return False, "Request timed out while validating the key."
    except Exception as e:
        return False, str(e)[:120]


def validate_redis_url(url: str) -> bool:
    import re
    import redis as redis_lib
    if not re.match(r"^rediss?://.*|^unix://.*", url):
        _err("Invalid format. Use redis://, rediss:// or unix://")
        print(f"  {_LINE}  {_DIM}e.g. redis://localhost:6379  |  rediss://user:pass@host:6380{_RST}")
        return False
    try:
        redis_lib.from_url(url, socket_connect_timeout=5).ping()
        return True
    except Exception as e:
        _err(f"Connection failed: {e}")
        return False


def validate_database_url(url: str) -> bool:
    import re
    if re.match(r"^(postgresql|postgres|mysql|sqlite)(\+\w+)?://.*", url):
        return True
    _err("Invalid format.")
    print(f"  {_LINE}  {_DIM}e.g. postgresql://user:pass@localhost:5432/db{_RST}")
    return False


def _apply_schema_directly(database_url: str) -> bool:
    sql_path = Path("scripts/schema.sql")
    if not sql_path.exists():
        return False
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        sql = sql_path.read_text()
        with engine.connect() as conn:
            for stmt in (s.strip() for s in sql.split(";")):
                if stmt and not stmt.startswith("--"):
                    conn.execute(text(stmt))
            conn.commit()
        engine.dispose()
        return True
    except Exception as e:
        _err(f"Failed to apply schema: {str(e)[:200]}")
        return False


def _gen_encryption_key() -> str:
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        import base64
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def _raise_init_flag() -> None:
    with open(".initialized", "w") as f:
        f.write("Setup completed. Delete this file to re-run setup.")


# ── Wizard ─────────────────────────────────────────────────────────────────────

def run_setup() -> None:
    database_url = db_user = db_password = db_name = ""
    webhook_url = internal_token = data_path = ""

    _step_counter[0] = 0
    _spinner.start()
    _header()

    # ── Step 0: Deploy target ──────────────────────────────────────────────────
    _step("Deploy target", "Where will this run?")
    _opt(1, "Local",  "run directly on this machine with uvicorn")
    _opt(2, "Docker", "generates Dockerfile + docker-compose.yml")
    while True:
        c = _ask("Option", "1")
        if c in DEPLOY_OPTIONS:
            deploy_target = DEPLOY_OPTIONS[c]
            break
        _err("Enter 1 or 2.")
    _done("deploy", deploy_target)
    is_docker = deploy_target == "docker"

    # ── Step 1: Auth mode ─────────────────────────────────────────────────────
    _step("Auth mode", "How will requests be authenticated?")
    _opt(1, "Standalone", "API authenticates via Bearer {agent_id}.{secret}")
    _opt(2, "Internal",   "behind Yopa Proxy — X-Agent-Id injected by the proxy")
    while True:
        c = _ask("Option", "1")
        if c in AUTH_MODE_OPTIONS:
            auth_mode = AUTH_MODE_OPTIONS[c]
            break
        _err("Enter 1 or 2.")
    _done("auth mode", auth_mode)

    if auth_mode == "internal":
        internal_token = secrets.token_hex(32)
        print(f"\n  {_WARN}  {_BOLD}INTERNAL_TOKEN generated — save this before continuing:{_RST}")
        print(f"\n       {_CYAN}{_BOLD}{internal_token}{_RST}\n")
        print(f"  {_LINE}  {_DIM}Copy this token to your Yopa Proxy configuration.{_RST}")
        print(f"  {_LINE}  {_DIM}Proxy setup must be done separately.{_RST}")
        input(f"  {_LINE}  {_ARROW}  Press Enter once you've saved it...  ")

    # ── Step 2: AI provider ───────────────────────────────────────────────────
    _step("AI provider", "Which provider's API will this agent use?")
    for k, p in PROVIDERS.items():
        _opt(k, p["name"])
    while True:
        c = _ask("Option")
        if c in PROVIDERS:
            provider_num = c
            provider = PROVIDERS[c]
            break
        _err("Invalid selection.")
    _done("provider", provider["name"])

    # ── Step 3: API key ────────────────────────────────────────────────────────
    _step("API key", f"Paste your {provider['name']} API key.")
    while True:
        api_key = _ask("API key")
        if not api_key:
            _err("API key cannot be empty.")
            continue
        print(f"  {_LINE}  {_DIM}Validating...{_RST} ", end="", flush=True)
        ok, err_msg = validate_api_key(provider_num, api_key)
        if ok:
            print(f"{_GRN}✓{_RST}")
            break
        print(f"{_RED}✗{_RST}")
        _err(err_msg)
    _done("key", f"{'•' * 8}{api_key[-4:]}")

    # ── Step 4: Model ─────────────────────────────────────────────────────────
    _step("Model", f"Which {provider['name']} model should this agent use?")
    models = provider["models"]
    for i, (model_id, desc) in enumerate(models, 1):
        _opt(i, model_id, desc)
    while True:
        c = _ask("Option")
        if c.isdigit() and 1 <= int(c) <= len(models):
            ai_model = models[int(c) - 1][0]
            break
        _err(f"Enter a number between 1 and {len(models)}.")
    _done("model", ai_model)

    # ── Step 5: AI timeout ────────────────────────────────────────────────────
    _step("AI timeout", "Max seconds to wait for a model response.")
    while True:
        timeout = _ask("Timeout in seconds", "30")
        if timeout.isdigit() and int(timeout) > 0:
            break
        _err("Enter a valid number.")
    _done("timeout", f"{timeout}s")

    # ── Step 6: Run mode ──────────────────────────────────────────────────────
    _step("Run mode")
    if is_docker:
        run_mode = "production"
        print(f"  {_LINE}  {_DIM}Docker deploy — RUN_MODE=production set automatically.{_RST}")
    else:
        _opt(1, "development", "auto-reload, debug logs")
        _opt(2, "production",  "optimized for live traffic")
        while True:
            run_mode = _ask("Mode")
            if run_mode in ("development", "production"):
                break
            _err("Enter 'development' or 'production'.")
    _done("run mode", run_mode)

    # ── Step 7: Port ──────────────────────────────────────────────────────────
    _step("Port", "Which port should the server listen on?")
    while True:
        port = _ask("Port", "8000")
        if port.isdigit() and 1 <= int(port) <= 65535:
            break
        _err("Invalid port.")
    _done("port", port)

    # ── Step 8: Storage ───────────────────────────────────────────────────────
    _step("Storage type", "Where should agent and session data be stored?")
    _opt(1, "Local",    "JSON files on disk")
    _opt(2, "Database", "PostgreSQL / MySQL / SQLite")
    _opt(3, "Webhook",  "persist via HTTP to an external endpoint")
    while True:
        c = _ask("Option", "1")
        if c not in STORAGE_OPTIONS:
            _err("Enter 1, 2 or 3.")
            continue
        storage_type = STORAGE_OPTIONS[c]

        if storage_type == "local":
            data_path = _ask("Data directory path", "./data")

        elif storage_type == "database":
            print(f"\n  {_LINE}  {_BOLD}Database configuration{_RST}")
            while True:
                database_url = _ask("Connection string (e.g. postgresql://user:pass@host:5432/db)")
                if not validate_database_url(database_url):
                    continue

                parsed     = urlparse(database_url)
                p_scheme   = parsed.scheme or "postgresql"
                p_user     = parsed.username or ""
                p_password = parsed.password or ""
                p_host     = parsed.hostname or "localhost"
                p_port     = str(parsed.port) if parsed.port else "5432"
                p_db       = parsed.path.lstrip("/")

                print(f"\n  {_LINE}  {_BOLD}Detected:{_RST}")
                print(f"  {_LINE}  {_DIM}user      {_RST}  {p_user or '(empty)'}")
                print(f"  {_LINE}  {_DIM}password  {_RST}  {'•' * len(p_password) if p_password else '(empty)'}")
                print(f"  {_LINE}  {_DIM}host      {_RST}  {p_host}")
                print(f"  {_LINE}  {_DIM}port      {_RST}  {p_port}")
                print(f"  {_LINE}  {_DIM}database  {_RST}  {p_db or '(empty)'}")

                confirm = _ask("Correct?", "yes").lower()
                if confirm not in ("yes", "y"):
                    print(f"\n  {_LINE}  {_DIM}Press Enter to keep the current value.{_RST}")
                    p_user     = _ask("User", p_user)
                    p_password = _ask("Password", p_password)
                    p_host     = _ask("Host", p_host)
                    p_port     = _ask("Port", p_port)
                    p_db       = _ask("Database", p_db)
                    database_url = f"{p_scheme}://{p_user}:{p_password}@{p_host}:{p_port}/{p_db}"

                db_user     = p_user
                db_password = p_password
                db_name     = p_db
                masked      = database_url.replace(p_password, "•" * len(p_password)) if p_password else database_url
                _done("connection string", masked)
                break

            print(f"\n  {_WARN}  {_DIM}Schema scripts are saved to{_RST}  {_CYAN}scripts/{_RST}  {_DIM}for two reasons:{_RST}")
            print(f"  {_LINE}  {_DIM}1. Docker: Postgres auto-applies schema.sql on the first container start{_RST}")
            print(f"  {_LINE}  {_DIM}2. Version control: track schema changes alongside your code{_RST}\n")

            while True:
                gen = _ask("Generate schema scripts?", "yes").lower()
                if gen in ("yes", "y"):
                    os.makedirs("scripts", exist_ok=True)
                    create_sql_scripts()
                    if not is_docker:
                        print(f"  {_LINE}  {_DIM}Applying schema to database...{_RST} ", end="", flush=True)
                        if _apply_schema_directly(database_url):
                            print(f"{_GRN}✓{_RST}")
                        else:
                            print(f"{_YLW}skipped{_RST}")
                            _warn("Apply manually: psql $DATABASE_URL -f scripts/schema.sql")
                    break
                elif gen in ("no", "n"):
                    _warn("Create the schema manually before starting.")
                    break
                _err("Enter 'yes' or 'no'.")

        elif storage_type == "webhook":
            webhook_url = _ask("Webhook URL (https://...)")

        break
    _done("storage", storage_type)

    # ── Step 9: Redis ─────────────────────────────────────────────────────────
    _step("Redis", "Used for context cache, session history, and NLP scores.")
    if is_docker:
        redis_default = "redis://redis:6379"
        redis_url = _ask("Redis URL", redis_default)
        _warn("Connection will not be tested (container not running yet).")
    else:
        while True:
            redis_url = _ask("Redis URL", "redis://localhost:6379")
            if validate_redis_url(redis_url):
                break
    _done("redis", redis_url)

    # ── Step 10: Session TTL ──────────────────────────────────────────────────
    _step("Session TTL", "How long should inactive sessions be kept in cache?")
    while True:
        session_ttl = _ask("TTL in seconds", "86400")
        if session_ttl.isdigit() and int(session_ttl) > 0:
            break
        _err("Enter a valid number.")
    _done("session TTL", f"{session_ttl}s")

    # ── Step 11: Encryption key ───────────────────────────────────────────────
    _step("Encryption key", "Encrypts per-agent API keys (BYOK) and SQL connection strings.")
    encryption_key = _gen_encryption_key()
    print(f"\n  {_WARN}  {_BOLD}Back up this key — losing it makes all stored secrets unrecoverable:{_RST}")
    print(f"\n       {_CYAN}{_BOLD}{encryption_key}{_RST}\n")
    input(f"  {_LINE}  {_ARROW}  Press Enter once you've saved it...  ")
    _done("encryption key", "generated ✓")

    # ── Step 12: Tool settings ────────────────────────────────────────────────
    _step("Tool settings", "Limits for AI tool-use and SQL queries.")
    while True:
        max_tool_rounds = _ask("Max tool-use rounds per message", "5")
        if max_tool_rounds.isdigit() and int(max_tool_rounds) > 0:
            break
        _err("Enter a valid number.")
    while True:
        sql_timeout = _ask("SQL query timeout (seconds)", "10")
        if sql_timeout.isdigit() and int(sql_timeout) > 0:
            break
        _err("Enter a valid number.")
    while True:
        sql_max_rows = _ask("Max rows per SQL query", "50")
        if sql_max_rows.isdigit() and int(sql_max_rows) > 0:
            break
        _err("Enter a valid number.")
    _done("tools", f"rounds={max_tool_rounds}  sql_timeout={sql_timeout}s  max_rows={sql_max_rows}")

    # ── Step 13: NLP analyzer languages ──────────────────────────────────────
    _step("NLP analyzer languages", "English is always included. Select additional languages:")
    for k, (code, name) in ANALYZER_LANGUAGE_OPTIONS.items():
        _opt(k, name, code)
    analyzer_languages = ["en"]
    while True:
        raw = _ask("Languages (comma-separated numbers)", "none")
        if not raw or raw.lower() == "none":
            break
        selections = [s.strip() for s in raw.split(",")]
        invalid = [s for s in selections if s not in ANALYZER_LANGUAGE_OPTIONS]
        if invalid:
            _err(f"Invalid options: {', '.join(invalid)}.")
            continue
        selected_codes = [ANALYZER_LANGUAGE_OPTIONS[s][0] for s in selections]
        analyzer_languages += selected_codes
        print(f"  {_LINE}  {_DIM}Downloading packages: {', '.join(selected_codes)} → en{_RST}")
        try:
            from argostranslate import package as argo_pkg
            argo_pkg.update_package_index()
            available = argo_pkg.get_available_packages()
            for code in selected_codes:
                pkg = next((p for p in available if p.from_code == code and p.to_code == "en"), None)
                if pkg:
                    argo_pkg.install_from_path(pkg.download())
                    _ok(f"{code} → en installed.")
                else:
                    _err(f"Package {code} → en not found.")
        except Exception as e:
            _warn(f"Could not download packages: {e}")
        break
    _done("NLP languages", ", ".join(analyzer_languages))

    # ── Step 14: Log level ────────────────────────────────────────────────────
    _step("Log level", "Verbosity of server logs.")
    for k, lvl in LOG_LEVEL_OPTIONS.items():
        _opt(k, lvl)
    while True:
        c = _ask("Option", "2")
        if c in LOG_LEVEL_OPTIONS:
            log_level = LOG_LEVEL_OPTIONS[c]
            break
        _err("Invalid option.")
    _done("log level", log_level)

    # ── Write .env ─────────────────────────────────────────────────────────────
    print(f"\n  {_DOT}  {_BOLD}Writing .env...{_RST}")
    app_version = Path("VERSION").read_text().strip() if Path("VERSION").exists() else "0.1.0"
    lines = [
        f"APP_VERSION={app_version}",
        f"AI_API_KEY={api_key}",
        f"AI_MODEL={ai_model}",
        f"AI_TIMEOUT={timeout}",
        f"RUN_MODE={run_mode}",
        f"PORT={port}",
        f"STORAGE_TYPE={storage_type}",
    ]
    if storage_type == "local":
        lines.append(f"DATA_PATH={data_path}")
    elif storage_type == "database":
        lines += [
            f"DATABASE_URL={database_url}",
            f"DB_USER={db_user}",
            f"DB_PASSWORD={db_password}",
            f"DB_NAME={db_name}",
            f"DB_PORT={p_port}",
        ]
    elif storage_type == "webhook":
        lines.append(f"WEBHOOK_URL={webhook_url}")
    lines += [
        f"REDIS_URL={redis_url}",
        f"SESSION_TTL={session_ttl}",
        f"AUTH_MODE={auth_mode}",
    ]
    if auth_mode == "internal":
        lines.append(f"INTERNAL_TOKEN={internal_token}")
    lines += [
        f"SQL_ENCRYPTION_KEY={encryption_key}",
        f"MAX_TOOL_ROUNDS={max_tool_rounds}",
        f"SQL_QUERY_TIMEOUT={sql_timeout}",
        f"SQL_MAX_ROWS={sql_max_rows}",
        f"ANALYZER_LANGUAGES={json.dumps(analyzer_languages)}",
        f"LOG_LEVEL={log_level}",
    ]
    with open(".env", "w") as f:
        f.write("\n".join(lines) + "\n")
    _ok(".env written.")

    # ── Docker files ───────────────────────────────────────────────────────────
    if is_docker:
        print(f"\n  {_DOT}  {_BOLD}Generating Docker files...{_RST}")
        if Path("Dockerfile").exists():
            overwrite = _ask("Dockerfile already exists. Overwrite?", "no").lower()
            if overwrite in ("yes", "y"):
                generate_dockerfile(port)
                _ok("Dockerfile generated.")
            else:
                print(f"  {_LINE}  {_DIM}Dockerfile kept as-is.{_RST}")
        else:
            generate_dockerfile(port)
            _ok("Dockerfile generated.")
        generate_docker_compose(port, storage_type)
        _ok("docker-compose.yml generated.")

        print(f"\n  {_DOT}  {_BOLD}Starting Docker containers...{_RST}")
        import subprocess
        version = Path("VERSION").read_text().strip() if Path("VERSION").exists() else "latest"
        image_tag = f"ai-chatbot-api:{version}"
        image_check = subprocess.run(
            ["docker", "images", "-q", image_tag],
            capture_output=True, text=True,
        )
        if image_check.stdout.strip():
            print(f"  {_LINE}  {_DIM}Image {image_tag} already up to date — skipping build.{_RST}")
            build_flag = []
        else:
            print(f"  {_LINE}  {_DIM}Image {image_tag} not found — building.{_RST}")
            build_flag = ["--build"]
        cmd = ["docker", "compose", "up"] + build_flag + ["-d"]
        print(f"  {_LINE}  {_DIM}Running: {' '.join(cmd)}{_RST}\n")
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print()
            _done("containers", "up and running ✓")
            print(f"\n  {_LINE}  {_DIM}API available at{_RST}  {_CYAN}http://localhost:{port}{_RST}")
            if storage_type == "database":
                print(f"  {_LINE}  {_DIM}Database schema applied automatically on first start.{_RST}")
            print(f"  {_LINE}  {_DIM}View logs:{_RST}  {_CYAN}docker compose logs -f api{_RST}")
            print(f"  {_LINE}  {_DIM}Stop:{_RST}  {_CYAN}docker compose down{_RST}")

            if build_flag:
                old_out = subprocess.run(
                    ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}", "ai-chatbot-api"],
                    capture_output=True, text=True,
                ).stdout.strip()
                old_lines = [
                    l for l in old_out.splitlines()
                    if l and not l.startswith(f"ai-chatbot-api:{version}\t")
                ]
                if old_lines:
                    print(f"\n  {_WARN}  {len(old_lines)} old image(s) found (keeping them allows rollback):")
                    for line in old_lines:
                        tag, img_id = line.split("\t", 1)
                        print(f"  {_LINE}  {_DIM}{tag}   {img_id[:12]}{_RST}")
                    clean = _ask("Remove old images?", "no").lower()
                    if clean in ("yes", "y"):
                        for line in old_lines:
                            tag, img_id = line.split("\t", 1)
                            subprocess.run(["docker", "rmi", img_id], capture_output=True)
                            _ok(f"Removed {tag}")
                    else:
                        print(f"  {_LINE}  {_DIM}Kept. Remove manually: docker rmi <image-id>{_RST}")
        else:
            print()
            _err("docker compose failed. Check the output above for details.")

    _raise_init_flag()

    _spinner.finish()
    print(f"\n  {_DONE}  {_BOLD}Setup complete!{_RST}  {_DIM}Run{_RST}  {_CYAN}uvicorn main:app --reload{_RST}  {_DIM}to start the server.{_RST}\n")


if __name__ == "__main__":
    run_setup()
