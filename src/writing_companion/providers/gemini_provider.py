"""Google Gemini Flash provider for high-speed single-inference LLM execution."""

import json
import httpx
from writing_companion.providers.base import BaseProvider
from writing_companion.core.schema import SingleInferenceResponse
from writing_companion.core.prompt import SYSTEM_PROMPT


class GeminiProvider(BaseProvider):
    """Gemini 2.0 Flash provider using direct REST API with JSON schema enforcement."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite", proxy: str = ""):
        self.api_key = api_key.strip()
        self.model = model
        self.proxy = proxy.strip() if proxy else None
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

        client_kwargs = {"timeout": 25.0}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.post(self.url, params=params, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p["text"] for p in parts if "text" in p and p["text"]]
        if not text_parts:
            raise RuntimeError("Gemini returned no text content.")

        raw_text = text_parts[-1].strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed_json = json.loads(raw_text.strip())
        return SingleInferenceResponse(**parsed_json)
