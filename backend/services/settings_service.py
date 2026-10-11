"""
Settings Service — manages persistence of desktop application settings and API keys.
Stores configuration in SQLite app_settings with fallback to OS environment variables.
Provides stdlib-based verification for Google Gemini and OpenRouter API keys.
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from db.database import get_db

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def mask_key(key: str) -> str:
    """Masks an API key for safe display in the frontend UI."""
    if not key or len(key) < 8:
        return "••••••••"
    return f"{key[:6]}••••••••{key[-4:]}"


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves a single setting from the database, or default if not set."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
    except Exception:
        pass
    return default


def set_setting(key: str, value: str) -> None:
    """Inserts or updates a setting in the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value)),
        )


def get_provider_keys_pool(provider: str) -> list[str]:
    """Retrieves full list of configured API keys for a provider with fallback to legacy single key."""
    provider = provider.lower().strip()
    raw_json = get_setting(f"{provider}_api_keys")
    if raw_json:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                keys = [str(k).strip() for k in parsed if str(k).strip()]
                if keys:
                    return keys
        except Exception:
            pass

    # Fallback to legacy single key setting
    single = get_setting(f"{provider}_api_key")
    if single and single.strip():
        return [single.strip()]

    # Fallback to os.environ
    env_prefixes = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY"],
        "openrouter": ["OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY", "OPENROUTER_KEY"],
        "tokenharbor": ["TOKENHARBOR_API_KEY", "TOKEN_HARBOR_API_KEY", "TOKENHARBOR_KEY"],
    }
    for env_var in env_prefixes.get(provider, []):
        val = os.environ.get(env_var)
        if val and val.strip():
            return [val.strip()]

    return []


def set_provider_keys_pool(provider: str, keys: list[str]) -> list[str]:
    """Persists a list of keys for a provider, deduplicating while preserving order."""
    provider = provider.lower().strip()
    clean_keys: list[str] = []
    for k in keys:
        clean = str(k).strip()
        if clean and clean not in clean_keys:
            clean_keys.append(clean)

    set_setting(f"{provider}_api_keys", json.dumps(clean_keys))
    # Keep legacy single key synced with the primary key
    first_key = clean_keys[0] if clean_keys else ""
    set_setting(f"{provider}_api_key", first_key)

    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "tokenharbor": "TOKENHARBOR_API_KEY",
    }
    env_name = env_map.get(provider)
    if env_name:
        if first_key:
            os.environ[env_name] = first_key
        elif env_name in os.environ:
            del os.environ[env_name]

    return clean_keys


def add_provider_key(provider: str, key: str) -> list[str]:
    """Appends a new key to a provider's key pool."""
    pool = get_provider_keys_pool(provider)
    clean = key.strip()
    if clean and clean not in pool:
        pool.append(clean)
        set_provider_keys_pool(provider, pool)
    return pool


def remove_provider_key(provider: str, key_or_index: Any) -> list[str]:
    """Removes a key from a provider's pool by index or raw key."""
    pool = get_provider_keys_pool(provider)
    if isinstance(key_or_index, int) or (isinstance(key_or_index, str) and key_or_index.isdigit()):
        idx = int(key_or_index)
        if 0 <= idx < len(pool):
            pool.pop(idx)
    elif key_or_index in pool:
        pool.remove(key_or_index)
    elif isinstance(key_or_index, str):
        target = key_or_index.strip()
        pool = [k for k in pool if k != target]

    set_provider_keys_pool(provider, pool)
    return pool


def get_raw_gemini_key() -> Optional[str]:
    """Resolves active primary Gemini API key."""
    keys = get_provider_keys_pool("gemini")
    return keys[0] if keys else None


def get_raw_openrouter_key() -> Optional[str]:
    """Resolves active primary OpenRouter API key."""
    keys = get_provider_keys_pool("openrouter")
    return keys[0] if keys else None


def get_raw_tokenharbor_key() -> Optional[str]:
    """Resolves active primary Token Harbor API key."""
    keys = get_provider_keys_pool("tokenharbor")
    return keys[0] if keys else None


def get_keys_status() -> Dict[str, Any]:
    """Returns safe masked key statuses & multi-key pools across all 3 providers."""
    gemini_keys = get_provider_keys_pool("gemini")
    openrouter_keys = get_provider_keys_pool("openrouter")
    tokenharbor_keys = get_provider_keys_pool("tokenharbor")

    return {
        "gemini_configured": bool(gemini_keys),
        "gemini_masked": mask_key(gemini_keys[0]) if gemini_keys else "",
        "gemini_count": len(gemini_keys),
        "gemini_keys": [
            {"id": idx, "masked": mask_key(k), "preview": f"{k[:4]}...{k[-4:]}" if len(k) >= 8 else "••••"}
            for idx, k in enumerate(gemini_keys)
        ],
        "openrouter_configured": bool(openrouter_keys),
        "openrouter_masked": mask_key(openrouter_keys[0]) if openrouter_keys else "",
        "openrouter_count": len(openrouter_keys),
        "openrouter_keys": [
            {"id": idx, "masked": mask_key(k), "preview": f"{k[:4]}...{k[-4:]}" if len(k) >= 8 else "••••"}
            for idx, k in enumerate(openrouter_keys)
        ],
        "tokenharbor_configured": bool(tokenharbor_keys),
        "tokenharbor_masked": mask_key(tokenharbor_keys[0]) if tokenharbor_keys else "",
        "tokenharbor_count": len(tokenharbor_keys),
        "tokenharbor_keys": [
            {"id": idx, "masked": mask_key(k), "preview": f"{k[:4]}...{k[-4:]}" if len(k) >= 8 else "••••"}
            for idx, k in enumerate(tokenharbor_keys)
        ],
    }


