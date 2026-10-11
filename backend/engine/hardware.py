"""
Hardware Abstraction Layer (HAL) for Transcriber.
Detects runtime compute backend (NVIDIA CUDA, Apple Silicon MPS, or CPU)
and determines optimal precision (float16 vs int8) and device routing.
"""

from typing import Dict, Any
import os
import time
import functools
import psutil

try:
    import torch
except ImportError:
    torch = None


@functools.lru_cache(maxsize=1)
def get_compute_backend() -> Dict[str, Any]:
    """
    Inspects available hardware accelerators and returns optimal configuration.
    """
    total_cores = os.cpu_count() or 4
    # Faster-Whisper / CTranslate2 scales best with 4 to 8 threads on multi-core host CPUs
    optimal_cpu_threads = min(8, max(2, total_cores))

    if torch is not None and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_total_mb = int(vram_total_bytes / (1024 * 1024))
        
        return {
            "platform": "NVIDIA CUDA",
            "device_name": gpu_name,
            "whisper_device": "cuda",
            "compute_type": "float16",  # Tensor Core acceleration
            "torch_device": torch.device("cuda"),
            "torch_device_str": "cuda",
            "vram_total_mb": vram_total_mb,
            "supports_fp16": True,
            "cpu_threads": 4,
        }
    
    # Check for Apple Silicon Metal Performance Shaders (MPS)
    if torch is not None and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return {
            "platform": "Apple Silicon (MPS + Accelerate)",
            "device_name": "Apple M-Series Neural/GPU",
            # Note: CTranslate2 uses CPU with ARM NEON / Accelerate vector SIMD on Mac
            "whisper_device": "cpu",
            "compute_type": "int8_float32",  # int8 weights with float32 accumulation for maximum numerical precision
            "torch_device": torch.device("mps"),
            "torch_device_str": "mps",
            "vram_total_mb": None,  # Uses Unified System Memory
            "supports_fp16": False,
            "cpu_threads": optimal_cpu_threads,
        }
        
    # Standard CPU Fallback
    return {
        "platform": "Generic CPU",
        "device_name": "Host CPU",
        "whisper_device": "cpu",
        "compute_type": "int8_float32",
        "torch_device": torch.device("cpu") if torch is not None else None,
        "torch_device_str": "cpu",
        "vram_total_mb": None,
        "supports_fp16": False,
        "cpu_threads": optimal_cpu_threads,
    }


_TELEMETRY_CACHE: Dict[str, Any] = {}
_TELEMETRY_CACHE_TIME: float = 0.0


def get_system_telemetry() -> Dict[str, Any]:
    """
    Returns live system metrics: VRAM/RAM utilization and CPU load.
    Cached for 0.8s to eliminate redundant psutil sampling on rapid polling.
    """
    global _TELEMETRY_CACHE, _TELEMETRY_CACHE_TIME
    now = time.time()
    if _TELEMETRY_CACHE and (now - _TELEMETRY_CACHE_TIME < 0.8):
        return dict(_TELEMETRY_CACHE)

    backend = get_compute_backend()
    mem = psutil.virtual_memory()
    
    telemetry = {
        "platform": backend["platform"],
        "device_name": backend["device_name"],
        "cpu_threads": os.cpu_count() or 1,
        "cpu_usage_percent": psutil.cpu_percent(interval=None),
        "system_ram_total_gb": round(mem.total / (1024**3), 2),
        "system_ram_available_gb": round(mem.available / (1024**3), 2),
        "system_ram_used_percent": mem.percent,
        "vram_total_mb": backend.get("vram_total_mb"),
        "vram_allocated_mb": 0,
        "vram_free_mb": 0,
    }
    
    if torch is not None and torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
        reserved = torch.cuda.memory_reserved(0) / (1024 * 1024)
        total = backend.get("vram_total_mb") or 0
        telemetry["vram_allocated_mb"] = int(allocated)
        telemetry["vram_reserved_mb"] = int(reserved)
        telemetry["vram_free_mb"] = max(0, int(total - reserved))
        
    _TELEMETRY_CACHE = telemetry
    _TELEMETRY_CACHE_TIME = now
    return dict(telemetry)


if __name__ == "__main__":
    import json
    print("Transcriber Hardware Backend Detection:")
    backend_info = get_compute_backend()
    # Format torch.device for JSON printing
    info_printable = {k: str(v) for k, v in backend_info.items()}
    print(json.dumps(info_printable, indent=2))
    print("\nLive System Telemetry:")
    print(json.dumps(get_system_telemetry(), indent=2))
