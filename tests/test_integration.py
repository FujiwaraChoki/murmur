"""Integration tests for Murmur."""

from __future__ import annotations

import json
import platform
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def mock_all_hardware(mock_sounddevice, mock_parakeet, mock_pyperclip, mock_keyboard_controller):
    """Mock all hardware-dependent modules."""
    return {
        "sounddevice": mock_sounddevice,
        "parakeet": mock_parakeet,
        "pyperclip": mock_pyperclip,
        "keyboard": mock_keyboard_controller,
    }


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_recording_workflow(self, mock_all_hardware, sample_audio_1sec):
        """Press hotkey → record → release → transcribe."""
        from murmur.audio import AudioRecorder
        from murmur.transcribe import Transcriber

        # Setup
        recorder = AudioRecorder()
        transcriber = Transcriber()

        # Mock the transcription
        with patch.object(transcriber, "transcribe", return_value="Hello World"):
            # Simulate recording workflow
            recorder.start()
            assert recorder.is_recording is True

            # Simulate audio being recorded
            recorder._buffer.append(sample_audio_1sec)

            # Stop and get audio
            audio = recorder.stop()
            assert recorder.is_recording is False
            assert audio.size > 0

            # Transcribe
            result = transcriber.transcribe(audio)
            assert result == "Hello World"

    def test_settings_persistence(self, mock_config_path):
        """Change settings → restart → settings persist."""
        from murmur.settings import load_config, save_config

        # Save new settings
        new_config = {
            "hotkey": "ctrl+alt+r",
            "microphone_index": 2,
            "model": "custom-model",
        }
        save_config(new_config)

        # Simulate "restart" by loading config again
        loaded_config = load_config()

        assert loaded_config["hotkey"] == "ctrl+alt+r"
        assert loaded_config["microphone_index"] == 2
        assert loaded_config["model"] == "custom-model"

    def test_hotkey_change_takes_effect(self):
        """Changing hotkey in settings updates handler."""
        from pynput import keyboard

        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert keyboard.Key.space == handler._target_key

        # Change hotkey
        handler.set_hotkey("cmd+enter")
        assert handler._target_key == keyboard.Key.enter


class TestComponentIntegration:
    """Component integration tests."""

    def test_audio_to_transcriber(self, mock_parakeet, sample_audio_1sec):
        """Audio output compatible with transcriber input."""
        from murmur.audio import AudioRecorder
        from murmur.transcribe import Transcriber

        recorder = AudioRecorder()
        transcriber = Transcriber()

        # Record some audio
        recorder._recording = True
        recorder._buffer.append(sample_audio_1sec)
        recorder._recording = False

        with recorder._lock:
            audio = np.concatenate(recorder._buffer, axis=0)
            recorder._buffer = []

        # Audio should be compatible with transcriber
        assert audio.dtype == np.float32
        assert audio.ndim == 1

        # Transcriber should accept this audio without error
        with patch("murmur.transcribe.sf.write"):
            result = transcriber.transcribe(audio)
            assert isinstance(result, str)

    def test_config_loads_at_startup(self, mock_config_path):
        """App loads config from file on start."""
        from murmur.settings import CONFIG_FILE, load_config, save_config

        # Create a config file
        test_config = {"hotkey": "ctrl+shift+r"}
        save_config(test_config)

        # Verify file exists
        assert CONFIG_FILE.exists()

        # Load config (simulating startup)
        config = load_config()
        assert config["hotkey"] == "ctrl+shift+r"


class TestAudioTranscriberPipeline:
    """Tests for the complete audio to transcription pipeline."""

    def test_audio_format_compatibility(self, sample_audio_1sec):
        """Audio recorder output format matches transcriber expectations."""
        from murmur.audio import AudioRecorder

        recorder = AudioRecorder()

        # Verify default sample rate matches Parakeet expectations
        assert recorder.sample_rate == 16000

        # Audio should be float32
        assert sample_audio_1sec.dtype == np.float32

    def test_stereo_to_mono_conversion(self, sample_audio_2d, mock_sounddevice):
        """Stereo audio is properly converted to mono."""
        from murmur.audio import AudioRecorder

        recorder = AudioRecorder()
        recorder.start()
        recorder._buffer.append(sample_audio_2d)
        audio = recorder.stop()

        # Should be flattened to 1D
        assert audio.ndim == 1

    def test_empty_recording_handling(self, mock_sounddevice):
        """Empty recording returns empty array, not error."""
        from murmur.audio import AudioRecorder
        from murmur.transcribe import Transcriber

        recorder = AudioRecorder()
        recorder.start()
        audio = recorder.stop()  # Stop immediately with no audio

        assert audio.size == 0

        transcriber = Transcriber()
        result = transcriber.transcribe(audio)
        assert result == ""


@pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
class TestMacOSIntegration:
    """macOS-specific integration tests."""

    def test_hotkey_listener_can_start(self):
        """Hotkey listener can be started on macOS."""
        from pynput import keyboard

        from murmur.hotkey import HotkeyHandler

        # Mock the Listener to avoid macOS permission issues in CI
        mock_listener = MagicMock()
        with patch.object(keyboard, "Listener", return_value=mock_listener):
            handler = HotkeyHandler(hotkey="cmd+shift+space")
            handler.start()
            assert handler._listener is not None
            handler.stop()
            assert handler._listener is None
