"""Abstract base class for LLM providers (Cloud & Local)."""

from abc import ABC, abstractmethod
from writing_companion.core.schema import SingleInferenceResponse


class BaseProvider(ABC):
    """Abstract interface for writing assistant providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'groq', 'gemini', 'ollama', 'mock')."""
        pass

    @abstractmethod
    async def generate_correction(self, text: str) -> SingleInferenceResponse:
        """Evaluate text and return single-inference structured response."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider credentials/endpoint are currently accessible."""
        pass
