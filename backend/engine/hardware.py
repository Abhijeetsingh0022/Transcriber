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
    For Windows machines, ML inference is routed majorly to the Host CPU by default,
    wisely tuned with AVX2 vector SIMD, int8_float32 quantization, and physical core thread pooling,
    preserving GPU VRAM and 3D resources for studio video playback, muxing, and desktop UI.
    """
    total_logical = os.cpu_count() or 4
    try:
        physical_cores = psutil.cpu_count(logical=False) or total_logical
    except Exception:
        physical_cores = total_logical

    # Wisely calculate CPU worker threads:
    # Avoid thread contention and cache thrashing across Hyper-Threading / E-cores.
    # On Windows, leave 1-2 physical cores free for Windows DWM, audio playback, and browser.
    if sys.platform == "win32" and physical_cores > 4:
        optimal_cpu_threads = min(8, physical_cores - 1)
    else:
        optimal_cpu_threads = min(8, max(2, physical_cores))

    # Configure PyTorch CPU thread pool to match optimal threads
    if torch is not None:
        try:
            torch.set_num_threads(optimal_cpu_threads)
            torch.set_num_interop_threads(2)
        except Exception:
            pass

    # Check explicit user preference override (e.g. TRANSCRIBER_DEVICE=cuda or cpu)
    device_override = os.environ.get("TRANSCRIBER_DEVICE", "").strip().lower()

    # Determine if CUDA should be used:
    # 1. On non-Windows platforms (e.g. Linux servers/cloud), CUDA is default if available.
    # 2. On Windows machines, default to CPU to keep GPU VRAM/render pipeline free for studio,
    #    unless TRANSCRIBER_DEVICE=cuda is explicitly specified.
    wants_cuda = False
    if torch is not None and torch.cuda.is_available():
        if device_override in ("cuda", "gpu"):
            wants_cuda = True
        elif sys.platform != "win32":
            # On Linux / headless servers, use CUDA by default if available
            wants_cuda = (device_override != "cpu")
        else:
            # On Windows, user requested: run ML part majorly on CPU
            wants_cuda = False

    if wants_cuda:
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
        env_pref = os.environ.get("TRANSCRIBER_COMPUTE_TYPE", "").strip().lower()
        if env_pref in ("float16", "int8_float16", "int8", "float32"):
            compute_type = env_pref
            if compute_type == "bfloat16" and not supports_bf16:
                compute_type = "float16"
        elif supports_fp16:
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
            "physical_cores": physical_cores,
        }
    
    # Check for Apple Silicon Metal Performance Shaders (MPS)
    if sys.platform != "win32" and torch is not None and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
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
            "physical_cores": physical_cores,
        }
        
    # Windows Host CPU (or generic CPU) - Wisely Chosen
    platform_name = (
        "Windows Host CPU (AVX2/INT8 Vector Optimized)"
        if sys.platform == "win32"
        else "Generic Host CPU (Vector Optimized)"
    )
    device_label = (
        f"Host CPU ({physical_cores} Cores, {optimal_cpu_threads} Worker Threads)"
    )

    return {
        "platform": platform_name,
        "device_name": device_label,
        "whisper_device": "cpu",
        "compute_type": "int8_float32",  # 8-bit quantized weights + float32 accumulation: 3x-4x faster than fp32 on CPU
        "torch_device": torch.device("cpu") if torch is not None else None,
        "torch_device_str": "cpu",
        "vram_total_mb": None,
        "supports_fp16": False,
        "supports_bf16": False,
        "cuda_compute_capability": None,
        "cpu_threads": optimal_cpu_threads,
        "physical_cores": physical_cores,
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
            telemetry["gpu_name"] = torch.cuda.get_device_name(0)
            telemetry["vram_total_mb"] = int(total_bytes / (1024 * 1024))
            telemetry["vram_free_mb"] = int(free_bytes / (1024 * 1024))
            telemetry["vram_allocated_mb"] = int(allocated_bytes / (1024 * 1024))
            telemetry["vram_reserved_mb"] = int(reserved_bytes / (1024 * 1024))
            telemetry["gpu_status"] = (
                "Active (Inference)" if backend["whisper_device"] == "cuda"
                else "Unburdened (Dedicated to Studio Video & Display)"
            )
        except Exception:
            allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)
            reserved = torch.cuda.memory_reserved(0) / (1024 * 1024)
            total = backend.get("vram_total_mb") or 0
            telemetry["gpu_name"] = torch.cuda.get_device_name(0)
            telemetry["vram_allocated_mb"] = int(allocated)
            telemetry["vram_reserved_mb"] = int(reserved)
            telemetry["vram_free_mb"] = max(0, int(total - reserved))
            telemetry["gpu_status"] = "Available"
        
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
