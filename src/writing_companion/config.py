"""Configuration management for Writing Companion."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict

USER_CONFIG_DIR = Path(os.path.expanduser("~/.config/writing_companion"))
USER_CONFIG_FILE = USER_CONFIG_DIR / "settings.json"


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from user config, environment or defaults."""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ai_provider: str = "auto"
    proxy: str = ""
    
    # Storage
    db_path: Path = Path(os.path.expanduser("~/.local/share/writing_companion/history.db"))
    
    # Providers config
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Timeout
    timeout_ms: int = 7000


def save_user_settings(data: dict) -> None:
    """Persist user settings to ~/.config/writing_companion/settings.json."""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if USER_CONFIG_FILE.is_file():
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing.update(data)
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def load_settings() -> Settings:
    """Load settings with priority: settings.json > environment variables > .env > defaults."""
    # 1. Read .env file if available
    env_file = Path(".env")
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

    # 2. Read user settings.json
    user_conf = {}
    if USER_CONFIG_FILE.is_file():
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
        except Exception:
            user_conf = {}

    groq_key = user_conf.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
    gemini_key = user_conf.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    provider = user_conf.get("ai_provider") or os.getenv("AI_PROVIDER", "auto")
    groq_model = user_conf.get("groq_model") or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    gemini_model = user_conf.get("gemini_model") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    ollama_host = user_conf.get("ollama_host") or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = user_conf.get("ollama_model") or os.getenv("OLLAMA_MODEL", "llama3.2")
    
    db_path_str = user_conf.get("db_path") or os.getenv("DB_PATH", "~/.local/share/writing_companion/history.db")
    db_path = Path(os.path.expanduser(db_path_str))

    proxy = user_conf.get("proxy") or os.getenv("PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY") or ""
    if not proxy:
        try:
            from gi.repository import Gio
            gsettings = Gio.Settings.new("org.gnome.system.proxy")
            if gsettings.get_string("mode") == "manual":
                http_settings = Gio.Settings.new("org.gnome.system.proxy.http")
                host = http_settings.get_string("host")
                port = http_settings.get_int("port")
                if host and port:
                    proxy = f"http://{host}:{port}"
        except Exception:
            pass

    if not proxy:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                if s.connect_ex(("127.0.0.1", 10808)) == 0:
                    proxy = "http://127.0.0.1:10808"
        except Exception:
            pass

    if proxy:
        if "HTTP_PROXY" not in os.environ and "http_proxy" not in os.environ:
            os.environ["HTTP_PROXY"] = proxy
            os.environ["http_proxy"] = proxy
        if "HTTPS_PROXY" not in os.environ and "https_proxy" not in os.environ:
            os.environ["HTTPS_PROXY"] = proxy
            os.environ["https_proxy"] = proxy

    return Settings(
        groq_api_key=groq_key,
        gemini_api_key=gemini_key,
        ai_provider=provider,
        proxy=proxy,
        db_path=db_path,
        groq_model=groq_model,
        gemini_model=gemini_model,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
        timeout_ms=int(user_conf.get("timeout_ms") or os.getenv("TIMEOUT_MS", "7000")),
    )
