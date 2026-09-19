"""Unit tests for system prompt guardrails and operating principles (ADR-01, ADR-02, ADR-03)."""

from writing_companion.core.prompt import SYSTEM_PROMPT


def test_system_prompt_principles():
    """Verify that all core constitutional principles are explicitly mandated in prompt."""
    prompt = SYSTEM_PROMPT.upper()

    # Principle I: Minimal Intervention & Code Freeze
    assert "MINIMAL INTERVENTION" in prompt
    assert "CODE FREEZE" in prompt
    assert "NEVER MODIFY, RENAME, TRANSLATE" in prompt

    # Principle II: Semantic Checkpoint
    assert "PERSIAN SEMANTIC CHECKPOINT" in prompt
    assert "INTERPRETED_MEANING_FA" in prompt

    # Principle III: Tolerance for Hybrid & Bracketed Inputs
    assert "BRACKET_TRANSLATION" in prompt
    assert "BRACKETED" in prompt

    # Principle IV: Single-Inference JSON schema
    assert "IS_CORRECT" in prompt
    assert "CORRECTED_TEXT" in prompt
    assert "CHANGES" in prompt
