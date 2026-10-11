"""
Model Service — manages Whisper speech recognition models for TMUX Studio.
Provides model registry metadata, disk usage inspection, on-demand background downloading,
and storage reclamation. Zero new external dependencies.
"""

import os
import sys
import shutil
import platform
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from services.settings_service import get_setting

# Known Model Tiers & Metadata
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "cheetah": {
        "id": "cheetah",
        "name": "Cheetah",
        "label": "Cheetah (Base)",
        "repo_id": "Systran/faster-whisper-base",
        "approx_size_mb": 145,
        "approx_size_bytes": 145 * 1024 * 1024,
        "ram_required": "~0.5 GB",
        "speed_rating": "5x Realtime",
        "accuracy_rating": "Good",
        "description": "Ultra-fast acoustic inference. Best for fast voice dictation & lower-spec systems.",
        "is_default_bundled": True,
    },
    "dolphin": {
        "id": "dolphin",
        "name": "Dolphin",
        "label": "Dolphin (Small)",
        "repo_id": "Systran/faster-whisper-small",
        "approx_size_mb": 480,
        "approx_size_bytes": 480 * 1024 * 1024,
        "ram_required": "~1.0 GB",
        "speed_rating": "3x Realtime",
        "accuracy_rating": "Very Good",
        "description": "Balanced speed and accuracy. Great for clear podcasts, interviews, and meetings.",
        "is_default_bundled": False,
    },
    "whale_turbo": {
        "id": "whale_turbo",
        "name": "Whale Turbo",
        "label": "Whale Turbo (Large-v3 Turbo)",
        "repo_id": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "approx_size_mb": 1600,
        "approx_size_bytes": 1600 * 1024 * 1024,
        "ram_required": "~2.5 GB",
        "speed_rating": "2.5x Realtime",
        "accuracy_rating": "Exceptional",
        "description": "State-of-the-art Large-v3 accuracy at 2x faster speed with optimized weight memory.",
        "is_default_bundled": False,
    },
    "whale": {
        "id": "whale",
        "name": "Whale",
        "label": "Whale (Large-v3)",
        "repo_id": "Systran/faster-whisper-large-v3",
        "approx_size_mb": 3100,
        "approx_size_bytes": 3100 * 1024 * 1024,
        "ram_required": "~4.5 GB",
        "speed_rating": "1.2x Realtime",
        "accuracy_rating": "Broadcast Reference",
        "description": "Gold-standard reference model. Maximum precision for accents, technical jargon, and noisy audio.",
        "is_default_bundled": False,
    },
}

# In-memory download tracking state
_DOWNLOAD_LOCK = threading.Lock()
_DOWNLOAD_STATE: Dict[str, Dict[str, Any]] = {}


def get_default_models_dir() -> Path:
    """
    Returns the persistent application models directory based on the host OS.
    Preserves backwards compatibility with ~/.cache/transcriber/models.
    """
    custom = get_setting("models_directory")
    if custom and custom.strip():
        p = Path(custom.strip())
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Existing cache check
    legacy_cache = Path.home() / ".cache" / "transcriber" / "models"
    if legacy_cache.exists():
        return legacy_cache

    system = platform.system()
    if system == "Darwin":
        app_support = Path.home() / "Library" / "Application Support" / "TMUX Studio" / "models"
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else (Path.home() / "AppData" / "Local")
        app_support = base / "TMUX Studio" / "models"
    else:
        app_support = Path.home() / ".local" / "share" / "tmux-studio" / "models"

    app_support.mkdir(parents=True, exist_ok=True)
    return app_support


def get_dir_size_bytes(directory: Path) -> int:
    """Calculates recursive directory size in bytes without throwing on locks."""
    total = 0
    if not directory.exists():
        return 0
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and not entry.is_symlink():
                try:
                    total += entry.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    return total


def format_bytes_human(num_bytes: int) -> str:
    """Formats bytes into human-readable MB / GB string."""
    if num_bytes <= 0:
        return "0 MB"
    mb = num_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def _repo_to_folder_prefix(repo_id: str) -> str:
    """Converts a HuggingFace repo ID (e.g. 'Systran/faster-whisper-base') to its cached directory pattern."""
    return f"models--{repo_id.replace('/', '--')}"