def save_api_keys(
    gemini_key: Optional[str] = None,
    openrouter_key: Optional[str] = None,
    tokenharbor_key: Optional[str] = None,
    gemini_keys: Optional[list[str]] = None,
    openrouter_keys: Optional[list[str]] = None,
    tokenharbor_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Saves API keys to persistent SQLite settings.
    Supports single keys and multi-key lists. Empty string removes keys.
    """
    if gemini_keys is not None:
        set_provider_keys_pool("gemini", gemini_keys)
    elif gemini_key is not None:
        if gemini_key.strip():
            set_provider_keys_pool("gemini", [gemini_key.strip()])
        else:
            set_provider_keys_pool("gemini", [])

    if openrouter_keys is not None:
        set_provider_keys_pool("openrouter", openrouter_keys)
    elif openrouter_key is not None:
        if openrouter_key.strip():
            set_provider_keys_pool("openrouter", [openrouter_key.strip()])
        else:
            set_provider_keys_pool("openrouter", [])

    if tokenharbor_keys is not None:
        set_provider_keys_pool("tokenharbor", tokenharbor_keys)
    elif tokenharbor_key is not None:
        if tokenharbor_key.strip():
            set_provider_keys_pool("tokenharbor", [tokenharbor_key.strip()])
        else:
            set_provider_keys_pool("tokenharbor", [])

    return get_keys_status()


def verify_gemini_key(key: Optional[str] = None, key_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Sends a lightweight 1-token test prompt to Google Gemini API.
    Zero external dependencies (pure standard library urllib).
    """
    if key is not None:
        target_key = key.strip() if key.strip() else None
    elif key_index is not None:
        pool = get_provider_keys_pool("gemini")
        target_key = pool[key_index] if 0 <= key_index < len(pool) else None
    else:
        target_key = get_raw_gemini_key()

    if not target_key:
        return {
            "valid": False,
            "error": "No Gemini API key provided. Enter a key first.",
        }

    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={target_key}"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if resp.status == 200:
                return {
                    "valid": True,
                    "latency_ms": latency_ms,
                    "model": model_name,
                    "provider": "Google Gemini",
                }
            return {
                "valid": False,
                "error": f"Unexpected response status: {resp.status}",
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            msg = err_data.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        is_quota = e.code == 429
        return {
            "valid": is_quota,
            "rate_limited": is_quota,
            "error": "Rate limit / free tier quota exceeded" if is_quota else msg,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "provider": "Google Gemini",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Connection failed: {str(e)}",
        }


def verify_openrouter_key(key: Optional[str] = None, key_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Sends a lightweight auth verification check to OpenRouter.
    Zero external dependencies (pure standard library urllib).
    """
    if key is not None:
        target_key = key.strip() if key.strip() else None
    elif key_index is not None:
        pool = get_provider_keys_pool("openrouter")
        target_key = pool[key_index] if 0 <= key_index < len(pool) else None
    else:
        target_key = get_raw_openrouter_key()

    if not target_key:
        return {
            "valid": False,
            "error": "No OpenRouter API key provided. Enter a key first.",
        }

    url = "https://openrouter.ai/api/v1/auth/key"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {target_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                label = data.get("data", {}).get("label", "OpenRouter User")
                return {
                    "valid": True,
                    "latency_ms": latency_ms,
                    "label": label,
                    "provider": "OpenRouter",
                }
            return {
                "valid": False,
                "error": f"Unexpected response status: {resp.status}",
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            msg = err_data.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        is_quota = e.code == 429
        return {
            "valid": is_quota,
            "rate_limited": is_quota,
            "error": "Rate limit / quota exceeded" if is_quota else msg,
            "status_code": e.code,
            "latency_ms": latency_ms,
            "provider": "OpenRouter",
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Connection failed: {str(e)}",
        }


def verify_tokenharbor_key(key: Optional[str] = None, key_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Sends a lightweight auth verification check to Token Harbor.
    Zero external dependencies (pure standard library urllib).
    """
    if key is not None:
        target_key = key.strip() if key.strip() else None
    elif key_index is not None:
        pool = get_provider_keys_pool("tokenharbor")
        target_key = pool[key_index] if 0 <= key_index < len(pool) else None
    else:
        target_key = get_raw_tokenharbor_key()

    if not target_key:
        return {
            "valid": False,
            "error": "No Token Harbor API key provided. Enter a key first.",
        }

    url = "https://tokenharbor.ai/v1/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {target_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "TMUX AI Gateway",
        },
        method="GET",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if resp.status == 200:
                return {
                    "valid": True,
                    "latency_ms": latency_ms,
                    "provider": "Token Harbor",
                }
            return {
                "valid": False,
                "error": f"Unexpected response status: {resp.status}",
            }
    except urllib.error.HTTPError as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            msg = err_data.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return {
            "valid": False,
            "error": msg,
            "status_code": e.code,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Connection failed: {str(e)}",
        }
