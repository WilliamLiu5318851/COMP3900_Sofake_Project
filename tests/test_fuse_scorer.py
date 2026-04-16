"""
test_fuse_scorer.py

Tests for FUSE/evaluation/fuse_scorer.py.

Changes from the original teammate version:
  - API: switched to the current LLM SDK (client.messages.create / response.content[0].text)
  - Dimensions: 6 → 9  (added SI, SAA, PIB)
  - Output: Total_Deviation (avg of 6 core) + Extended_Deviation (avg of all 9)
  - Missing-key guard: model omissions are filled with 0.0
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from FUSE.evaluation.fuse_scorer import FUSEScoringSystem

CORE_DIMS    = ["SS", "NII", "CS", "STS", "TS", "PD"]
EXTENDED_DIMS = CORE_DIMS + ["SI", "SAA", "PIB"]


@pytest.fixture
def evaluator():
    """Initialise with a dummy key — API calls are always mocked in these tests."""
    return FUSEScoringSystem(api_key="mock-key-for-testing")


def _make_mock_response(scores_dict: dict) -> MagicMock:
    """Helper: build a fake LLM response whose .content[0].text is the JSON."""
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(scores_dict))]
    return mock_resp


# ── Happy-path tests ────────────────────────────────────────────────────────────

def test_all_9_dimensions_returned(evaluator):
    """All 9 dimension keys plus Total_Deviation and Extended_Deviation must appear."""
    mock_scores = {
        "SS": 8.0, "NII": 7.0, "CS": 6.0, "STS": 9.0,
        "TS": 5.0, "PD": 7.0, "SI": 8.5, "SAA": 6.5, "PIB": 7.5,
    }
    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(mock_scores)):
        result = evaluator.evaluate_news("original news", "evolved news")

    assert set(EXTENDED_DIMS).issubset(result.keys())
    assert "Total_Deviation" in result
    assert "Extended_Deviation" in result


def test_total_deviation_uses_6_core_dims(evaluator):
    """
    Total_Deviation must equal the average of the 6 FUSE-paper core dimensions,
    NOT all 9.  Paper formula: TD = (1/6) * Σ D_i,d
    """
    mock_scores = {
        "SS": 8.0, "NII": 7.0, "CS": 6.0, "STS": 9.0,
        "TS": 5.0, "PD": 7.0,
        "SI": 0.0, "SAA": 0.0, "PIB": 0.0,   # extended dims at 0
    }
    expected_td = round((8.0 + 7.0 + 6.0 + 9.0 + 5.0 + 7.0) / 6, 2)  # 7.0

    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(mock_scores)):
        result = evaluator.evaluate_news("original news", "evolved news")

    assert result["Total_Deviation"] == expected_td


def test_extended_deviation_uses_all_9_dims(evaluator):
    """Extended_Deviation is the average of all 9 dimensions."""
    mock_scores = {
        "SS": 9.0, "NII": 9.0, "CS": 9.0, "STS": 9.0,
        "TS": 9.0, "PD": 9.0, "SI": 0.0, "SAA": 0.0, "PIB": 0.0,
    }
    expected_ext = round(sum(mock_scores.values()) / 9, 2)  # (54/9) = 6.0

    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(mock_scores)):
        result = evaluator.evaluate_news("original news", "evolved news")

    assert result["Extended_Deviation"] == expected_ext


def test_scores_rounded_to_2_decimal_places(evaluator):
    """Every numeric score in the result must have at most 2 decimal places."""
    mock_scores = {k: 7.123456 for k in EXTENDED_DIMS}

    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(mock_scores)):
        result = evaluator.evaluate_news("original news", "evolved news")

    for key in EXTENDED_DIMS:
        val = result[key]
        assert val == round(val, 2), f"{key} not rounded: {val}"


def test_baseline_identical_text_scores_zero(evaluator):
    """When evolved == original, a well-calibrated scorer should return all zeros."""
    mock_scores = {k: 0.0 for k in EXTENDED_DIMS}

    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(mock_scores)):
        result = evaluator.evaluate_news("same text", "same text")

    assert result["Total_Deviation"] == 0.0
    assert result["Extended_Deviation"] == 0.0


# ── Robustness / edge-case tests ────────────────────────────────────────────────

def test_missing_key_filled_with_zero(evaluator):
    """If the model omits a dimension, it should be filled with 0.0 (not crash)."""
    incomplete_scores = {
        "SS": 8.0, "NII": 7.0, "CS": 6.0, "STS": 9.0, "TS": 5.0, "PD": 7.0,
        # SI, SAA, PIB intentionally missing
    }
    with patch.object(evaluator.client.messages, "create",
                      return_value=_make_mock_response(incomplete_scores)):
        result = evaluator.evaluate_news("original news", "evolved news")

    # Missing keys must be present and set to 0.0
    assert result["SI"]  == 0.0
    assert result["SAA"] == 0.0
    assert result["PIB"] == 0.0
    assert "Total_Deviation" in result


def test_error_handling_returns_empty_dict(evaluator):
    """If the API raises an exception, evaluate_news must return {} gracefully."""
    with patch.object(evaluator.client.messages, "create",
                      side_effect=Exception("API Timeout")):
        result = evaluator.evaluate_news("original", "evolved")

    assert result == {}


def test_markdown_fenced_json_is_parsed(evaluator):
    """The scorer must strip ```json ... ``` fences that the model sometimes adds."""
    raw_scores = {k: 5.0 for k in EXTENDED_DIMS}
    fenced_text = "```json\n" + json.dumps(raw_scores) + "\n```"

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=fenced_text)]

    with patch.object(evaluator.client.messages, "create", return_value=mock_resp):
        result = evaluator.evaluate_news("original news", "evolved news")

    assert result["SS"] == 5.0
    assert "Total_Deviation" in result
