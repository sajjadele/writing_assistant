"""Google Gemini Flash provider for high-speed single-inference LLM execution."""

import json
import httpx
from writing_companion.providers.base import BaseProvider
from writing_companion.core.schema import SingleInferenceResponse
from writing_companion.core.prompt import SYSTEM_PROMPT


class GeminiProvider(BaseProvider):
    """Gemini 2.0 Flash provider using direct REST API with JSON schema enforcement."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key.strip()
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    @property
    def name(self) -> str:
        return "gemini"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_correction(self, text: str) -> SingleInferenceResponse:
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": text}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 1000,
            },
        }

        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(self.url, params=params, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        raw_text = candidates[0]["content"]["parts"][0]["text"]
        parsed_json = json.loads(raw_text)
        return SingleInferenceResponse(**parsed_json)
