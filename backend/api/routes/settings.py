"""
Settings & Model Manager API Endpoints.
Provides client control over cloud AI keys, local model downloads, and engine preferences.
"""

import shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from services import settings_service, model_service

router = APIRouter(prefix="/settings", tags=["Settings & Models"])


class ApiKeysPayload(BaseModel):
    gemini_key: Optional[str] = None
    openrouter_key: Optional[str] = None
    tokenharbor_key: Optional[str] = None
    gemini_keys: Optional[List[str]] = None
    openrouter_keys: Optional[List[str]] = None
    tokenharbor_keys: Optional[List[str]] = None


class VerifyKeyPayload(BaseModel):
    provider: str = Field(default="gemini", description="'gemini', 'openrouter', or 'tokenharbor'")
    key: Optional[str] = None
    key_index: Optional[int] = None


class AddKeyPayload(BaseModel):
    provider: str = Field(..., description="'gemini', 'openrouter', or 'tokenharbor'")
    key: str = Field(..., description="API key to add to the provider's pool")


class RemoveKeyPayload(BaseModel):
    provider: str = Field(..., description="'gemini', 'openrouter', or 'tokenharbor'")
    key_index: Optional[int] = None
    key: Optional[str] = None


@router.get("/keys")
def get_api_keys():
    """Returns the configuration status, count, and masked values of API keys across all 3 providers."""
    return settings_service.get_keys_status()


@router.post("/keys")
def save_api_keys(payload: ApiKeysPayload):
    """Saves API keys to persistent SQLite settings and updates environment."""
    return settings_service.save_api_keys(
        gemini_key=payload.gemini_key,
        openrouter_key=payload.openrouter_key,
        tokenharbor_key=payload.tokenharbor_key,
        gemini_keys=payload.gemini_keys,
        openrouter_keys=payload.openrouter_keys,
        tokenharbor_keys=payload.tokenharbor_keys,
    )


@router.post("/keys/add")
def add_api_key(payload: AddKeyPayload):
    """Adds a new key to a provider's key pool for multi-key load balancing and auto-failover."""
    provider = payload.provider.lower().strip()
    if provider not in ("gemini", "openrouter", "tokenharbor", "token_harbor"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: '{payload.provider}'")
    if not payload.key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    settings_service.add_provider_key(provider, payload.key.strip())
    return settings_service.get_keys_status()


@router.post("/keys/remove")
def remove_api_key(payload: RemoveKeyPayload):
    """Removes an API key from a provider's pool by index or raw key."""
    provider = payload.provider.lower().strip()
    if provider not in ("gemini", "openrouter", "tokenharbor", "token_harbor"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: '{payload.provider}'")
    identifier = payload.key_index if payload.key_index is not None else payload.key
    if identifier is None:
        raise HTTPException(status_code=400, detail="Must provide key_index or key to remove.")
    settings_service.remove_provider_key(provider, identifier)
    return settings_service.get_keys_status()


@router.post("/keys/verify")
def verify_api_key(payload: VerifyKeyPayload):
    """
    Sends a live test prompt to verify an API key and measure round-trip latency.
    """
    provider = payload.provider.lower().strip()
    if provider == "gemini":
        result = settings_service.verify_gemini_key(payload.key, payload.key_index)
    elif provider == "openrouter":
        result = settings_service.verify_openrouter_key(payload.key, payload.key_index)
    elif provider in ("tokenharbor", "token_harbor"):
        result = settings_service.verify_tokenharbor_key(payload.key, payload.key_index)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: '{payload.provider}'")

    return result


@router.get("/models")
def list_models():
    """Returns all supported speech models with disk status and download progress."""
    return model_service.get_model_status_list()


@router.post("/models/{tier}/download")
def download_model(tier: str):
    """Initiates an asynchronous background download of a model tier."""
    try:
        return model_service.start_model_download(tier)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")


@router.get("/models/{tier}/download/status")
def model_download_status(tier: str):
    """Polls live download progress for a specific model tier."""
    return model_service.get_download_status(tier)


@router.delete("/models/{tier}")
def delete_model(tier: str):
    """Safely removes downloaded model weights to reclaim disk space."""
    try:
        return model_service.delete_model(tier)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.get("/storage")
def get_storage_info():
    """Returns the persistent models directory location and available disk space."""
    models_dir = model_service.get_default_models_dir()
    try:
        disk_usage = shutil.disk_usage(models_dir)
        total_gb = round(disk_usage.total / (1024**3), 2)
        free_gb = round(disk_usage.free / (1024**3), 2)
        used_gb = round(disk_usage.used / (1024**3), 2)
    except Exception:
        total_gb, free_gb, used_gb = 0.0, 0.0, 0.0

    return {
        "models_directory": str(models_dir),
        "total_disk_gb": total_gb,
        "free_disk_gb": free_gb,
        "used_disk_gb": used_gb,
    }


# ── SQLite Database Performance & Maintenance ───────────────────────────────

class CheckpointPayload(BaseModel):
    mode: str = Field(default="TRUNCATE", description="'PASSIVE', 'FULL', 'RESTART', or 'TRUNCATE'")


class VacuumPayload(BaseModel):
    incremental: bool = Field(default=False, description="True for non-blocking incremental vacuum, False for full VACUUM")
    pages: int = Field(default=1000, description="Pages to vacuum if incremental is True")


@router.get("/database/stats")
def get_database_statistics():
    """Returns real-time SQLite health metrics, table row counts, page size, and WAL status."""
    from db.database import get_db_stats
    return get_db_stats()


@router.post("/database/checkpoint")
def checkpoint_database(payload: CheckpointPayload = CheckpointPayload()):
    """Triggers an immediate SQLite WAL checkpoint to sync WAL frames into transcriber.db."""
    from db.database import wal_checkpoint
    return wal_checkpoint(mode=payload.mode)


@router.post("/database/vacuum")
def vacuum_database(payload: VacuumPayload = VacuumPayload()):
    """Reclaims unused SQLite pages and defragments the database file."""
    from db.database import vacuum_db
    return vacuum_db(incremental=payload.incremental, pages=payload.pages)

