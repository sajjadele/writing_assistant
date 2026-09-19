"""Configuration management for Writing Companion."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment or defaults."""
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    ai_provider: str = os.getenv("AI_PROVIDER", "auto")
    
    # Storage
    db_path: Path = Path(
        os.path.expanduser(
            os.getenv("DB_PATH", "~/.local/share/writing_companion/history.db")
        )
    )
    
    # Providers config
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Timeout
    timeout_ms: int = int(os.getenv("TIMEOUT_MS", "4500"))


def load_settings() -> Settings:
    """Load settings with automatic .env discovery."""
    # Attempt simple .env read if file exists
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

    return Settings()
