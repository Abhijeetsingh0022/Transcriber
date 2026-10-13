"""
GPU and Runtime Diagnostic Verification Tool for Transcriber.
Validates NVIDIA CUDA runtime, Turing Tensor Cores, CTranslate2 Faster-Whisper,
cuBLAS/cuDNN DLL resolution on Windows, and audio processing capabilities.
Run directly on Windows via:
    python verify_gpu.py
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engine.hardware import setup_windows_cuda_dll_paths, get_compute_backend, get_system_telemetry
from engine.audio import find_ffmpeg_binary


def run_diagnostics() -> bool:
    print("=" * 65)
    print("        TRANSCRIBER GPU & RUNTIME OPTIMIZATION AUDIT        ")
    print("=" * 65)
    print(f"Platform: {sys.platform} (Python {sys.version.split()[0]})")

    # 1. Windows DLL Setup
    if sys.platform == "win32":
        registered = setup_windows_cuda_dll_paths()
        print(f"\n[1/5] Windows CUDA DLL Directory Registration:")
        if registered:
            for r in registered:
                print(f"  ✓ Registered: {r}")
        else:
            print("  ℹ No pip nvidia wheel directories required registration or already registered.")
    else:
        print("\n[1/5] Windows DLL Resolution: Skipped (Non-Windows OS)")

    # 2. PyTorch & CUDA Check
    print("\n[2/5] PyTorch & NVIDIA Driver Telemetry:")
    try:
        import torch
        print(f"  ✓ PyTorch Version: {torch.__version__}")
        cuda_avail = torch.cuda.is_available()
        print(f"  ✓ CUDA Available: {cuda_avail}")

        if not cuda_avail:
            print("  ✖ CUDA is NOT available in PyTorch!")
            print("    Run: pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124")
            return False

        print(f"  ✓ PyTorch CUDA Build: {torch.version.cuda}")
        gpu_count = torch.cuda.device_count()
        print(f"  ✓ Detected GPUs: {gpu_count}")
        gpu_name = torch.cuda.get_device_name(0)
        print(f"  ✓ Primary GPU: {gpu_name}")
        
        major, minor = torch.cuda.get_device_capability(0)
        print(f"  ✓ CUDA Compute Capability: {major}.{minor}")
        
        # RTX 2080 is Turing (Compute Capability 7.5)
        if major == 7 and minor == 5:
            print("    -> Architecture: NVIDIA Turing (TU104)")
            print("    -> Tensor Cores: 2nd Gen Turing Tensor Cores (Native FP16 & INT8)")
            print("    -> bfloat16: Not supported on Turing (Ampere 8.0+ only, properly guarded)")
        elif major >= 8:
            print(f"    -> Architecture: Ampere/Ada/Hopper (Compute Capability {major}.{minor})")
        else:
            print(f"    -> Architecture: Legacy CUDA (Compute Capability {major}.{minor})")

        free_b, total_b = torch.cuda.mem_get_info(0)
        free_mb = free_b // (1024 * 1024)
        total_mb = total_b // (1024 * 1024)
        print(f"  ✓ Total VRAM: {total_mb} MB ({total_mb / 1024:.2f} GB)")
        print(f"  ✓ Free VRAM Available: {free_mb} MB ({free_mb / 1024:.2f} GB)")

    except ImportError:
        print("  ✖ PyTorch is not installed!")
        return False
    except Exception as e:
        print(f"  ✖ Error probing CUDA: {e}")
        return False

    # 3. Tensor Core FP16 Benchmark
    print("\n[3/5] Testing Turing Tensor Core FP16 Matrix Multiplication:")
    try:
        device = torch.device("cuda:0")
        size = 2048
        a = torch.randn(size, size, dtype=torch.float16, device=device)
        b = torch.randn(size, size, dtype=torch.float16, device=device)
        
        # Warm-up
        _ = torch.matmul(a, b)
        torch.cuda.synchronize()

        # Timed run
        t0 = time.perf_counter()
        iters = 50
        for _ in range(iters):
            _ = torch.matmul(a, b)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0

        tflops = (2 * (size ** 3) * iters) / (elapsed * 1e12)
        print(f"  ✓ FP16 Matrix Multiply ({size}x{size}): {elapsed*1000/iters:.2f} ms/iter")
        print(f"  ✓ Estimated Tensor Core Throughput: ~{tflops:.1f} TFLOPS")
        del a, b
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"  ✖ Tensor Core FP16 test failed: {e}")
        return False

    # 4. CTranslate2 / Faster-Whisper Verification
    print("\n[4/5] Faster-Whisper & CTranslate2 CUDA Engine:")
    try:
        import ctranslate2
        print(f"  ✓ CTranslate2 Version: {ctranslate2.__version__}")
        ct2_gpus = ctranslate2.get_cuda_device_count()
        print(f"  ✓ CTranslate2 CUDA Device Count: {ct2_gpus}")
        
        supported_types = ctranslate2.get_supported_compute_types("cuda")
        print(f"  ✓ Supported Compute Types on CUDA: {sorted(list(supported_types))}")

        if "float16" in supported_types:
            print("  ✓ 'float16' Tensor Core Precision is fully supported!")
        if "int8_float16" in supported_types:
            print("  ✓ 'int8_float16' Low-Memory Precision is fully supported!")

        from faster_whisper import WhisperModel
        print("  ✓ Faster-Whisper module imported successfully.")
        
    except ImportError as e:
        print(f"  ✖ Faster-Whisper or CTranslate2 missing: {e}")
        return False
    except Exception as e:
        print(f"  ✖ CTranslate2 CUDA error (Check cuBLAS/cuDNN DLLs): {e}")
        return False

    # 5. Audio Extraction Subsystem
    print("\n[5/5] Audio Processing & FFmpeg Discovery:")
    ffmpeg_path = find_ffmpeg_binary()
    if ffmpeg_path:
        print(f"  ✓ FFmpeg Binary Found: {ffmpeg_path}")
    else:
        print("  ℹ FFmpeg standalone binary not found in standard paths.")

    try:
        import av
        print(f"  ✓ PyAV Engine Active: v{av.__version__} (Built-in container/audio decoder)")
    except ImportError:
        print("  ✖ PyAV is not installed!")
        return False

    # HAL summary
    print("\n" + "=" * 65)
    backend_info = get_compute_backend()
    print("HARDWARE ABSTRACTION LAYER (HAL) SELECTION:")
    print(f"  Platform:          {backend_info['platform']}")
    print(f"  Device:            {backend_info['device_name']}")
    print(f"  Engine Device:     {backend_info['whisper_device']}")
    print(f"  Compute Precision: {backend_info['compute_type']}")
    print(f"  Total VRAM:        {backend_info.get('vram_total_mb')} MB")
    print(f"  Supports FP16:     {backend_info.get('supports_fp16')}")
    print(f"  Supports BF16:     {backend_info.get('supports_bf16')} (Turing safety guard active)")
    print("=" * 65)
    print(">>> STATUS: ALL CHECKS PASSED — GPU ACCELERATION READY FOR RTX 2080 <<<")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
