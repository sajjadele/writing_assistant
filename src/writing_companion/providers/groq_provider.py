"""Groq Cloud Provider for sub-300ms single-inference LLM execution (Llama 3.3 70B)."""

import json
import httpx
from writing_companion.providers.base import BaseProvider
from writing_companion.core.schema import SingleInferenceResponse
from writing_companion.core.prompt import SYSTEM_PROMPT


class GroqProvider(BaseProvider):
    """Groq API provider with structured JSON mode and ultra-low TTFT."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key.strip()
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def name(self) -> str:
        return "groq"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_correction(self, text: str) -> SingleInferenceResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 1000,
        }

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_content = data["choices"][0]["message"]["content"]
        parsed_json = json.loads(raw_content)
        return SingleInferenceResponse(**parsed_json)
