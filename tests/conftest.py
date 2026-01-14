"""Shared fixtures for Murmur tests."""

from __future__ import annotations

import platform
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest


@pytest.fixture
def sample_audio_1sec():
    """Generate 1 second of sample audio at 16kHz."""
    return np.random.randn(16000).astype(np.float32)


@pytest.fixture
def sample_audio_5sec():
    """Generate 5 seconds of sample audio at 16kHz."""
    return np.random.randn(80000).astype(np.float32)


@pytest.fixture
def sample_audio_2d():
    """Generate 2D stereo sample audio (16000 samples, 2 channels)."""
    return np.random.randn(16000, 2).astype(np.float32)


@pytest.fixture
def mock_sounddevice(monkeypatch):
    """Mock sounddevice module for testing without hardware."""
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {
            "name": "Built-in Microphone",
            "max_input_channels": 2,
            "max_output_channels": 0,
            "default_samplerate": 44100.0,
        },
        {
            "name": "External USB Mic",
            "max_input_channels": 1,
            "max_output_channels": 0,
            "default_samplerate": 48000.0,
        },
        {
            "name": "Built-in Output",
            "max_input_channels": 0,
            "max_output_channels": 2,
            "default_samplerate": 44100.0,
        },
    ]
    mock_sd.default.device = (0, 1)

    # Mock InputStream
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream

    monkeypatch.setattr("murmur.audio.sd", mock_sd)
    return mock_sd


@pytest.fixture
def mock_quartz(monkeypatch):
    """Mock Quartz module for keyboard event simulation."""
    mock_event = MagicMock()
    mocks = {
        "CGEventCreateKeyboardEvent": MagicMock(return_value=mock_event),
        "CGEventSetFlags": MagicMock(),
        "CGEventPost": MagicMock(),
        "CGEventSourceCreate": MagicMock(),
        "CGEventKeyboardSetUnicodeString": MagicMock(),
        "kCGHIDEventTap": 0,
        "kCGEventSourceStateHIDSystemState": 0,
        "kCGEventFlagMaskCommand": 1 << 20,
    }

    for name, mock in mocks.items():
        monkeypatch.setattr(f"murmur.paste.Quartz.{name}", mock)

    return mocks


@pytest.fixture
def mock_pyperclip(monkeypatch):
    """Mock pyperclip module."""
    mock_clipboard = {"content": ""}

    def mock_copy(text):
        mock_clipboard["content"] = text

    def mock_paste():
        return mock_clipboard["content"]

    monkeypatch.setattr("murmur.paste.pyperclip.copy", mock_copy)
    monkeypatch.setattr("murmur.paste.pyperclip.paste", mock_paste)
    return mock_clipboard


@pytest.fixture
def mock_parakeet(monkeypatch):
    """Mock parakeet_mlx module."""
    mock_model = MagicMock()
    mock_model.preprocessor_config.sample_rate = 16000
    mock_result = MagicMock()
    mock_result.text = " Hello World "
    mock_model.transcribe.return_value = mock_result

    def mock_from_pretrained(model_name):
        return mock_model

    monkeypatch.setattr("parakeet_mlx.from_pretrained", mock_from_pretrained)
    return mock_model


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".config" / "murmur"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def mock_config_path(temp_config_dir, monkeypatch):
    """Redirect CONFIG_DIR and CONFIG_FILE to temp."""
    monkeypatch.setattr("murmur.settings.CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr("murmur.settings.CONFIG_FILE", temp_config_dir / "config.json")
    return temp_config_dir


@pytest.fixture
def mock_macos_apis():
    """Mock macOS-specific APIs for CI testing on non-macOS."""
    with patch.dict(
        "sys.modules",
        {
            "AppKit": MagicMock(),
            "Quartz": MagicMock(),
            "Foundation": MagicMock(),
            "objc": MagicMock(),
        },
    ):
        yield


@pytest.fixture(scope="session")
def is_macos():
    """Check if running on macOS."""
    return platform.system() == "Darwin"
