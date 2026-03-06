"""Audio recording module using sounddevice."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd
from numpy.typing import NDArray

logger = logging.getLogger("murmur.audio")


class AudioRecorder:
    """Records audio from the microphone."""

    waveform_bins = 29

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize the audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Parakeet).
            channels: Number of audio channels (default 1 for mono).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_waveform_update: Callable[[list[float]], None] | None = None
        self._buffer: list[NDArray[np.float32]] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False
        self._waveform_levels = np.full(self.waveform_bins, 0.06, dtype=np.float32)

    def _audio_callback(
        self,
        indata: NDArray[np.float32],
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream."""
        if status:
            logger.warning("Audio stream status: %s", status)
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())
        if self._recording and self.on_waveform_update is not None:
            self.on_waveform_update(self._analyze_waveform(indata))

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            if self._recording:
                return
            self._buffer = []
            self._recording = True
            self._waveform_levels = np.full(self.waveform_bins, 0.06, dtype=np.float32)

        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            stream.start()
            self._stream = stream
        except Exception:
            # Keep internal state consistent if stream startup fails.
            with self._lock:
                self._recording = False
                self._buffer = []
            self._stream = None
            raise

    def stop(self) -> NDArray[np.float32]:
        """Stop recording and return the recorded audio.

        Returns:
            Recorded audio as a float32 numpy array.
        """
        with self._lock:
            was_recording = self._recording
            self._recording = False
            self._waveform_levels = np.full(self.waveform_bins, 0.06, dtype=np.float32)
            stream = self._stream
            self._stream = None

        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()

        if not was_recording:
            return np.array([], dtype=np.float32)

        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []

        # Flatten to 1D if needed
        if audio.ndim > 1:
            audio = audio.flatten()

        return audio

    def _analyze_waveform(self, indata: NDArray[np.float32]) -> list[float]:
        """Convert the latest audio chunk into smoothed waveform levels."""
        samples = np.asarray(indata, dtype=np.float32)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        else:
            samples = samples.reshape(-1)

        if samples.size == 0:
            return self._waveform_levels.astype(float).tolist()

        segments = np.array_split(np.abs(samples), self.waveform_bins)
        segment_rms = np.array(
            [float(np.sqrt(np.mean(segment**2))) if segment.size else 0.0 for segment in segments],
            dtype=np.float32,
        )
        overall_rms = float(np.sqrt(np.mean(samples**2))) if samples.size else 0.0

        # Lift quiet speech and keep the waveform lively without clipping hard peaks.
        boosted = np.sqrt(segment_rms * 5.5)
        boosted += min(overall_rms * 1.4, 0.22)
        boosted = np.clip(boosted, 0.04, 1.0)

        with self._lock:
            rising = boosted > self._waveform_levels
            smoothing = np.where(rising, 0.6, 0.22).astype(np.float32)
            self._waveform_levels = (
                self._waveform_levels * (1 - smoothing)
            ) + (boosted * smoothing)
            levels = np.clip(self._waveform_levels, 0.04, 1.0)

        return levels.astype(float).tolist()

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
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
