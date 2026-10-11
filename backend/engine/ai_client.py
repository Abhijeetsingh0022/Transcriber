"""
Unified AI Client & Gateway for Video Transcription and Semantic Reasoning.
Provides centralized API key resolution, provider failover (Gemini -> OpenRouter),
intelligent circuit breakers/cooldowns, cost/token optimization, and multi-tier response caching.
Zero new third-party dependencies (built with standard library).
"""

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# In-memory thread lock for thread-safe gateway state mutations
_AI_GATEWAY_LOCK = threading.Lock()

# In-memory circuit breakers & cooldowns (timestamp until which provider is temporarily bypassed)
_COOLDOWNS: Dict[str, float] = {
    "gemini": 0.0,
    "openrouter": 0.0,
    "tokenharbor": 0.0,
}
_DISABLED_PROVIDERS: set = set()
_CACHED_OPENROUTER_INFERENCE_KEY: Optional[str] = None
_RESOLVED_OPENROUTER_KEYS: Dict[str, str] = {}

# Per-key cooldown tracking and quarantine
_KEY_COOLDOWNS: Dict[str, float] = {}
_DISABLED_KEYS: set = set()
_KEY_ROBIN_INDEX: Dict[str, int] = {
    "gemini": 0,
    "openrouter": 0,
    "tokenharbor": 0,
}

# High-performance LRU in-memory cache keyed by content hash or job ID
_AI_CACHE: OrderedDict = OrderedDict()
_MAX_CACHE_ENTRIES = 250


def _cache_put(key: str, val: Dict[str, Any]) -> None:
    """Inserts or updates LRU cache item, evicting oldest entry if full."""
    with _AI_GATEWAY_LOCK:
        if key in _AI_CACHE:
            _AI_CACHE.move_to_end(key)
        else:
            if len(_AI_CACHE) >= _MAX_CACHE_ENTRIES:
                _AI_CACHE.popitem(last=False)
        _AI_CACHE[key] = val


def _key_hash(key: str) -> str:
    """Computes a deterministic short hash for an API key to track state safely without storing secrets."""
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()[:16]


def _cool_down_key(key: str, seconds: float) -> None:
    """Sets a temporary cooldown on a specific key (e.g. on HTTP 429 rate limit)."""
    if key and key.strip():
        with _AI_GATEWAY_LOCK:
            _KEY_COOLDOWNS[_key_hash(key)] = time.time() + max(5.0, seconds)


def _disable_key(key: str) -> None:
    """Quarantines a revoked or unauthorized key (HTTP 401/403)."""
    if key and key.strip():
        with _AI_GATEWAY_LOCK:
            _DISABLED_KEYS.add(_key_hash(key))


def get_healthy_candidate_keys(provider: str) -> List[str]:
    """
    Returns all healthy (non-disabled, non-cooling) API keys for a provider,
    rotated in round-robin order to balance load across keys.
    """
    now = time.time()
    pool: List[str] = []
    try:
        from services.settings_service import get_provider_keys_pool
        pool = get_provider_keys_pool(provider)
    except Exception:
        pass

    if not pool:
        single_getters = {
            "gemini": get_gemini_api_key,
            "openrouter": get_openrouter_api_key,
            "tokenharbor": get_tokenharbor_api_key,
        }
        getter = single_getters.get(provider)
        if getter:
            k = getter()
            if k:
                pool = [k]

    with _AI_GATEWAY_LOCK:
        healthy: List[str] = [
            k for k in pool
            if k and k.strip()
            and _key_hash(k) not in _DISABLED_KEYS
            and now >= _KEY_COOLDOWNS.get(_key_hash(k), 0.0)
        ]

        if not healthy:
            return []

        # Round-robin rotation across healthy keys
        current_idx = _KEY_ROBIN_INDEX.get(provider, 0) % len(healthy)
        _KEY_ROBIN_INDEX[provider] = (_KEY_ROBIN_INDEX.get(provider, 0) + 1) % len(healthy)
        return healthy[current_idx:] + healthy[:current_idx]



