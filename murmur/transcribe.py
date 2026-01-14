"""Transcription module using Parakeet-MLX."""

from __future__ import annotations

import tempfile
import os

import numpy as np
import soundfile as sf
from numpy.typing import NDArray


class Transcriber:
    """Speech-to-text transcriber using Parakeet-MLX."""

    def __init__(self, model_name: str = "mlx-community/parakeet-tdt-0.6b-v2"):
        """Initialize the transcriber.

        Args:
            model_name: HuggingFace model name for parakeet-mlx.
        """
        self.model_name = model_name
        self._model = None

    def load_model(self) -> None:
        """Load the Parakeet model. Call this before transcribing."""
        if self._model is None:
            from parakeet_mlx import from_pretrained

            self._model = from_pretrained(self.model_name)

    @property
    def model(self):
        """Get the loaded model, loading it if necessary."""
        if self._model is None:
            self.load_model()
        return self._model

    @property
    def sample_rate(self) -> int:
        """Get the expected sample rate for audio input."""
        return self.model.preprocessor_config.sample_rate

    def transcribe(self, audio: NDArray[np.float32]) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio data as float32 numpy array, mono, at model's sample rate.

        Returns:
            Transcribed text string.
        """
        if audio.size == 0:
            return ""

        # Ensure audio is 1D
        if audio.ndim > 1:
            audio = audio.flatten()

        # Normalize if needed (parakeet expects float32 in [-1, 1])
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val

        # Save audio to a temporary file (parakeet-mlx expects a file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Write audio to temp file
            sf.write(temp_path, audio, self.sample_rate)

            # Transcribe from file
            result = self.model.transcribe(temp_path)
            return result.text.strip()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# Global transcriber instance for convenience
_transcriber: Transcriber | None = None


def get_transcriber(model_name: str = "mlx-community/parakeet-tdt-0.6b-v2") -> Transcriber:
    """Get or create the global transcriber instance.

    Args:
        model_name: HuggingFace model name for parakeet-mlx.

    Returns:
        Transcriber instance.
    """
    global _transcriber
    if _transcriber is None or _transcriber.model_name != model_name:
        _transcriber = Transcriber(model_name)
    return _transcriber
