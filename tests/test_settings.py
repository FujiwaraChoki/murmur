"""Tests for the settings module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestConfigurationIO:
    """Tests for configuration I/O."""

    def test_load_config_default_when_missing(self, mock_config_path):
        """Returns DEFAULT_CONFIG when file missing."""
        from murmur.settings import DEFAULT_CONFIG, load_config

        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_load_config_reads_file(self, mock_config_path):
        """Reads and parses JSON file."""
        from murmur.settings import CONFIG_FILE, load_config

        test_config = {"hotkey": "ctrl+alt+r", "microphone_index": 1}
        CONFIG_FILE.write_text(json.dumps(test_config))

        config = load_config()
        assert config["hotkey"] == "ctrl+alt+r"
        assert config["microphone_index"] == 1

    def test_load_config_merges_with_defaults(self, mock_config_path):
        """Missing keys filled from defaults."""
        from murmur.settings import CONFIG_FILE, DEFAULT_CONFIG, load_config

        # Only save partial config
        test_config = {"hotkey": "ctrl+alt+r"}
        CONFIG_FILE.write_text(json.dumps(test_config))

        config = load_config()
        assert config["hotkey"] == "ctrl+alt+r"
        # Should have default values for missing keys
        assert config["microphone_index"] == DEFAULT_CONFIG["microphone_index"]
        assert config["model"] == DEFAULT_CONFIG["model"]

    def test_load_config_handles_invalid_json(self, mock_config_path):
        """Returns defaults on parse error."""
        from murmur.settings import CONFIG_FILE, DEFAULT_CONFIG, load_config

        CONFIG_FILE.write_text("not valid json {{{")

        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_save_config_creates_directory(self, tmp_path, monkeypatch):
        """Creates ~/.config/murmur if needed."""
        from murmur import settings

        config_dir = tmp_path / "new_dir" / "murmur"
        config_file = config_dir / "config.json"

        monkeypatch.setattr(settings, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(settings, "CONFIG_FILE", config_file)

        settings.save_config({"hotkey": "cmd+space"})

        assert config_dir.exists()
        assert config_file.exists()

    def test_save_config_writes_json(self, mock_config_path):
        """Writes valid JSON to file."""
        from murmur.settings import CONFIG_FILE, save_config

        test_config = {"hotkey": "ctrl+alt+r", "microphone_index": 2}
        save_config(test_config)

        # Read and parse to verify valid JSON
        saved = json.loads(CONFIG_FILE.read_text())
        assert saved["hotkey"] == "ctrl+alt+r"
        assert saved["microphone_index"] == 2

    def test_save_config_overwrites_existing(self, mock_config_path):
        """Overwrites existing config file."""
        from murmur.settings import CONFIG_FILE, save_config

        # Save initial config
        save_config({"hotkey": "cmd+a"})
        assert json.loads(CONFIG_FILE.read_text())["hotkey"] == "cmd+a"

        # Overwrite with new config
        save_config({"hotkey": "cmd+b"})
        assert json.loads(CONFIG_FILE.read_text())["hotkey"] == "cmd+b"

    def test_config_roundtrip(self, mock_config_path):
        """save then load returns same data."""
        from murmur.settings import load_config, save_config

        test_config = {
            "hotkey": "ctrl+shift+r",
            "microphone_index": 3,
            "model": "custom-model",
        }
        save_config(test_config)

        loaded = load_config()
        assert loaded["hotkey"] == test_config["hotkey"]
        assert loaded["microphone_index"] == test_config["microphone_index"]
        assert loaded["model"] == test_config["model"]


class TestDefaultConfiguration:
    """Tests for default configuration."""

    def test_default_config_has_hotkey(self):
        """DEFAULT_CONFIG contains hotkey."""
        from murmur.settings import DEFAULT_CONFIG

        assert "hotkey" in DEFAULT_CONFIG

    def test_default_config_has_microphone_index(self):
        """DEFAULT_CONFIG contains microphone_index."""
        from murmur.settings import DEFAULT_CONFIG

        assert "microphone_index" in DEFAULT_CONFIG

    def test_default_config_has_model(self):
        """DEFAULT_CONFIG contains model."""
        from murmur.settings import DEFAULT_CONFIG

        assert "model" in DEFAULT_CONFIG

    def test_default_hotkey_value(self):
        """Default hotkey is 'alt+shift'."""
        from murmur.settings import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["hotkey"] == "alt+shift"

    def test_default_microphone_is_none(self):
        """Default microphone_index is None."""
        from murmur.settings import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["microphone_index"] is None
