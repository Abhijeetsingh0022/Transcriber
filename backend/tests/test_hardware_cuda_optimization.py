"""
Unit Tests for Transcriber Hardware Abstraction Layer (HAL) & CUDA Optimization.
Verifies NVIDIA GeForce RTX 2080 (Turing TU104, Compute Capability 7.5) support:
- FP16 Tensor Core precision routing
- Low-VRAM int8_float16 fallback
- Turing bfloat16 safety guard
- Windows CUDA DLL directory loader
- System telemetry and FFmpeg discovery
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


def test_turing_rtx_2080_hardware_detection_and_precision():
    """
    Simulates NVIDIA GeForce RTX 2080 (TU104, Compute Capability 7.5, 8GB VRAM)
    and verifies that the HAL configures native float16 Tensor Core precision.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)  # Turing CC 7.5
    
    mock_props = MagicMock()
    mock_props.total_memory = 8 * 1024 * 1024 * 1024  # 8 GB GDDR6
    mock_torch.cuda.get_device_properties.return_value = mock_props
    mock_torch.device.return_value = "cuda"

    # Clear LRU cache before testing
    get_compute_backend.cache_clear()

    with patch.dict(os.environ, {}, clear=True), patch("engine.hardware.torch", mock_torch):
        backend = get_compute_backend()
        assert backend["platform"] == "NVIDIA CUDA"
        assert backend["device_name"] == "NVIDIA GeForce RTX 2080"
        assert backend["whisper_device"] == "cuda"
        assert backend["compute_type"] == "float16"
        assert backend["supports_fp16"] is True
        assert backend["supports_bf16"] is False  # Turing lacks native bf16
        assert backend["cuda_compute_capability"] == "7.5"
        assert backend["vram_total_mb"] == 8192

    get_compute_backend.cache_clear()


def test_turing_low_vram_int8_fp16_routing():
    """
    Verifies that for GPUs with constrained VRAM (< 5.5GB),
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

    with patch.dict(os.environ, {}, clear=True), patch("engine.hardware.torch", mock_torch):
        backend = get_compute_backend()
        assert backend["compute_type"] == "int8_float16"
        assert backend["vram_total_mb"] == 4096

    get_compute_backend.cache_clear()


def test_turing_guards_against_unsupported_bfloat16():
    """
    Verifies that if TRANSCRIBER_COMPUTE_TYPE=bfloat16 is requested,
    the HAL protects Turing (CC 7.5) by falling back to float16.
    """
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)  # Turing
    mock_props = MagicMock()
    mock_props.total_memory = 8 * 1024 * 1024 * 1024
    mock_torch.cuda.get_device_properties.return_value = mock_props

    get_compute_backend.cache_clear()

    with patch.dict(os.environ, {"TRANSCRIBER_COMPUTE_TYPE": "bfloat16"}), patch("engine.hardware.torch", mock_torch):
        backend = get_compute_backend()
        # Must fall back to float16 because Turing lacks bfloat16 hardware
        assert backend["compute_type"] == "float16"

    get_compute_backend.cache_clear()


def test_user_override_compute_type():
    """Verifies manual override via TRANSCRIBER_COMPUTE_TYPE."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    mock_torch.cuda.get_device_name.return_value = "NVIDIA GeForce RTX 2080"
    mock_torch.cuda.get_device_capability.return_value = (7, 5)
    mock_props = MagicMock()
    mock_props.total_memory = 8 * 1024 * 1024 * 1024
    mock_torch.cuda.get_device_properties.return_value = mock_props

    get_compute_backend.cache_clear()

    with patch.dict(os.environ, {"TRANSCRIBER_COMPUTE_TYPE": "int8_float16"}), patch("engine.hardware.torch", mock_torch):
        backend = get_compute_backend()
        assert backend["compute_type"] == "int8_float16"

    get_compute_backend.cache_clear()


def test_telemetry_queries_mem_get_info():
    """Verifies telemetry correctly utilizes driver VRAM info."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    # 5GB free, 8GB total
    mock_torch.cuda.mem_get_info.return_value = (5 * 1024**3, 8 * 1024**3)
    mock_torch.cuda.memory_allocated.return_value = 1 * 1024**3
    mock_torch.cuda.memory_reserved.return_value = 2 * 1024**3

    with patch("engine.hardware.torch", mock_torch), patch("engine.hardware._TELEMETRY_CACHE", {}):
        telemetry = get_system_telemetry()
        assert telemetry["vram_total_mb"] == 8192
        assert telemetry["vram_free_mb"] == 5120
        assert telemetry["vram_allocated_mb"] == 1024
        assert telemetry["vram_reserved_mb"] == 2048


def test_ffmpeg_binary_find_does_not_crash():
    """Verifies find_ffmpeg_binary operates cleanly."""
    bin_path = find_ffmpeg_binary()
    assert bin_path is None or isinstance(bin_path, str)
