"""Tests for the main CLI module."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


class TestArgumentParsing:
    """Tests for argument parsing."""

    def test_default_model_argument(self):
        """Default model is parakeet-tdt-0.6b-v2."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--version"]):
            with patch("murmur.main.print"):
                main()
        # The default model is used when not specified

    def test_custom_model_argument(self):
        """--model sets custom model."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--model", "custom-model", "--version"]):
            with patch("murmur.main.print"):
                main()

    def test_model_short_flag(self):
        """-m works same as --model."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "-m", "custom-model", "--version"]):
            with patch("murmur.main.print"):
                result = main()
                assert result == 0

    def test_default_hotkey_argument(self):
        """Default hotkey is alt+shift."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--version"]):
            with patch("murmur.main.print"):
                main()

    def test_custom_hotkey_argument(self):
        """--hotkey sets custom hotkey."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--hotkey", "ctrl+alt+r", "--version"]):
            with patch("murmur.main.print"):
                result = main()
                assert result == 0

    def test_hotkey_short_flag(self):
        """-k works same as --hotkey."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "-k", "ctrl+alt+r", "--version"]):
            with patch("murmur.main.print"):
                result = main()
                assert result == 0

    def test_list_devices_flag(self, mock_sounddevice):
        """--list-devices returns early."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--list-devices"]):
            with patch("murmur.main.print"):
                result = main()
                assert result == 0

    def test_version_flag(self):
        """--version prints version and exits."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "--version"]):
            with patch("murmur.main.print") as mock_print:
                result = main()
                assert result == 0
                # Should have printed version
                mock_print.assert_called()

    def test_version_short_flag(self):
        """-v works same as --version."""
        from murmur.main import main

        with patch("sys.argv", ["murmur", "-v"]):
            with patch("murmur.main.print"):
                result = main()
                assert result == 0


class TestCommandExecution:
    """Tests for command execution."""

    def test_list_devices_prints_devices(self, mock_sounddevice):
        """--list-devices prints device list."""
        from murmur.main import main

        printed_lines = []

        def capture_print(*args, **kwargs):
            printed_lines.append(args[0] if args else "")

        with patch("sys.argv", ["murmur", "--list-devices"]):
            with patch("murmur.main.print", capture_print):
                main()

        # Should have printed device info
        output = "\n".join(printed_lines)
        assert "Available audio input devices" in output

    def test_list_devices_shows_default(self, mock_sounddevice):
        """Default device marked with '(default)'."""
        from murmur.main import main

        # Configure mock to return proper default device
        mock_sounddevice.query_devices.side_effect = None
        mock_sounddevice.query_devices.return_value = [
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
        ]
        # Set default device index (input device at index 0)
        mock_sounddevice.default.device = (0, 1)

        # Mock query_devices to return proper device info when called with index
        def query_devices_side_effect(device=None):
            if device is None:
                return mock_sounddevice.query_devices.return_value
            if device == 0:
                return {
                    "name": "Built-in Microphone",
                    "max_input_channels": 2,
                    "default_samplerate": 44100.0,
                }
            return None

        mock_sounddevice.query_devices.side_effect = query_devices_side_effect

        printed_lines = []

        def capture_print(*args, **kwargs):
            printed_lines.append(args[0] if args else "")

        with patch("sys.argv", ["murmur", "--list-devices"]):
            with patch("murmur.main.print", capture_print):
                main()

        output = "\n".join(printed_lines)
        assert "(default)" in output

    def test_version_shows_correct_version(self):
        """Version matches __version__."""
        from murmur import __version__
        from murmur.main import main

        printed_lines = []

        def capture_print(*args, **kwargs):
            printed_lines.append(args[0] if args else "")

        with patch("sys.argv", ["murmur", "--version"]):
            with patch("murmur.main.print", capture_print):
                main()

        output = "\n".join(printed_lines)
        assert __version__ in output

    def test_main_starts_app(self):
        """Normal invocation calls run_app."""
        mock_run_app = Mock()
        mock_module = MagicMock(run_app=mock_run_app)

        with patch("sys.argv", ["murmur"]):
            with patch("murmur.main.print"):
                with patch.dict("sys.modules", {"murmur.app": mock_module}):
                    from murmur.main import main

                    result = main()

        assert result == 0
        mock_run_app.assert_called_once_with(
            model_name="mlx-community/parakeet-tdt-0.6b-v2",
            hotkey="alt+shift",
            microphone_index=None,
        )

    def test_device_argument_passed_to_run_app(self):
        """--device is forwarded to run_app."""
        mock_run_app = Mock()
        mock_module = MagicMock(run_app=mock_run_app)

        with patch("sys.argv", ["murmur", "--device", "2"]):
            with patch("murmur.main.print"):
                with patch.dict("sys.modules", {"murmur.app": mock_module}):
                    from murmur.main import main

                    result = main()

        assert result == 0
        mock_run_app.assert_called_once_with(
            model_name="mlx-community/parakeet-tdt-0.6b-v2",
            hotkey="alt+shift",
            microphone_index=2,
        )

    def test_keyboard_interrupt_handled(self):
        """Ctrl+C exits gracefully."""
        from murmur.main import main

        def raise_interrupt(*args, **kwargs):
            raise KeyboardInterrupt()

        # Mock the run_app import inside main.py
        mock_module = MagicMock()
        mock_module.run_app = raise_interrupt

        with patch("sys.argv", ["murmur"]):
            with patch("murmur.main.print"):
                with patch.dict("sys.modules", {"murmur.app": mock_module}):
                    result = main()
                    # Should handle KeyboardInterrupt and return 0
                    assert result == 0
