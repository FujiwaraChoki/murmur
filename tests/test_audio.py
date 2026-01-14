"""Tests for the audio module."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import sounddevice as sd
from murmur.audio import AudioRecorder, get_default_input_device, list_audio_devices


class TestAudioRecorder:
    """Tests for AudioRecorder class."""

    def test_init_default_params(self):
        """Verify default sample_rate=16000, channels=1."""
        recorder = AudioRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1

    def test_init_custom_params(self):
        """Verify custom sample_rate and channels are set."""
        recorder = AudioRecorder(sample_rate=44100, channels=2)
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2

    def test_start_begins_recording(self, mock_sounddevice):
        """start() sets is_recording=True."""
        recorder = AudioRecorder()
        assert recorder.is_recording is False
        recorder.start()
        assert recorder.is_recording is True

    def test_start_idempotent(self, mock_sounddevice):
        """Multiple start() calls don't crash."""
        recorder = AudioRecorder()
        recorder.start()
        recorder.start()  # Second call should be no-op
        assert recorder.is_recording is True
        # InputStream should only be created once
        assert mock_sounddevice.InputStream.call_count == 1

    def test_stop_returns_array(self, mock_sounddevice, sample_audio_1sec):
        """stop() returns numpy float32 array."""
        recorder = AudioRecorder()
        recorder.start()
        # Simulate callback adding data
        recorder._buffer.append(sample_audio_1sec)
        result = recorder.stop()
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_stop_when_not_recording(self):
        """stop() returns empty array when not recording."""
        recorder = AudioRecorder()
        result = recorder.stop()
        assert isinstance(result, np.ndarray)
        assert result.size == 0

    def test_stop_clears_buffer(self, mock_sounddevice, sample_audio_1sec):
        """Buffer is cleared after stop()."""
        recorder = AudioRecorder()
        recorder.start()
        recorder._buffer.append(sample_audio_1sec)
        recorder.stop()
        assert len(recorder._buffer) == 0

    def test_recording_flag_thread_safe(self, mock_sounddevice):
        """is_recording protected by lock."""
        recorder = AudioRecorder()
        assert hasattr(recorder, "_lock")
        assert isinstance(recorder._lock, type(threading.Lock()))

    def test_audio_callback_appends_buffer(self):
        """Callback adds data to buffer when recording."""
        recorder = AudioRecorder()
        recorder._recording = True
        test_data = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        recorder._audio_callback(test_data, 3, {}, None)
        assert len(recorder._buffer) == 1
        np.testing.assert_array_equal(recorder._buffer[0], test_data)

    def test_audio_callback_ignores_when_stopped(self):
        """Callback ignores data when not recording."""
        recorder = AudioRecorder()
        recorder._recording = False
        test_data = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        recorder._audio_callback(test_data, 3, {}, None)
        assert len(recorder._buffer) == 0

    def test_recorded_audio_is_1d(self, mock_sounddevice):
        """Output array is flattened to 1D."""
        recorder = AudioRecorder()
        recorder.start()
        # Add 2D stereo-like data
        recorder._buffer.append(np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32))
        result = recorder.stop()
        assert result.ndim == 1


class TestListAudioDevices:
    """Tests for list_audio_devices function."""

    def test_list_audio_devices_returns_list(self, mock_sounddevice):
        """Returns list of device dicts."""
        devices = list_audio_devices()
        assert isinstance(devices, list)
        assert len(devices) > 0

    def test_list_audio_devices_dict_structure(self, mock_sounddevice):
        """Each dict has index, name, channels, sample_rate."""
        devices = list_audio_devices()
        for dev in devices:
            assert "index" in dev
            assert "name" in dev
            assert "channels" in dev
            assert "sample_rate" in dev

    def test_list_audio_devices_only_inputs(self, mock_sounddevice):
        """Only returns input devices (max_input_channels > 0)."""
        devices = list_audio_devices()
        # Mock has 2 input devices and 1 output-only device
        assert len(devices) == 2
        for dev in devices:
            assert dev["channels"] > 0


class TestGetDefaultInputDevice:
    """Tests for get_default_input_device function."""

    def test_get_default_input_device_returns_dict(self, mock_sounddevice):
        """Returns dict with device info."""
        mock_sounddevice.query_devices.side_effect = None
        mock_sounddevice.query_devices.return_value = {
            "name": "Built-in Microphone",
            "max_input_channels": 2,
            "default_samplerate": 44100.0,
        }
        device = get_default_input_device()
        assert isinstance(device, dict)
        assert "index" in device
        assert "name" in device
        assert "channels" in device
        assert "sample_rate" in device

    def test_get_default_input_device_none_when_unavailable(self, mock_sounddevice):
        """Returns None when no device."""
        mock_sounddevice.default.device = (None, 1)
        device = get_default_input_device()
        assert device is None

    def test_get_default_input_device_handles_exception(self, mock_sounddevice):
        """Returns None when exception occurs."""
        mock_sounddevice.query_devices.side_effect = Exception("No device")
        device = get_default_input_device()
        assert device is None
