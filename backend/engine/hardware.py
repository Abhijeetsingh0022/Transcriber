"""
Hardware Abstraction Layer (HAL) for Transcriber.
Detects runtime compute backend (NVIDIA CUDA, Apple Silicon MPS, or CPU)
and determines optimal precision (float16 vs int8) and device routing.
"""

import sys
from typing import Dict, Any, List
import os
import time
import functools
from pathlib import Path
import psutil

try:
    import torch
except ImportError:
    torch = None


def setup_windows_cuda_dll_paths() -> List[str]:
    """
    Configures Windows DLL search directories for NVIDIA CUDA, cuBLAS, cuDNN, and PyTorch.
    Ensures CTranslate2 and Faster-Whisper locate cublas64_*.dll and cudnn_ops_infer64_*.dll
    on Windows without requiring manual system PATH changes.
    Returns list of successfully registered DLL directories.
    """
    registered = []
    if sys.platform != "win32":
        return registered

    candidate_dirs = set()

    # 1. Search Python site-packages & virtual environment
    search_roots = [Path(sys.prefix)]
    try:
        import site
        for p in site.getsitepackages():
            search_roots.append(Path(p))
        if hasattr(site, "getusersitepackages"):
            search_roots.append(Path(site.getusersitepackages()))
    except Exception:
        pass

    for root in search_roots:
        if not root.exists():
            continue

        sp_dirs = [root]
        if (root / "Lib" / "site-packages").is_dir():
            sp_dirs.append(root / "Lib" / "site-packages")
        if (root / "site-packages").is_dir():
            sp_dirs.append(root / "site-packages")

        for sp in sp_dirs:
            # NVIDIA pip wheels (nvidia-cublas-cu12, nvidia-cudnn-cu12, etc.)
            nvidia_root = sp / "nvidia"
            if nvidia_root.is_dir():
                for sub in nvidia_root.iterdir():
                    bin_dir = sub / "bin"
                    if bin_dir.is_dir():
                        candidate_dirs.add(str(bin_dir.resolve()))

            # Torch lib directory
            torch_lib = sp / "torch" / "lib"
            if torch_lib.is_dir():
                candidate_dirs.add(str(torch_lib.resolve()))

            # CTranslate2 package directory
            ct2_dir = sp / "ctranslate2"
            if ct2_dir.is_dir():
                candidate_dirs.add(str(ct2_dir.resolve()))

    # 2. CUDA_PATH environment variable & standard toolkit installations
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        cp = Path(cuda_path) / "bin"
        if cp.is_dir():
            candidate_dirs.add(str(cp.resolve()))

    toolkit_root = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA")
    if toolkit_root.is_dir():
        try:
            for p in toolkit_root.glob("*/bin"):
                if p.is_dir():
                    candidate_dirs.add(str(p.resolve()))
        except Exception:
            pass

    # 3. Register directories with os.add_dll_directory and PATH
    path_env = os.environ.get("PATH", "")
    path_parts = [p.strip() for p in path_env.split(";") if p.strip()]

    for d in sorted(candidate_dirs):
        if not os.path.isdir(d):
            continue
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(d)
                registered.append(d)
            except Exception:
                pass
        if d not in path_parts:
            path_parts.insert(0, d)

    os.environ["PATH"] = ";".join(path_parts)
    return registered


# Auto-configure Windows CUDA DLL directories on module import
setup_windows_cuda_dll_paths()


@functools.lru_cache(maxsize=1)
def get_compute_backend() -> Dict[str, Any]:
    """
    Inspects available hardware accelerators and returns optimal configuration.
    Optimized for NVIDIA GPUs (RTX 2080 Turing architecture CC 7.5), Apple Silicon MPS, and CPU.
    """
    total_cores = os.cpu_count() or 4
    # Faster-Whisper / CTranslate2 scales best with 4 to 8 threads on multi-core host CPUs
    optimal_cpu_threads = min(8, max(2, total_cores))

    if torch is not None and torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_total_mb = int(vram_total_bytes / (1024 * 1024))

        # Inspect CUDA compute capability (RTX 2080 is Turing CC 7.5)
        try:
            major, minor = torch.cuda.get_device_capability(0)
        except Exception:
            major, minor = 7, 5

        has_tensor_cores = major >= 7
        supports_fp16 = has_tensor_cores or (major == 6 and minor == 0)
        supports_bf16 = major >= 8  # Ampere (CC 8.0+) or newer; Turing lacks native bf16

        # Optimal precision selection for RTX 2080 (8GB VRAM GDDR6, Turing Tensor Cores):
        # - "float16": Native Turing Tensor Core FP16 execution (~20+ TFLOPS).
        #   Whisper Large-v3 fits into ~3.1 GB VRAM, easily within the 8 GB budget.
        # - "int8_float16": INT8 quantized weights + FP16 tensor core math (~1.6 GB VRAM).
        # - "bfloat16": Not supported on Turing; automatically guarded against.
        env_pref = os.environ.get("TRANSCRIBER_COMPUTE_TYPE", "").strip().lower()
        if env_pref in ("float16", "int8_float16", "int8", "float32"):
            compute_type = env_pref
            if compute_type == "bfloat16" and not supports_bf16:
                compute_type = "float16"
        elif supports_fp16:
            # 8GB VRAM (like RTX 2080) handles float16 reference precision effortlessly.
            # If total VRAM is smaller than 5.5GB, default to int8_float16 to avoid VRAM pressure.
            if vram_total_mb >= 5500:
                compute_type = "float16"
            else:
                compute_type = "int8_float16"
        else:
            compute_type = "float32"

        return {
            "platform": "NVIDIA CUDA",
            "device_name": gpu_name,
            "whisper_device": "cuda",
            "compute_type": compute_type,
            "torch_device": torch.device("cuda"),
            "torch_device_str": "cuda",
            "vram_total_mb": vram_total_mb,
            "supports_fp16": supports_fp16,
            "supports_bf16": supports_bf16,
            "cuda_compute_capability": f"{major}.{minor}",
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
            "supports_bf16": False,
            "cuda_compute_capability": None,
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
        "supports_bf16": False,
        "cuda_compute_capability": None,
        "cpu_threads": optimal_cpu_threads,
    }


_TELEMETRY_CACHE: Dict[str, Any] = {}
_TELEMETRY_CACHE_TIME: float = 0.0


def get_system_telemetry() -> Dict[str, Any]:
    """
    Returns live system metrics: VRAM/RAM utilization and CPU load.
    Cached for 0.8s to eliminate redundant psutil sampling on rapid polling.
    Uses torch.cuda.mem_get_info() for true physical driver-level VRAM tracking.
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
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            allocated_bytes = torch.cuda.memory_allocated(0)
            reserved_bytes = torch.cuda.memory_reserved(0)
            telemetry["vram_total_mb"] = int(total_bytes / (1024 * 1024))
            telemetry["vram_free_mb"] = int(free_bytes / (1024 * 1024))
            telemetry["vram_allocated_mb"] = int(allocated_bytes / (1024 * 1024))
            telemetry["vram_reserved_mb"] = int(reserved_bytes / (1024 * 1024))
        except Exception:
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