def get_gemini_api_key() -> Optional[str]:
    """Retrieves primary Gemini API key from database settings, with .env fallback."""
    try:
        from services.settings_service import get_raw_gemini_key
        key = get_raw_gemini_key()
        if key:
            return key
    except Exception:
        pass

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GEMINI_KEY")
    )


def get_openrouter_api_key() -> Optional[str]:
    """Retrieves primary OpenRouter API key from database settings, with .env fallback."""
    try:
        from services.settings_service import get_raw_openrouter_key
        key = get_raw_openrouter_key()
        if key:
            return key
    except Exception:
        pass

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPEN_ROUTER_API_KEY")
        or os.environ.get("OPENROUTER_KEY")
    )


def get_tokenharbor_api_key() -> Optional[str]:
    """Retrieves primary Token Harbor API key from database settings, with .env fallback."""
    try:
        from services.settings_service import get_raw_tokenharbor_key
        key = get_raw_tokenharbor_key()
        if key:
            return key
    except Exception:
        pass

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return (
        os.environ.get("TOKENHARBOR_API_KEY")
        or os.environ.get("TOKEN_HARBOR_API_KEY")
        or os.environ.get("TOKENHARBOR_KEY")
    )


def resolve_openrouter_inference_key(raw_key: Optional[str] = None) -> Optional[str]:
    """
    Resolves OpenRouter API key. If the key is a management/provisioning key,
    automatically provisions and caches an active inference key.
    """
    global _CACHED_OPENROUTER_INFERENCE_KEY
    key_to_check = raw_key or get_openrouter_api_key()
    if not key_to_check:
        return None

    if key_to_check in _RESOLVED_OPENROUTER_KEYS:
        return _RESOLVED_OPENROUTER_KEYS[key_to_check]

    try:
        chk_req = urllib.request.Request(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {key_to_check}"}
        )
        with urllib.request.urlopen(chk_req, timeout=8.0) as resp:
            info = json.loads(resp.read().decode("utf-8")).get("data", {})

        if info.get("is_provisioning_key"):
            create_req = urllib.request.Request(
                "https://openrouter.ai/api/v1/keys",
                data=json.dumps({"name": "Transcriber AI Gateway"}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {key_to_check}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(create_req, timeout=8.0) as c_resp:
                c_data = json.loads(c_resp.read().decode("utf-8"))
                created_key = c_data.get("key")
                if created_key:
                    _RESOLVED_OPENROUTER_KEYS[key_to_check] = created_key
                    _CACHED_OPENROUTER_INFERENCE_KEY = created_key
                    return created_key
        else:
            _RESOLVED_OPENROUTER_KEYS[key_to_check] = key_to_check
            _CACHED_OPENROUTER_INFERENCE_KEY = key_to_check
            return key_to_check
    except Exception:
        pass

    _RESOLVED_OPENROUTER_KEYS[key_to_check] = key_to_check
    _CACHED_OPENROUTER_INFERENCE_KEY = key_to_check
    return key_to_check


def get_ai_status() -> Dict[str, Any]:
    """Returns current status and health of configured AI providers and key pools."""
    now = time.time()
    try:
        from services.settings_service import get_provider_keys_pool
    except Exception:
        def get_provider_keys_pool(p: str) -> List[str]:
            return []

    gemini_pool = get_provider_keys_pool("gemini") or ([get_gemini_api_key()] if get_gemini_api_key() else [])
    openrouter_pool = get_provider_keys_pool("openrouter") or ([get_openrouter_api_key()] if get_openrouter_api_key() else [])
    tokenharbor_pool = get_provider_keys_pool("tokenharbor") or ([get_tokenharbor_api_key()] if get_tokenharbor_api_key() else [])

    def provider_stats(provider: str, pool: List[str]) -> Dict[str, Any]:
        healthy_keys = [
            k for k in pool
            if _key_hash(k) not in _DISABLED_KEYS
            and now >= _KEY_COOLDOWNS.get(_key_hash(k), 0.0)
        ]
        provider_cd = _COOLDOWNS.get(provider, 0.0)
        is_prov_cooling = now < provider_cd
        keys_cooling = len(pool) > 0 and len(healthy_keys) == 0 and not all(_key_hash(k) in _DISABLED_KEYS for k in pool)
        cooling_down = is_prov_cooling or keys_cooling

        min_cd = 0.0
        if is_prov_cooling:
            min_cd = provider_cd - now
        elif keys_cooling:
            cds = [_KEY_COOLDOWNS.get(_key_hash(k), 0.0) - now for k in pool if _key_hash(k) not in _DISABLED_KEYS]
            min_cd = min(cds) if cds else 0.0

        return {
            "configured": len(pool) > 0,
            "total_keys": len(pool),
            "healthy_keys": len(healthy_keys),
            "disabled": provider in _DISABLED_PROVIDERS or (len(pool) > 0 and all(_key_hash(k) in _DISABLED_KEYS for k in pool)),
            "cooling_down": cooling_down,
            "cooldown_remaining_sec": max(0, int(min_cd)),
        }

    return {
        "gemini": provider_stats("gemini", gemini_pool),
        "openrouter": provider_stats("openrouter", openrouter_pool),
        "tokenharbor": provider_stats("tokenharbor", tokenharbor_pool),
        "cache_entries": len(_AI_CACHE),
    }


def clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extracts and parses JSON from LLM responses,
    stripping Markdown code fences and conversational preambles.
    """
    if not raw_text or not raw_text.strip():
        return None

    txt = raw_text.strip()

    # 1. Direct parse attempt
    try:
        val = json.loads(txt)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    # 2. Strip Markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", txt, re.IGNORECASE)
    if fence_match:
        try:
            val = json.loads(fence_match.group(1).strip())
            if isinstance(val, dict):
                return val
        except Exception:
            pass

    # 3. Search for outermost balanced { ... } object
    start_brace = txt.find("{")
    end_brace = txt.rfind("}")
    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
        candidate = txt[start_brace : end_brace + 1]
        try:
            val = json.loads(candidate)
            if isinstance(val, dict):
                return val
        except Exception:
            try:
                cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
                val = json.loads(cleaned)
                if isinstance(val, dict):
                    return val
            except Exception:
                pass

    # 4. Truncation auto-repair: if model hit token limits mid-output, close open arrays/objects
    if start_brace != -1:
        core = txt[start_brace:]
        last_obj = core.rfind("}")
        if last_obj != -1:
            prefix = core[:last_obj + 1]
            for suffix in ["]}", "}", "}]"]:
                try:
                    cand = prefix + suffix
                    val = json.loads(cand)
                    if isinstance(val, dict) and ("characters" in val or "turns" in val):
                        return val
                except Exception:
                    pass

    return None


def _compute_cache_key(prompt: str, task_tag: str, custom_key: Optional[str] = None) -> str:
    """Generates unique deterministic cache key."""
    if custom_key:
        return f"{task_tag}:{custom_key}"
    h = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:24]
    return f"{task_tag}:{h}"


def _execute_gemini_call(
    prompt: str,
    api_key: str,
    timeout: float = 30.0,
    schema: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Executes call against Google Gemini models with automatic 429 quota failover across model tiers."""
    pref_model = None
    try:
        from services.settings_service import get_setting
        pref_model = get_setting("gemini_model")
    except Exception:
        pass

    primary_model = pref_model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    models_to_try = [primary_model]
    if primary_model != "gemini-3-flash-preview":
        models_to_try.append("gemini-3-flash-preview")

    base_config: Dict[str, Any] = {
        "responseMimeType": "application/json",
        "temperature": 0.1,
        "maxOutputTokens": 8192,
        "thinkingConfig": {"thinkingBudget": 0},
    }

    req_config = dict(base_config)
    if schema:
        req_config["responseSchema"] = schema

    all_exhausted = True
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

        def _do_request(gen_cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_cfg,
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates") or []
                if not candidates:
                    return None
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    return None
                raw_text = parts[0].get("text", "")
                return clean_and_parse_json(raw_text)

        try:
            res = _do_request(req_config)
            if res:
                return res
            all_exhausted = False
        except urllib.error.HTTPError as he:
            if schema and he.code in (400, 503):
                try:
                    res = _do_request(base_config)
                    if res:
                        return res
                except Exception:
                    pass

            if he.code == 429:
                # Quota reached for this model; try secondary model on same key!
                continue
            elif he.code in (401, 403):
                _disable_key(api_key)
                return None
            all_exhausted = False
        except urllib.error.URLError:
            # Transient network disconnect; retry once after short backoff
            time.sleep(0.4)
            try:
                res = _do_request(req_config)
                if res:
                    return res
            except Exception:
                pass
            all_exhausted = False
        except Exception:
            if schema:
                try:
                    res = _do_request(base_config)
                    if res:
                        return res
                except Exception:
                    pass
            all_exhausted = False

    if all_exhausted:
        _cool_down_key(api_key, 60.0)

    return None


def _execute_openai_compat_call(
    url: str,
    api_key: str,
    models: List[str],
    prompt: str,
    provider_name: str,
    timeout: float = 12.0,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Unified high-performance executor for OpenAI-compatible completions endpoints (OpenRouter & Token Harbor).
    Handles sequential model fallback, dynamic Retry-After parsing on HTTP 429, circuit breaker cooldowns,
    and automatic auth revocation quarantine.
    """
    for model_name in models:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 4096,
            "temperature": 0.1,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                choices = res.get("choices") or []
                if not choices:
                    continue
                content = choices[0].get("message", {}).get("content", "")
                parsed = clean_and_parse_json(content)
                if parsed:
                    return parsed
        except urllib.error.HTTPError as he:
            if he.code == 429:
                retry_hdr = he.headers.get("Retry-After") if hasattr(he, "headers") else None
                try:
                    wait_sec = float(retry_hdr) if retry_hdr else 45.0
                except (ValueError, TypeError):
                    wait_sec = 45.0
                cd_time = max(5.0, min(wait_sec, 300.0))
                _cool_down_key(api_key, cd_time)
                if provider_name:
                    with _AI_GATEWAY_LOCK:
                        _COOLDOWNS[provider_name] = time.time() + cd_time
                break
            elif he.code in (401, 403):
                _disable_key(api_key)
                if provider_name:
                    with _AI_GATEWAY_LOCK:
                        _DISABLED_PROVIDERS.add(provider_name)
                break
            continue
        except urllib.error.URLError:
            # Transient network glitch; retry once
            time.sleep(0.4)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    choices = res.get("choices") or []
                    if choices:
                        parsed = clean_and_parse_json(choices[0].get("message", {}).get("content", ""))
                        if parsed:
                            return parsed
            except Exception:
                pass
            continue
        except Exception:
            continue

    return None


def _execute_openrouter_call(
    prompt: str,
    inf_key: str,
    timeout: float = 12.0,
) -> Optional[Dict[str, Any]]:
    """Executes call against OpenRouter high-speed free models."""
    models_to_try = [
        "liquid/lfm-2.5-2.6b:free",
        "nvidia/nemotron-3.5-lightning:free",
    ]
    pref_or = None
    try:
        from services.settings_service import get_setting
        pref_or = get_setting("openrouter_model")
    except Exception:
        pass
    custom_model = pref_or or os.environ.get("OPENROUTER_MODEL")
    if custom_model:
        models_to_try.insert(0, custom_model)

    return _execute_openai_compat_call(
        url="https://openrouter.ai/api/v1/chat/completions",
        api_key=inf_key,
        models=models_to_try,
        prompt=prompt,
        provider_name="openrouter",
        timeout=timeout,
        extra_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "TMUX AI Gateway",
        },
    )


def _execute_tokenharbor_call(
    prompt: str,
    api_key: str,
    timeout: float = 25.0,
) -> Optional[Dict[str, Any]]:
    """Executes call against Token Harbor free tier models."""
    models_to_try = [
        "claude-haiku-5.5:free",
        "deepseek-v4.1-flash:free",
        "mimo-v2.6-flash:free",
    ]
    pref_th = None
    try:
        from services.settings_service import get_setting
        pref_th = get_setting("tokenharbor_model")
    except Exception:
        pass
    custom_model = pref_th or os.environ.get("TOKENHARBOR_MODEL")
    if custom_model:
        models_to_try.insert(0, custom_model)

    return _execute_openai_compat_call(
        url="https://tokenharbor.ai/v1/chat/completions",
        api_key=api_key,
        models=models_to_try,
        prompt=prompt,
        provider_name="tokenharbor",
        timeout=timeout,
        extra_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "TMUX AI Gateway",
        },
    )


def call_ai_json(
    prompt: str,
    task_tag: str = "generic",
    cache_key: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
    override_gemini_key: Optional[str] = None,
    override_openrouter_key: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Executes a structured JSON AI request with resilient multi-key and multi-tier fallback:
    1. Instant in-memory cache lookup (0ms, $0 cost).
    2. Primary Google Gemini 3.8 Flash (pool of keys, round-robin, seamless 429 intra-pool failover).
    3. Secondary OpenRouter Free Models (pool of keys, round-robin, sequential model fallback).
    4. Tertiary Token Harbor Free Models (pool of keys, round-robin, auto-failover).
    5. Circuit breaker protection with dynamic Retry-After parsing against rate-limits.

    Returns (result_dict, provider_used) where provider_used is:
    'cache', 'gemini', 'openrouter', 'tokenharbor', or 'none'.
    """
    global _AI_CACHE
    c_key = _compute_cache_key(prompt, task_tag, cache_key)
    with _AI_GATEWAY_LOCK:
        if c_key in _AI_CACHE:
            _AI_CACHE.move_to_end(c_key)
            return _AI_CACHE[c_key], "cache"

    now = time.time()

    # 1. Try Gemini pool
    if ("gemini" not in _DISABLED_PROVIDERS) and (now >= _COOLDOWNS.get("gemini", 0.0)):
        gemini_candidates = get_healthy_candidate_keys("gemini")
        if override_gemini_key and override_gemini_key.strip():
            k = override_gemini_key.strip()
            if k in gemini_candidates:
                gemini_candidates.remove(k)
            gemini_candidates.insert(0, k)
        for g_key in gemini_candidates:
            res = _execute_gemini_call(prompt, g_key, timeout=timeout, schema=schema)
            if res:
                with _AI_GATEWAY_LOCK:
                    _COOLDOWNS["gemini"] = 0.0
                    _DISABLED_PROVIDERS.discard("gemini")
                _cache_put(c_key, res)
                return res, "gemini"
        if gemini_candidates:
            with _AI_GATEWAY_LOCK:
                _COOLDOWNS["gemini"] = time.time() + 30.0

    # 2. Try OpenRouter pool
    if ("openrouter" not in _DISABLED_PROVIDERS) and (now >= _COOLDOWNS.get("openrouter", 0.0)):
        openrouter_candidates = get_healthy_candidate_keys("openrouter")
        if override_openrouter_key and override_openrouter_key.strip():
            k = override_openrouter_key.strip()
            if k in openrouter_candidates:
                openrouter_candidates.remove(k)
            openrouter_candidates.insert(0, k)
        for or_raw in openrouter_candidates:
            inf_key = resolve_openrouter_inference_key(or_raw)
            if not inf_key:
                continue
            res = _execute_openrouter_call(prompt, inf_key, timeout=timeout)
            if res:
                with _AI_GATEWAY_LOCK:
                    _COOLDOWNS["openrouter"] = 0.0
                    _DISABLED_PROVIDERS.discard("openrouter")
                _cache_put(c_key, res)
                return res, "openrouter"
        if openrouter_candidates:
            with _AI_GATEWAY_LOCK:
                _COOLDOWNS["openrouter"] = time.time() + 30.0

    # 3. Try Token Harbor pool
    if ("tokenharbor" not in _DISABLED_PROVIDERS) and (now >= _COOLDOWNS.get("tokenharbor", 0.0)):
        tokenharbor_candidates = get_healthy_candidate_keys("tokenharbor")
        for th_key in tokenharbor_candidates:
            res = _execute_tokenharbor_call(prompt, th_key, timeout=min(timeout, 25.0))
            if res:
                with _AI_GATEWAY_LOCK:
                    _COOLDOWNS["tokenharbor"] = 0.0
                    _DISABLED_PROVIDERS.discard("tokenharbor")
                _cache_put(c_key, res)
                return res, "tokenharbor"
        if tokenharbor_candidates:
            with _AI_GATEWAY_LOCK:
                _COOLDOWNS["tokenharbor"] = time.time() + 30.0

    return None, "none"
