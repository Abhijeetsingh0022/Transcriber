"""
Unit and regression tests for Token Harbor 3rd fallback AI integration in TMUX.
Validates:
1. API key resolution and aliases.
2. AI status telemetry reporting.
3. Unified OpenAI-compatible executor logic.
4. Circuit breaker activation and dynamic Retry-After parsing.
5. Quarantine of revoked keys (401/403).
6. Complete multi-tier failover degradation.
"""

import os
import time
import io
import json
import urllib.error
import urllib.response
from unittest.mock import patch, MagicMock

from engine import ai_client
from engine.ai_client import (
    get_tokenharbor_api_key,
    get_ai_status,
    call_ai_json,
    _execute_tokenharbor_call,
    _COOLDOWNS,
    _DISABLED_PROVIDERS,
    _AI_CACHE,
)


def test_tokenharbor_api_key_resolution():
    """Validates resolution of TOKENHARBOR_API_KEY and alias TOKEN_HARBOR_API_KEY."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ, {}, clear=True):
            assert get_tokenharbor_api_key() is None

        with patch.dict(os.environ, {"TOKENHARBOR_API_KEY": "thk_live_test_123"}, clear=True):
            assert get_tokenharbor_api_key() == "thk_live_test_123"

        with patch.dict(os.environ, {"TOKEN_HARBOR_API_KEY": "thk_alias_456"}, clear=True):
            assert get_tokenharbor_api_key() == "thk_alias_456"


def test_get_ai_status_telemetry():
    """Validates telemetry reporting for Token Harbor in get_ai_status()."""
    _COOLDOWNS["tokenharbor"] = 0.0
    _DISABLED_PROVIDERS.discard("tokenharbor")

    with patch.dict(os.environ, {"TOKENHARBOR_API_KEY": "thk_live_status_test"}):
        status = get_ai_status()
        assert "tokenharbor" in status
        assert status["tokenharbor"]["configured"] is True
        assert status["tokenharbor"]["disabled"] is False
        assert status["tokenharbor"]["cooling_down"] is False
        assert status["tokenharbor"]["cooldown_remaining_sec"] == 0

    # Test cooldown telemetry
    _COOLDOWNS["tokenharbor"] = time.time() + 45.0
    with patch.dict(os.environ, {"TOKENHARBOR_API_KEY": "thk_live_status_test"}):
        status = get_ai_status()
        assert status["tokenharbor"]["cooling_down"] is True
        assert status["tokenharbor"]["cooldown_remaining_sec"] > 40
    _COOLDOWNS["tokenharbor"] = 0.0


def test_tokenharbor_retry_after_header_handling():
    """Validates that HTTP 429 correctly extracts Retry-After header and activates cooldown."""
    _COOLDOWNS["tokenharbor"] = 0.0
    _DISABLED_PROVIDERS.discard("tokenharbor")

    # Mock HTTP 429 response with Retry-After: 35
    mock_headers = {"Retry-After": "35"}
    error_429 = urllib.error.HTTPError(
        url="https://tokenharbor.ai/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=mock_headers,
        fp=io.BytesIO(b'{"error": "rate_limit_exceeded"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error_429):
        result = _execute_tokenharbor_call("test prompt", "thk_key")
        assert result is None
        # Cooldown should be approximately current time + 35s
        remaining = _COOLDOWNS["tokenharbor"] - time.time()
        assert 30 <= remaining <= 36

    _COOLDOWNS["tokenharbor"] = 0.0


def test_tokenharbor_auth_failure_quarantine():
    """Validates that HTTP 401/403 places Token Harbor into _DISABLED_PROVIDERS."""
    _DISABLED_PROVIDERS.discard("tokenharbor")

    error_401 = urllib.error.HTTPError(
        url="https://tokenharbor.ai/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"error": "invalid_api_key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error_401):
        result = _execute_tokenharbor_call("test prompt", "thk_bad_key")
        assert result is None
        assert "tokenharbor" in _DISABLED_PROVIDERS

    _DISABLED_PROVIDERS.discard("tokenharbor")


def test_tokenharbor_successful_structured_json():
    """Validates successful response extraction and parsing from Token Harbor."""
    _COOLDOWNS["tokenharbor"] = 0.0
    _DISABLED_PROVIDERS.discard("tokenharbor")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": '```json\n{"status": "success", "topics": ["Introduction", "Demo"]}\n```'
                }
            }
        ]
    }
    raw_bytes = json.dumps(mock_response_data).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_bytes
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = _execute_tokenharbor_call("Analyze topics", "thk_good_key")
        assert res is not None
        assert res.get("status") == "success"
        assert len(res.get("topics", [])) == 2


def test_call_ai_json_tier3_failover():
    """
    Validates complete failover chain:
    Gemini fails -> OpenRouter fails -> Token Harbor succeeds -> tagged as 'tokenharbor'.
    """
    _AI_CACHE.clear()
    _COOLDOWNS["gemini"] = time.time() + 60.0  # Gemini cooling down
    _COOLDOWNS["openrouter"] = time.time() + 60.0  # OpenRouter cooling down
    _COOLDOWNS["tokenharbor"] = 0.0
    _DISABLED_PROVIDERS.clear()

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"engine": "tokenharbor_pass", "confidence": 0.98})
                }
            }
        ]
    }
    raw_bytes = json.dumps(mock_response_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_bytes
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    with patch.dict(os.environ, {"TOKENHARBOR_API_KEY": "thk_mock_key"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res, provider = call_ai_json("classify this section", task_tag="unit_test")
            assert provider == "tokenharbor"
            assert res is not None
            assert res.get("engine") == "tokenharbor_pass"

    # Reset state
    _COOLDOWNS["gemini"] = 0.0
    _COOLDOWNS["openrouter"] = 0.0
    _COOLDOWNS["tokenharbor"] = 0.0
    _AI_CACHE.clear()


if __name__ == "__main__":
    print("Running Token Harbor fallback test suite...")
    test_tokenharbor_api_key_resolution()
    print(" API Key resolution passed")
    test_get_ai_status_telemetry()
    print(" Status telemetry passed")
    test_tokenharbor_retry_after_header_handling()
    print(" Retry-After 429 circuit breaker passed")
    test_tokenharbor_auth_failure_quarantine()
    print(" Auth failure quarantine passed")
    test_tokenharbor_successful_structured_json()
    print(" JSON parse & extraction passed")
    test_call_ai_json_tier3_failover()
    print(" Tier 3 failover progression passed")
    print("\nALL TOKEN HARBOR TESTS PASSED!")
