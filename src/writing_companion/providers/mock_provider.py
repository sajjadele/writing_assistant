"""Offline mock provider for deterministic testing and instant desktop validation."""

import re
from typing import Optional
from writing_companion.providers.base import BaseProvider
from writing_companion.core.schema import SingleInferenceResponse, ChangeItem


class MockProvider(BaseProvider):
    """Deterministic fixture-based provider for offline tests and prototype verification."""

    @property
    def name(self) -> str:
        return "mock"

    async def is_available(self) -> bool:
        return True

    async def generate_correction(self, text: str) -> SingleInferenceResponse:
        cleaned = text.strip()

        # Fixture 1: Adapt / Compatibility hybrid with bracket
        if "[سازگار کنیم]" in cleaned:
            return SingleInferenceResponse(
                is_correct=False,
                interpreted_meaning_fa="آیا می‌توانیم این تابع را با API جدید سازگار کنیم؟",
                corrected_text="Can we adapt this function to the new API?",
                changes=[
                    ChangeItem(
                        original="[سازگار کنیم]",
                        replacement="adapt",
                        category="bracket_translation",
                        explanation_fa="معادل مناسب فنی در زمینه هماهنگ‌سازی کدها.",
                    ),
                    ChangeItem(
                        original="with new",
                        replacement="to the new",
                        category="grammar",
                        explanation_fa="حرف اضافه مناسب برای فعل adapt در این بافت to است.",
                    ),
                ],
            )

        # Fixture 2: Latency bottleneck investigation
        if "[بررسی کنیم]" in cleaned:
            return SingleInferenceResponse(
                is_correct=False,
                interpreted_meaning_fa="ما باید گلوگاه تاخیر را بررسی کنیم.",
                corrected_text="We should investigate the latency bottleneck.",
                changes=[
                    ChangeItem(
                        original="[بررسی کنیم]",
                        replacement="investigate",
                        category="bracket_translation",
                        explanation_fa="معادل دقیق فنی برای بازرسی یا ریشه‌یابی مشکلات عملکردی.",
                    )
                ],
            )

        # Fixture 3: Perfect input (No Change Needed check)
        if "resolves the memory leak" in cleaned.lower() or "perfect" in cleaned.lower():
            return SingleInferenceResponse(
                is_correct=True,
                interpreted_meaning_fa="این درخواست ادغام، نشت حافظه را برطرف می‌کند.",
                corrected_text=cleaned,
                changes=[],
            )

        # Generic Bracket Replacement
        bracket_match = re.search(r"\[(.*?)\]", cleaned)
        if bracket_match:
            persian_word = bracket_match.group(1)
            corrected = re.sub(r"\[(.*?)\]", "resolve", cleaned)
            return SingleInferenceResponse(
                is_correct=False,
                interpreted_meaning_fa=f"بررسی منظور در عبارت: {persian_word}",
                corrected_text=corrected,
                changes=[
                    ChangeItem(
                        original=f"[{persian_word}]",
                        replacement="resolve",
                        category="bracket_translation",
                        explanation_fa="ترجمه عبارت داخل براکت با توجه به بافت جمله.",
                    )
                ],
            )

        # Default Mock Correction
        return SingleInferenceResponse(
            is_correct=False,
            interpreted_meaning_fa=f"منظور از جمله: {cleaned[:40]}...",
            corrected_text=f"{cleaned.capitalize()}.",
            changes=[
                ChangeItem(
                    original=cleaned,
                    replacement=f"{cleaned.capitalize()}.",
                    category="grammar",
                    explanation_fa="تصحیح نگارشی و علائم انتهای جمله.",
                )
            ],
        )
