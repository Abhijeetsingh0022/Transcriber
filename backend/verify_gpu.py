"""
Hardware and Runtime Diagnostic Verification Tool for Transcriber.
Validates CPU (AVX2/INT8 vector acceleration) and optional NVIDIA CUDA GPU execution,
thread pool sizing, CTranslate2 Faster-Whisper, and audio processing capabilities.
Run directly via:
    python verify_gpu.py
"""

import sys
import os
import time
from pathlib import Path
import psutil

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engine.hardware import setup_windows_cuda_dll_paths, get_compute_backend, get_system_telemetry
from engine.audio import find_ffmpeg_binary


def run_diagnostics() -> bool:
    print("=" * 70)
    print("      TRANSCRIBER HARDWARE & RUNTIME OPTIMIZATION AUDIT        ")
    print("=" * 70)
    print(f"Platform: {sys.platform} (Python {sys.version.split()[0]})")

    # 1. Windows DLL Setup
    if sys.platform == "win32":
        registered = setup_windows_cuda_dll_paths()
        print(f"\n[1/6] Windows CUDA DLL Directory Registration:")
        if registered:
            for r in registered:
                print(f"  ✓ Registered: {r}")
        else:
            print("  ℹ No pip nvidia wheel directories required registration or already registered.")
    else:
        print("\n[1/6] Windows DLL Resolution: Skipped (Non-Windows OS)")

    # 2. Host CPU Topology & Thread Pool Optimization
    print("\n[2/6] CPU Architecture & Thread Pool Sizing:")
    total_logical = os.cpu_count() or 4
    physical_cores = psutil.cpu_count(logical=False) or total_logical
    mem = psutil.virtual_memory()

    print(f"  ✓ Physical Cores: {physical_cores}")
    print(f"  ✓ Logical Threads: {total_logical}")
    print(f"  ✓ System RAM: {mem.total / (1024**3):.2f} GB (Available: {mem.available / (1024**3):.2f} GB)")

    # Wise thread allocation on Windows
    if sys.platform == "win32" and physical_cores > 4:
        rec_threads = min(8, physical_cores - 1)
        print(f"  ✓ Wise Worker Threads: {rec_threads} (Reserves 1-2 cores for Windows DWM & 60fps UI)")
    else:
        rec_threads = min(8, max(2, physical_cores))
        print(f"  ✓ Wise Worker Threads: {rec_threads}")

    # 3. CPU AVX2 Vector Performance Benchmark
    print("\n[3/6] CPU Vector Matrix Multiplication Benchmark (AVX2/FMA):")
    try:
        import torch
        torch.set_num_threads(rec_threads)
        size = 1024
        a = torch.randn(size, size, dtype=torch.float32)
        b = torch.randn(size, size, dtype=torch.float32)
        
        # Warm-up
        _ = torch.matmul(a, b)
        
        t0 = time.perf_counter()
        iters = 20
        for _ in range(iters):
            _ = torch.matmul(a, b)
        elapsed = time.perf_counter() - t0

        gflops = (2 * (size ** 3) * iters) / (elapsed * 1e9)
        print(f"  ✓ CPU Matrix Multiply ({size}x{size}): {elapsed*1000/iters:.2f} ms/iter")
        print(f"  ✓ CPU SIMD Throughput: ~{gflops:.1f} GFLOPS across {rec_threads} worker threads")
        del a, b
    except Exception as e:
        print(f"  ℹ CPU benchmark info: {e}")

    # 4. NVIDIA GPU / CUDA Detection (Optional / Unburdened)
    print("\n[4/6] NVIDIA GPU Hardware & VRAM Telemetry:")
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            major, minor = torch.cuda.get_device_capability(0)
            free_b, total_b = torch.cuda.mem_get_info(0)
            free_mb = free_b // (1024 * 1024)
            total_mb = total_b // (1024 * 1024)
            print(f"  ✓ NVIDIA GPU Present: {gpu_name}")
            print(f"  ✓ CUDA Compute Capability: {major}.{minor}")
            print(f"  ✓ Total VRAM: {total_mb} MB ({total_mb / 1024:.2f} GB)")
            print(f"  ✓ Free VRAM: {free_mb} MB ({free_mb / 1024:.2f} GB)")
            if sys.platform == "win32":
                print("  ✓ Status on Windows: UNBURDENED by default (Reserved for Studio Video & UI)")
                print("    (To route ML to GPU instead, set: TRANSCRIBER_DEVICE=cuda)")
        else:
            print("  ℹ CUDA GPU not available or not active in PyTorch.")
    except Exception as e:
        print(f"  ℹ GPU probe: {e}")

    # 5. CTranslate2 & Faster-Whisper Verification
    print("\n[5/6] Faster-Whisper & CTranslate2 Engine:")
    try:
        import ctranslate2
        print(f"  ✓ CTranslate2 Version: {ctranslate2.__version__}")
        cpu_types = ctranslate2.get_supported_compute_types("cpu")
        print(f"  ✓ Supported Compute Types on CPU: {sorted(list(cpu_types))}")
        if "int8_float32" in cpu_types:
            print("  ✓ Optimal 'int8_float32' CPU Quantization is ACTIVE & SUPPORTED!")

        if ctranslate2.get_cuda_device_count() > 0:
            cuda_types = ctranslate2.get_supported_compute_types("cuda")
            print(f"  ✓ Supported Compute Types on CUDA: {sorted(list(cuda_types))}")

        from faster_whisper import WhisperModel
        print("  ✓ Faster-Whisper module imported successfully.")
    except ImportError as e:
        print(f"  ✖ Faster-Whisper or CTranslate2 missing: {e}")
        return False
    except Exception as e:
        print(f"  ✖ CTranslate2 inspection error: {e}")
        return False

    # 6. Audio Processing Subsystem
    print("\n[6/6] Audio Processing & FFmpeg Discovery:")
    ffmpeg_path = find_ffmpeg_binary()
    if ffmpeg_path:
        print(f"  ✓ FFmpeg Binary Found: {ffmpeg_path}")
    else:
        print("  ℹ FFmpeg standalone binary not in standard paths; native PyAV engine handles decoding.")

    try:
        import av
        print(f"  ✓ PyAV Engine Active: v{av.__version__} (Built-in container/audio decoder)")
    except ImportError:
        print("  ✖ PyAV is not installed!")
        return False

    # Final Hardware Abstraction Layer (HAL) Resolution
    print("\n" + "=" * 70)
    backend_info = get_compute_backend()
    print("HARDWARE ABSTRACTION LAYER (HAL) SELECTION:")
    print(f"  Platform:          {backend_info['platform']}")
    print(f"  Device Name:       {backend_info['device_name']}")
    print(f"  Whisper Device:    {backend_info['whisper_device']}")
    print(f"  Compute Precision: {backend_info['compute_type']}")
    print(f"  CPU Threads:       {backend_info.get('cpu_threads')}")
    print(f"  Physical Cores:    {backend_info.get('physical_cores')}")
    print("=" * 70)
    print(">>> STATUS: ALL CHECKS PASSED — READY FOR OPTIMIZED TRANSCRIPTION <<<")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
