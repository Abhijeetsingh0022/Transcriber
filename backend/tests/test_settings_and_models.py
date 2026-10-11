"""
Unit tests for Settings Service, Model Service, and /api/settings endpoints.
Tests key-value persistence, API key masking, offline validation, and model registry inspection.
"""

import os
import pytest
from fastapi.testclient import TestClient
from main import app
from services import settings_service, model_service

client = TestClient(app)


def test_app_settings_crud():
    """Verify SQLite app_settings can set, get, and overwrite values."""
    settings_service.set_setting("test_custom_param", "studio_v2")
    assert settings_service.get_setting("test_custom_param") == "studio_v2"

    settings_service.set_setting("test_custom_param", "studio_v3")
    assert settings_service.get_setting("test_custom_param") == "studio_v3"

    assert settings_service.get_setting("non_existent_key", "default_val") == "default_val"


def test_api_key_masking():
    """Verify key masking never reveals full API key secrets."""
    raw = "AIzaSyB7TestingKey1234567890Secret"
    masked = settings_service.mask_key(raw)
    assert masked.startswith("AIzaSy")
    assert masked.endswith("cret")
    assert "TestingKey" not in masked
    assert "••••••••" in masked

    short_key = "abc"
    assert settings_service.mask_key(short_key) == "••••••••"


def test_api_keys_save_and_status():
    """Verify saving API keys updates database and status dict."""
    test_key = "AIzaSyTest_Saved_Key_12345678"
    status = settings_service.save_api_keys(gemini_key=test_key)
    assert status["gemini_configured"] is True
    assert "AIzaSy" in status["gemini_masked"]

    # Clear key
    cleared = settings_service.save_api_keys(gemini_key="")
    assert cleared["gemini_configured"] is False
    assert cleared["gemini_masked"] == ""


def test_tokenharbor_key_save_and_status():
    """Verify saving Token Harbor key updates database and status dict."""
    th_key = "thk_live_test_key_87654321"
    status = settings_service.save_api_keys(tokenharbor_key=th_key)
    assert status["tokenharbor_configured"] is True
    assert "thk_li" in status["tokenharbor_masked"]

    # Clear Token Harbor key
    cleared = settings_service.save_api_keys(tokenharbor_key="")
    assert cleared["tokenharbor_configured"] is False
    assert cleared["tokenharbor_masked"] == ""


def test_verify_tokenharbor_key_empty():
    """Verify empty Token Harbor key returns clean error response."""
    res = settings_service.verify_tokenharbor_key("")
    assert res["valid"] is False
    assert "No Token Harbor API key" in res["error"]


def test_verify_gemini_key_empty():
    """Verify empty key returns clean validation error without throwing exceptions."""
    res = settings_service.verify_gemini_key("")
    assert res["valid"] is False
    assert "No Gemini API key" in res["error"]


def test_verify_gemini_key_invalid():
    """Verify invalid key returns handled error response with HTTP status."""
    res = settings_service.verify_gemini_key("AIzaSyInvalidFakeKey_000000")
    assert res["valid"] is False
    assert "error" in res


def test_model_registry_list():
    """Verify model registry returns all 4 standard tiers with proper metadata."""
    models = model_service.get_model_status_list()
    assert len(models) == 4
    tier_ids = [m["id"] for m in models]
    assert "cheetah" in tier_ids
    assert "dolphin" in tier_ids
    assert "whale_turbo" in tier_ids
    assert "whale" in tier_ids

    # Cheetah is base model
    cheetah = next(m for m in models if m["id"] == "cheetah")
    assert cheetah["approx_size_mb"] == 145
    assert "repo_id" in cheetah


def test_model_storage_info_api():
    """Verify /api/settings/storage returns valid disk information."""
    resp = client.get("/api/settings/storage")
    assert resp.status_code == 200
    data = resp.json()
    assert "models_directory" in data
    assert "free_disk_gb" in data
    assert data["free_disk_gb"] > 0


def test_settings_api_endpoints():
    """Verify REST endpoints for /api/settings/keys and /api/settings/models."""
    # GET keys
    res = client.get("/api/settings/keys")
    assert res.status_code == 200
    assert "gemini_configured" in res.json()

    # GET models
    res_models = client.get("/api/settings/models")
    assert res_models.status_code == 200
    assert len(res_models.json()) == 4

    # POST verify with empty
    res_verify = client.post("/api/settings/keys/verify", json={"provider": "gemini", "key": ""})
    assert res_verify.status_code == 200
    assert res_verify.json()["valid"] is False

    # GET download status format
    res_status = client.get("/api/settings/models/cheetah/download/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "status" in status_data
    assert "progress" in status_data
    assert "tier" in status_data

    # DELETE endpoint format
    res_del = client.delete("/api/settings/models/nonexistent_dummy")
    assert res_del.status_code == 404


def test_multi_key_pool_endpoints():
    """Verify adding, removing, and pooling multiple API keys for the same provider."""
    # 1. Add key 1
    k1 = "AIzaSyPoolTestKeyOne111111111"
    res1 = client.post("/api/settings/keys/add", json={"provider": "gemini", "key": k1})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["gemini_configured"] is True
    assert data1["gemini_count"] >= 1
    assert any("AIzaSy" in item["masked"] for item in data1["gemini_keys"])

    # 2. Add key 2 to the same provider
    k2 = "AIzaSyPoolTestKeyTwo222222222"
    res2 = client.post("/api/settings/keys/add", json={"provider": "gemini", "key": k2})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["gemini_count"] >= 2

    # 3. Verify key candidate rotation in ai_client
    from engine.ai_client import get_healthy_candidate_keys
    candidates = get_healthy_candidate_keys("gemini")
    assert k1 in candidates
    assert k2 in candidates

    # 4. Remove key 2 by index
    # Find index of k2
    k2_idx = next(i for i, item in enumerate(data2["gemini_keys"]) if "Two222" in item.get("masked", "") or item["id"] == len(data2["gemini_keys"]) - 1)
    res_rem = client.post("/api/settings/keys/remove", json={"provider": "gemini", "key_index": k2_idx})
    assert res_rem.status_code == 200
    data3 = res_rem.json()
    assert data3["gemini_count"] == data2["gemini_count"] - 1

    # Clean up test keys
    client.post("/api/settings/keys/remove", json={"provider": "gemini", "key": k1})

