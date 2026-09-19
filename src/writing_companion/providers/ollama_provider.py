"""Local Ollama provider for offline resilience and privacy-first local inference."""

import json
import httpx
from writing_companion.providers.base import BaseProvider
from writing_companion.core.schema import SingleInferenceResponse
from writing_companion.core.prompt import SYSTEM_PROMPT


class OllamaProvider(BaseProvider):
    """Ollama local server provider using Ollama's native REST API with JSON mode."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host.rstrip("/")
        self.model = model
        self.chat_url = f"{self.host}/api/chat"
        self.tags_url = f"{self.host}/api/tags"

    @property
    def name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        """Check if local Ollama daemon is currently running and reachable."""
        try:
            async with httpx.AsyncClient(timeout=0.8) as client:
                resp = await client.get(self.tags_url)
                return resp.status_code == 200
        except Exception:
            return False

    async def generate_correction(self, text: str) -> SingleInferenceResponse:
        payload = {
            "model": self.model,
            "format": "json",
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "options": {
                "temperature": 0.2,
            },
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(self.chat_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["message"]["content"]
        parsed = json.loads(content)
        return SingleInferenceResponse(**parsed)
