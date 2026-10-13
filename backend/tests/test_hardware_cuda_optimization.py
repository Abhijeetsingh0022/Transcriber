"""
Unit Tests for Transcriber Hardware Abstraction Layer (HAL) & Windows CPU/GPU Optimization.
Verifies:
1. Windows machines route ML inference majorly to CPU by default (wisely chosen int8_float32 + core reservation).
2. Explicit TRANSCRIBER_DEVICE=cuda override activates RTX 2080 Turing Tensor Cores.
3. Turing bfloat16 safety guard and float16/int8_float16 precision routing.
4. Windows CUDA DLL directory resolution.
5. System telemetry reporting unburdened GPU state when ML executes on CPU.
"""

import os
import sys
from unittest.mock import patch, MagicMock
import pytest

from engine.hardware import (
    setup_windows_cuda_dll_paths,
    get_compute_backend,
    get_system_telemetry,
)
from engine.audio import find_ffmpeg_binary


def test_windows_cuda_dll_setup_safe_execution():
    """Verifies setup_windows_cuda_dll_paths executes cleanly without errors."""
    res = setup_windows_cuda_dll_paths()
    assert isinstance(res, list)


def test_windows_routes_ml_majorly_to_cpu_wisely():
    """
    Verifies that on a Windows machine, ML is routed to the Host CPU by default,
    wisely using int8_float32 quantization and reserving CPU headroom for the OS/UI,
    even if an NVIDIA GPU is physically present.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.device.return_value = "cpu"

    get_compute_backend.cache_clear()

    with patch("sys.platform", "win32"), \
         patch("psutil.cpu_count", return_value=8), \
         patch.dict(os.environ, {}, clear=True), \
         patch("engine.hardware.torch", mock_torch):

        backend = get_compute_backend()
        assert backend["platform"] == "Windows Host CPU (AVX2/INT8 Vector Optimized)"
        assert backend["whisper_device"] == "cpu"
        assert backend["compute_type"] == "int8_float32"
        # 8 physical cores -> 7 worker threads, reserving 1 core for Windows DWM & 60fps UI
        assert backend["cpu_threads"] == 7
        assert backend["physical_cores"] == 8

    get_compute_backend.cache_clear()


def test_windows_explicit_cuda_override():
    """
    Verifies that when TRANSCRIBER_DEVICE=cuda is explicitly set on Windows,
    the backend activates the NVIDIA RTX 2080 with Turing FP16 Tensor Cores.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)  # Turing CC 7.5
    
    mock_props = MagicMock()
    mock_props.total_memory = 8 * 1024 * 1024 * 1024  # 8 GB GDDR6
    mock_torch.cuda.get_device_properties.return_value = mock_props
    mock_torch.device.return_value = "cuda"

    get_compute_backend.cache_clear()

    with patch("sys.platform", "win32"), \
         patch.dict(os.environ, {"TRANSCRIBER_DEVICE": "cuda"}), \
         patch("engine.hardware.torch", mock_torch):

        backend = get_compute_backend()
        assert backend["platform"] == "NVIDIA CUDA"
        assert backend["device_name"] == "NVIDIA GeForce RTX 2080"
        assert backend["whisper_device"] == "cuda"
        assert backend["compute_type"] == "float16"
        assert backend["supports_fp16"] is True
        assert backend["supports_bf16"] is False  # Turing lacks native bf16
        assert backend["vram_total_mb"] == 8192

    get_compute_backend.cache_clear()


def test_turing_low_vram_int8_fp16_routing():
    """
    Verifies that when CUDA is active on a GPU with constrained VRAM (< 5.5GB),
    the HAL selects int8_float16 for high-speed, low-memory Tensor Core execution.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080 Mobile"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)
    
    mock_props = MagicMock()
    mock_props.total_memory = 4 * 1024 * 1024 * 1024  # 4 GB VRAM
    mock_torch.cuda.get_device_properties.return_value = mock_props

    get_compute_backend.cache_clear()

    with patch("sys.platform", "linux"), \
         patch.dict(os.environ, {}, clear=True), \
         patch("engine.hardware.torch", mock_torch):

        backend = get_compute_backend()
        assert backend["compute_type"] == "int8_float16"
        assert backend["vram_total_mb"] == 4096

    get_compute_backend.cache_clear()


def test_turing_guards_against_unsupported_bfloat16():
    """
    Verifies that if TRANSCRIBER_COMPUTE_TYPE=bfloat16 is requested with CUDA,
    the HAL protects Turing (CC 7.5) by falling back to float16.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)
    mock_props = MagicMock()
    mock_props.total_memory = 8 * 1024 * 1024 * 1024
    mock_torch.cuda.get_device_properties.return_value = mock_props

    get_compute_backend.cache_clear()

    with patch("sys.platform", "linux"), \
         patch.dict(os.environ, {"TRANSCRIBER_COMPUTE_TYPE": "bfloat16"}), \
         patch("engine.hardware.torch", mock_torch):

        backend = get_compute_backend()
        assert backend["compute_type"] == "float16"

    get_compute_backend.cache_clear()


def test_telemetry_reports_gpu_unburdened_when_cpu_executes_ml():
    """Verifies telemetry correctly reports GPU availability and unburdened status."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    # 6GB free, 8GB total
    mock_torch.cuda.mem_get_info.return_value = (6 * 1024**3, 8 * 1024**3)
    mock_torch.cuda.memory_allocated.return_value = 0
    mock_torch.cuda.memory_reserved.return_value = 0

    mock_backend = {
        "platform": "Windows Host CPU (AVX2/INT8 Vector Optimized)",
        "device_name": "Host CPU (8 Cores, 7 Worker Threads)",
        "whisper_device": "cpu",
        "compute_type": "int8_float32",
        "vram_total_mb": None,
    }

    with patch("engine.hardware.get_compute_backend", return_value=mock_backend), \
         patch("engine.hardware.torch", mock_torch), \
         patch("engine.hardware._TELEMETRY_CACHE", {}):

        telemetry = get_system_telemetry()
        assert telemetry["gpu_name"] == "NVIDIA GeForce RTX 2080"
        assert telemetry["vram_total_mb"] == 8192
        assert telemetry["vram_free_mb"] == 6144
        assert "Unburdened" in telemetry["gpu_status"]


def test_ffmpeg_binary_find_does_not_crash():
    """Verifies find_ffmpeg_binary operates cleanly."""
    bin_path = find_ffmpeg_binary()
    assert bin_path is None or isinstance(bin_path, str)
