"""Core orchestrator coordinating provider dispatch, validation, latency tracking, and storage."""

import time
from typing import Optional, Dict, Any, Tuple
from writing_companion.config import Settings
from writing_companion.core.schema import SingleInferenceResponse
from writing_companion.providers.base import BaseProvider
from writing_companion.providers.mock_provider import MockProvider
from writing_companion.storage.sqlite_store import SQLiteStore


class Engine:
    """Central processing engine for Writing Companion."""

    def __init__(self, settings: Settings, store: SQLiteStore):
        self.settings = settings
        self.store = store
        self.providers: Dict[str, BaseProvider] = {
            "mock": MockProvider(),
        }

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a provider instance."""
        self.providers[provider.name] = provider

    async def _resolve_provider(self, preferred: str) -> BaseProvider:
        """Select appropriate provider based on user preference and availability."""
        if preferred and preferred != "auto" and preferred in self.providers:
            provider = self.providers[preferred]
            if await provider.is_available():
                return provider

        # Auto fallback cascade: groq -> gemini -> ollama -> mock
        for candidate_name in ("groq", "gemini", "ollama"):
            if candidate_name in self.providers:
                cand = self.providers[candidate_name]
                if await cand.is_available():
                    return cand

        # Default fallback to mock provider
        return self.providers["mock"]

    async def process_text(
        self,
        text: str,
        preferred_backend: str = "auto",
    ) -> Tuple[SingleInferenceResponse, int, str, int]:
        """
        Process user text, measure execution duration, persist event, and return result.
        Returns: (SingleInferenceResponse, event_id, backend_name, duration_ms)
        """
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Input text cannot be empty.")

        provider = await self._resolve_provider(preferred_backend)
        start_time = time.perf_counter()

        response = await provider.generate_correction(cleaned)
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        changes_list = [c.model_dump() for c in response.changes]
        event_id = self.store.record_event(
            original_text=cleaned,
            interpreted_meaning_fa=response.interpreted_meaning_fa,
            corrected_text=response.corrected_text,
            is_correct=response.is_correct,
            changes=changes_list,
            source_backend=provider.name,
            duration_ms=duration_ms,
            accepted=False,
        )

        return response, event_id, provider.name, duration_ms

    def update_feedback(self, event_id: int, accepted: bool) -> bool:
        """Update acceptance signal (1 on Enter, 0 on dismissal)."""
        return self.store.update_acceptance(event_id=event_id, accepted=accepted)
