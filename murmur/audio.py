"""Audio recording module using sounddevice."""

from __future__ import annotations

import threading
from typing import Callable

import numpy as np
import sounddevice as sd
from numpy.typing import NDArray


class AudioRecorder:
    """Records audio from the microphone."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize the audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Parakeet).
            channels: Number of audio channels (default 1 for mono).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._buffer: list[NDArray[np.float32]] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False

    def _audio_callback(
        self,
        indata: NDArray[np.float32],
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream."""
        if status:
            print(f"Audio status: {status}")
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())

    def start(self) -> None:
        """Start recording audio."""
        if self._recording:
            return

        with self._lock:
            self._buffer = []
            self._recording = True

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> NDArray[np.float32]:
        """Stop recording and return the recorded audio.

        Returns:
            Recorded audio as a float32 numpy array.
        """
        if not self._recording:
            return np.array([], dtype=np.float32)

        with self._lock:
            self._recording = False

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []

        # Flatten to 1D if needed
        if audio.ndim > 1:
            audio = audio.flatten()

        return audio

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording


def list_audio_devices() -> list[dict]:
    """List available audio input devices.

    Returns:
        List of device info dictionaries.
    """
    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            input_devices.append(
                {
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                }
            )
    return input_devices


def get_default_input_device() -> dict | None:
    """Get the default input device info.

    Returns:
        Device info dictionary or None if no input device found.
    """
    try:
        idx = sd.default.device[0]
        if idx is None:
            return None
        dev = sd.query_devices(idx)
        return {
            "index": idx,
            "name": dev["name"],
            "channels": dev["max_input_channels"],
            "sample_rate": dev["default_samplerate"],
        }
    except Exception:
        return None