def find_model_path_on_disk(repo_id: str, models_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Checks if a model repository is downloaded in models_dir (or legacy cache).
    Returns Path if valid model weights exist (.bin, .safetensors, or model.bin).
    """
    check_dirs = [models_dir or get_default_models_dir()]
    legacy = Path.home() / ".cache" / "transcriber" / "models"
    if legacy not in check_dirs and legacy.exists():
        check_dirs.append(legacy)

    folder_prefix = _repo_to_folder_prefix(repo_id)

    for base_dir in check_dirs:
        # Check standard huggingface hub directory structure
        candidate = base_dir / folder_prefix
        if candidate.exists() and candidate.is_dir():
            # Verify snapshots have weights
            for weight_file in candidate.rglob("*.bin"):
                if weight_file.is_file() and weight_file.stat().st_size > 10 * 1024 * 1024:
                    return candidate
            for weight_file in candidate.rglob("*.safetensors"):
                if weight_file.is_file() and weight_file.stat().st_size > 10 * 1024 * 1024:
                    return candidate

        # Check direct folder without models-- prefix
        direct = base_dir / repo_id.split("/")[-1]
        if direct.exists() and direct.is_dir():
            for weight_file in direct.rglob("*.bin"):
                if weight_file.is_file() and weight_file.stat().st_size > 10 * 1024 * 1024:
                    return direct

    return None


def get_model_status_list() -> List[Dict[str, Any]]:
    """
    Returns the complete list of model tiers, their installation state, disk size,
    and any active download progress.
    """
    models_dir = get_default_models_dir()
    results = []

    with _DOWNLOAD_LOCK:
        active_downloads = dict(_DOWNLOAD_STATE)

    for tier_id, meta in MODEL_REGISTRY.items():
        found_path = find_model_path_on_disk(meta["repo_id"], models_dir)
        is_installed = found_path is not None
        size_bytes = get_dir_size_bytes(found_path) if found_path else 0

        # Check active download status
        download_info = active_downloads.get(tier_id, {
            "status": "idle",
            "progress_percent": 0.0,
            "error": None,
        })

        actual_mb = round(size_bytes / (1024 * 1024), 1) if size_bytes else 0.0
        results.append({
            "id": tier_id,
            "name": meta["name"],
            "label": meta["label"],
            "repo_id": meta["repo_id"],
            "approx_size_mb": meta["approx_size_mb"],
            "approx_size_bytes": meta["approx_size_bytes"],
            "ram_required": meta["ram_required"],
            "speed_rating": meta["speed_rating"],
            "accuracy_rating": meta["accuracy_rating"],
            "description": meta["description"],
            "is_default_bundled": meta["is_default_bundled"],
            "is_installed": is_installed,
            "installed_path": str(found_path) if found_path else None,
            "installed_size_bytes": size_bytes,
            "actual_size_mb": actual_mb,
            "installed_size_formatted": format_bytes_human(size_bytes) if is_installed else "Not Installed",
            "download_status": download_info.get("status", "idle"),
            "download_percent": download_info.get("progress_percent", 0.0),
            "download_progress": int(download_info.get("progress_percent", 0.0)),
            "download_error": download_info.get("error"),
        })

    return results


def start_model_download(tier_id: str) -> Dict[str, Any]:
    """
    Initiates an asynchronous background download of model weights.
    Returns initial download status.
    """
    tier_id = tier_id.lower()
    if tier_id not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model tier: {tier_id}")

    meta = MODEL_REGISTRY[tier_id]
    models_dir = get_default_models_dir()

    with _DOWNLOAD_LOCK:
        current = _DOWNLOAD_STATE.get(tier_id, {})
        if current.get("status") == "downloading":
            return {
                "tier": tier_id,
                "tier_id": tier_id,
                "status": "downloading",
                "message": "Download is already in progress.",
                "progress": int(current.get("progress_percent", 0.0)),
                "progress_percent": current.get("progress_percent", 0.0),
            }

        _DOWNLOAD_STATE[tier_id] = {
            "status": "downloading",
            "progress_percent": 2.0,
            "bytes_downloaded": 0,
            "total_bytes": meta["approx_size_bytes"],
            "error": None,
        }

    def _worker():
        try:
            from faster_whisper import download_model

            # Update progress checkpoint
            with _DOWNLOAD_LOCK:
                _DOWNLOAD_STATE[tier_id]["progress_percent"] = 15.0

            # Use cache_dir so Hugging Face organizes weights identically to WhisperModel download_root
            download_model(meta["repo_id"], cache_dir=str(models_dir))

            with _DOWNLOAD_LOCK:
                _DOWNLOAD_STATE[tier_id] = {
                    "status": "completed",
                    "progress_percent": 100.0,
                    "bytes_downloaded": meta["approx_size_bytes"],
                    "total_bytes": meta["approx_size_bytes"],
                    "error": None,
                }
        except Exception as e:
            with _DOWNLOAD_LOCK:
                _DOWNLOAD_STATE[tier_id] = {
                    "status": "error",
                    "progress_percent": 0.0,
                    "bytes_downloaded": 0,
                    "total_bytes": meta["approx_size_bytes"],
                    "error": str(e),
                }

    thread = threading.Thread(target=_worker, daemon=True, name=f"model-dl-{tier_id}")
    thread.start()

    return {
        "tier": tier_id,
        "tier_id": tier_id,
        "status": "downloading",
        "message": f"Downloading {meta['name']} in background.",
        "progress": 2,
        "progress_percent": 2.0,
    }


def get_download_status(tier_id: str) -> Dict[str, Any]:
    """Returns the live download status of a model tier."""
    tier_id = tier_id.lower()
    with _DOWNLOAD_LOCK:
        state = _DOWNLOAD_STATE.get(tier_id)

    if not state:
        # Check if already installed
        meta = MODEL_REGISTRY.get(tier_id)
        is_inst = bool(find_model_path_on_disk(meta["repo_id"])) if meta else False
        pct = 100.0 if is_inst else 0.0
        return {
            "tier": tier_id,
            "tier_id": tier_id,
            "status": "completed" if is_inst else "idle",
            "progress": int(pct),
            "progress_percent": pct,
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "error": None,
            "error_message": None,
        }

    pct = state.get("progress_percent", 0.0)
    err = state.get("error")
    return {
        "tier": tier_id,
        "tier_id": tier_id,
        "status": state.get("status", "idle"),
        "progress": int(pct),
        "progress_percent": pct,
        "bytes_downloaded": state.get("bytes_downloaded", 0),
        "total_bytes": state.get("total_bytes", 0),
        "error": err,
        "error_message": err,
    }


def delete_model(tier_id: str) -> Dict[str, Any]:
    """
    Safely removes a downloaded model from disk to reclaim storage space.
    """
    tier_id = tier_id.lower()
    if tier_id not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model tier: {tier_id}")

    meta = MODEL_REGISTRY[tier_id]
    models_dir = get_default_models_dir()
    found_path = find_model_path_on_disk(meta["repo_id"], models_dir)

    if not found_path or not found_path.exists():
        return {
            "tier": tier_id,
            "tier_id": tier_id,
            "success": False,
            "deleted": False,
            "freed_bytes": 0,
            "freed_mb": 0.0,
            "freed_formatted": "0 MB",
            "message": "Model is not installed on disk.",
        }

    size_freed = get_dir_size_bytes(found_path)
    shutil.rmtree(found_path, ignore_errors=True)

    # Clean up state
    with _DOWNLOAD_LOCK:
        if tier_id in _DOWNLOAD_STATE:
            del _DOWNLOAD_STATE[tier_id]

    # Invalidate cached Whisper instance if this was the loaded tier
    try:
        from engine.transcriber import TranscriberEngine
        with TranscriberEngine._model_lock:
            if TranscriberEngine._loaded_tier == tier_id:
                del TranscriberEngine._loaded_model
                TranscriberEngine._loaded_model = None
                TranscriberEngine._loaded_tier = None
    except Exception:
        pass

    freed_mb = round(size_freed / (1024 * 1024), 1)
    return {
        "tier": tier_id,
        "tier_id": tier_id,
        "success": True,
        "deleted": True,
        "freed_bytes": size_freed,
        "freed_mb": freed_mb,
        "freed_formatted": format_bytes_human(size_freed),
        "message": f"Successfully deleted {meta['name']} ({format_bytes_human(size_freed)} freed).",
    }
