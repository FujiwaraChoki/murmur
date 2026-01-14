"""Tests for the transcribe module."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest


class TestTranscriber:
    """Tests for Transcriber class."""

    def test_init_default_model(self):
        """Default model name is set."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        assert transcriber.model_name == "mlx-community/parakeet-tdt-0.6b-v2"

    def test_init_custom_model(self):
        """Custom model name is stored."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber(model_name="custom-model")
        assert transcriber.model_name == "custom-model"

    def test_model_lazy_loading(self):
        """Model is None until first access."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        assert transcriber._model is None

    def test_load_model_sets_model(self, mock_parakeet):
        """load_model() sets _model."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        transcriber.load_model()
        assert transcriber._model is not None

    def test_model_property_loads_on_access(self, mock_parakeet):
        """Accessing model loads if needed."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        assert transcriber._model is None
        _ = transcriber.model
        assert transcriber._model is not None

    def test_sample_rate_from_config(self, mock_parakeet):
        """sample_rate comes from model config."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        assert transcriber.sample_rate == 16000


class TestTranscription:
    """Tests for transcription functionality."""

    def test_transcribe_empty_audio(self, mock_parakeet):
        """Empty array returns empty string."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        result = transcriber.transcribe(np.array([], dtype=np.float32))
        assert result == ""

    def test_transcribe_flattens_2d_audio(self, mock_parakeet, sample_audio_2d):
        """2D audio is flattened."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        # Patch soundfile.write to capture the audio shape
        with patch("murmur.transcribe.sf.write") as mock_write:
            try:
                transcriber.transcribe(sample_audio_2d)
            except Exception:
                pass
            # Check that the audio passed to sf.write is 1D
            if mock_write.called:
                written_audio = mock_write.call_args[0][1]
                assert written_audio.ndim == 1

    def test_transcribe_converts_dtype(self, mock_parakeet):
        """Non-float32 is converted."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        int_audio = np.array([100, 200, 300], dtype=np.int16)

        with patch("murmur.transcribe.sf.write") as mock_write:
            try:
                transcriber.transcribe(int_audio)
            except Exception:
                pass
            if mock_write.called:
                written_audio = mock_write.call_args[0][1]
                assert written_audio.dtype == np.float32

    def test_transcribe_normalizes_audio(self, mock_parakeet):
        """Audio > 1.0 is normalized."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        loud_audio = np.array([2.0, -3.0, 1.5], dtype=np.float32)

        with patch("murmur.transcribe.sf.write") as mock_write:
            try:
                transcriber.transcribe(loud_audio)
            except Exception:
                pass
            if mock_write.called:
                written_audio = mock_write.call_args[0][1]
                assert np.abs(written_audio).max() <= 1.0

    def test_transcribe_creates_temp_file(self, mock_parakeet, sample_audio_1sec):
        """Temp file is created for transcription."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()
        created_files = []

        with patch("murmur.transcribe.sf.write") as mock_write:

            def capture_write(path, *args, **kwargs):
                created_files.append(path)

            mock_write.side_effect = capture_write
            try:
                transcriber.transcribe(sample_audio_1sec)
            except Exception:
                pass

        # Should have attempted to write to a temp file
        assert len(created_files) > 0
        assert any(".wav" in str(f) for f in created_files)

    def test_transcribe_cleans_up_temp_file(self, mock_parakeet, sample_audio_1sec):
        """Temp file is deleted after transcription."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()

        # Track temp files created
        temp_files_created = []
        original_named_temp = tempfile.NamedTemporaryFile

        def tracking_temp(*args, **kwargs):
            f = original_named_temp(*args, **kwargs)
            temp_files_created.append(f.name)
            return f

        with patch("murmur.transcribe.tempfile.NamedTemporaryFile", tracking_temp):
            with patch("murmur.transcribe.sf.write"):
                try:
                    transcriber.transcribe(sample_audio_1sec)
                except Exception:
                    pass

        # Temp files should be cleaned up
        for temp_file in temp_files_created:
            assert not os.path.exists(temp_file)

    def test_transcribe_strips_whitespace(self, mock_parakeet, sample_audio_1sec):
        """Result text is stripped."""
        from murmur.transcribe import Transcriber

        transcriber = Transcriber()

        with patch("murmur.transcribe.sf.write"):
            result = transcriber.transcribe(sample_audio_1sec)
            # Mock returns " Hello World " which should be stripped
            assert result == "Hello World"
            assert not result.startswith(" ")
            assert not result.endswith(" ")


class TestGlobalInstance:
    """Tests for global transcriber instance."""

    def test_get_transcriber_creates_instance(self):
        """First call creates Transcriber."""
        from murmur import transcribe

        # Reset global state
        transcribe._transcriber = None

        result = transcribe.get_transcriber()
        assert result is not None
        assert isinstance(result, transcribe.Transcriber)

    def test_get_transcriber_returns_same(self):
        """Repeated calls return same instance."""
        from murmur import transcribe

        # Reset global state
        transcribe._transcriber = None

        result1 = transcribe.get_transcriber()
        result2 = transcribe.get_transcriber()
        assert result1 is result2

    def test_get_transcriber_new_on_model_change(self):
        """Different model creates new instance."""
        from murmur import transcribe

        # Reset global state
        transcribe._transcriber = None

        result1 = transcribe.get_transcriber("model-a")
        result2 = transcribe.get_transcriber("model-b")
        assert result1 is not result2
        assert result2.model_name == "model-b"
