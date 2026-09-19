"""Unit tests for contract schema validation (contracts/single-inference-json.json)."""

import pytest
from pydantic import ValidationError
from writing_companion.core.schema import SingleInferenceResponse, ChangeItem


def test_valid_single_inference_response():
    data = {
        "is_correct": False,
        "interpreted_meaning_fa": "آیا می‌توان این تابع را بازنویسی کرد؟",
        "corrected_text": "Can we refactor this function?",
        "changes": [
            {
                "original": "rewrite",
                "replacement": "refactor",
                "category": "word_choice",
                "explanation_fa": "اصطلاح استاندارد در مهندسی نرم‌افزار.",
            }
        ],
    }
    resp = SingleInferenceResponse(**data)
    assert resp.is_correct is False
    assert resp.corrected_text == "Can we refactor this function?"
    assert len(resp.changes) == 1
    assert resp.changes[0].category == "word_choice"


def test_no_change_needed_response():
    data = {
        "is_correct": True,
        "interpreted_meaning_fa": "این تست بدون خطا اجرا می‌شود.",
        "corrected_text": "This test runs without errors.",
        "changes": [],
    }
    resp = SingleInferenceResponse(**data)
    assert resp.is_correct is True
    assert resp.changes == []


def test_invalid_category_rejection():
    data = {
        "original": "foo",
        "replacement": "bar",
        "category": "invalid_category_name",
        "explanation_fa": "تست",
    }
    with pytest.raises(ValidationError):
        ChangeItem(**data)


def test_missing_required_fields():
    with pytest.raises(ValidationError):
        SingleInferenceResponse(is_correct=False)
