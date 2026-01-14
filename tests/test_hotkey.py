"""Tests for the hotkey module."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestHotkeyParsing:
    """Tests for hotkey parsing."""

    def test_parse_cmd_shift_space(self):
        """Parses 'cmd+shift+space' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        # Check that modifiers are set (using Quartz flags)
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskCommand
        assert handler._target_modifiers & Quartz.kCGEventFlagMaskShift
        assert handler._target_keycode == 49  # space keycode

    def test_parse_ctrl_alt_r(self):
        """Parses 'ctrl+alt+r' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="ctrl+alt+r")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskControl
        assert handler._target_modifiers & Quartz.kCGEventFlagMaskAlternate
        assert handler._target_keycode == 15  # 'r' keycode

    def test_parse_single_modifier_key(self):
        """Parses 'cmd+d' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+d")
        import Quartz

        assert handler._target_modifiers == Quartz.kCGEventFlagMaskCommand
        assert handler._target_keycode == 2  # 'd' keycode

    def test_parse_case_insensitive(self):
        """'CMD+SHIFT+SPACE' works same as lowercase."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="CMD+SHIFT+SPACE")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskCommand
        assert handler._target_modifiers & Quartz.kCGEventFlagMaskShift
        assert handler._target_keycode == 49

    def test_parse_command_alias(self):
        """'command' maps to cmd."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="command+space")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskCommand

    def test_parse_option_alias(self):
        """'option' maps to alt."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="option+space")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskAlternate

    def test_parse_control_alias(self):
        """'control' maps to ctrl."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="control+space")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskControl

    def test_parse_special_keys_space(self):
        """'space' maps to keycode 49."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+space")
        assert handler._target_keycode == 49

    def test_parse_special_keys_enter(self):
        """'enter' and 'return' map to keycode 36."""
        from murmur.hotkey import HotkeyHandler

        handler1 = HotkeyHandler(hotkey="cmd+enter")
        handler2 = HotkeyHandler(hotkey="cmd+return")
        assert handler1._target_keycode == 36
        assert handler2._target_keycode == 36

    def test_parse_special_keys_tab(self):
        """'tab' maps to keycode 48."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+tab")
        assert handler._target_keycode == 48

    def test_parse_special_keys_escape(self):
        """'escape' and 'esc' map to keycode 53."""
        from murmur.hotkey import HotkeyHandler

        handler1 = HotkeyHandler(hotkey="cmd+escape")
        handler2 = HotkeyHandler(hotkey="cmd+esc")
        assert handler1._target_keycode == 53
        assert handler2._target_keycode == 53

    def test_parse_letter_keys(self):
        """Letter keys map to correct keycodes."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+a")
        assert handler._target_keycode == 0  # 'a' keycode

    def test_parse_modifier_only_hotkey(self):
        """Modifier-only hotkey (alt+shift) has no keycode."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="alt+shift")
        import Quartz

        assert handler._target_modifiers & Quartz.kCGEventFlagMaskAlternate
        assert handler._target_modifiers & Quartz.kCGEventFlagMaskShift
        assert handler._target_keycode is None


class TestHotkeyValidation:
    """Tests for hotkey validation."""

    def test_validate_valid_hotkey(self):
        """Valid hotkey returns True."""
        from murmur.hotkey import HotkeyHandler

        is_valid, error = HotkeyHandler.validate_hotkey("cmd+shift+space")
        assert is_valid is True
        assert error == ""

    def test_validate_empty_hotkey(self):
        """Empty hotkey returns False."""
        from murmur.hotkey import HotkeyHandler

        is_valid, error = HotkeyHandler.validate_hotkey("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_no_modifier(self):
        """Hotkey without modifier returns False."""
        from murmur.hotkey import HotkeyHandler

        is_valid, error = HotkeyHandler.validate_hotkey("space")
        assert is_valid is False
        assert "modifier" in error.lower()

    def test_validate_unknown_key(self):
        """Unknown key returns False."""
        from murmur.hotkey import HotkeyHandler

        is_valid, error = HotkeyHandler.validate_hotkey("cmd+unknownkey")
        assert is_valid is False
        assert "unknown" in error.lower()

    def test_validate_modifier_only_needs_two(self):
        """Modifier-only hotkey needs at least 2 modifiers."""
        from murmur.hotkey import HotkeyHandler

        # Single modifier should fail
        is_valid, error = HotkeyHandler.validate_hotkey("cmd")
        assert is_valid is False
        assert "2 modifiers" in error.lower()

        # Two modifiers should work
        is_valid, error = HotkeyHandler.validate_hotkey("alt+shift")
        assert is_valid is True


class TestModifierChecking:
    """Tests for modifier flag checking."""

    def test_check_modifiers_exact(self):
        """Exact modifier match works."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="alt+shift")
        import Quartz

        # Exact match
        flags = Quartz.kCGEventFlagMaskAlternate | Quartz.kCGEventFlagMaskShift
        assert handler._check_modifiers_exact(flags) is True

        # Extra modifier - should fail
        flags = (
            Quartz.kCGEventFlagMaskAlternate
            | Quartz.kCGEventFlagMaskShift
            | Quartz.kCGEventFlagMaskCommand
        )
        assert handler._check_modifiers_exact(flags) is False

    def test_check_modifiers_subset(self):
        """Subset modifier check (for regular hotkeys) works."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        import Quartz

        # With extra modifiers - should still match
        flags = (
            Quartz.kCGEventFlagMaskCommand
            | Quartz.kCGEventFlagMaskShift
            | Quartz.kCGEventFlagMaskAlternate
        )
        assert handler._check_modifiers(flags) is True

        # Missing required modifier - should fail
        flags = Quartz.kCGEventFlagMaskCommand  # Missing shift
        assert handler._check_modifiers(flags) is False


class TestLifecycle:
    """Tests for lifecycle management."""

    def test_start_creates_tap(self):
        """start() creates event tap."""
        from murmur.hotkey import HotkeyHandler

        with patch("murmur.hotkey.Quartz") as mock_quartz:
            mock_quartz.CGEventTapCreate.return_value = MagicMock()
            mock_quartz.CFMachPortCreateRunLoopSource.return_value = MagicMock()
            mock_quartz.CFRunLoopGetCurrent.return_value = MagicMock()

            handler = HotkeyHandler(hotkey="cmd+shift+space")
            assert handler._tap is None
            handler.start()
            # Give thread time to start
            time.sleep(0.1)
            handler.stop()

    def test_stop_cleans_up(self):
        """stop() cleans up resources."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._running = True
        handler._tap = MagicMock()
        handler._tap_thread = MagicMock()

        with patch("murmur.hotkey.Quartz"):
            handler.stop()

        assert handler._running is False

    def test_set_hotkey_updates_parsing(self):
        """set_hotkey() re-parses hotkey string."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert handler._target_keycode == 49  # space
        handler.set_hotkey("cmd+enter")
        assert handler._target_keycode == 36  # enter

    def test_is_held_property(self):
        """is_held reflects current state."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert handler.is_held is False
        handler._is_hotkey_held = True
        assert handler.is_held is True


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_hotkey_raises(self):
        """Invalid hotkey string raises ValueError."""
        from murmur.hotkey import HotkeyHandler

        with pytest.raises(ValueError):
            HotkeyHandler(hotkey="")

        with pytest.raises(ValueError):
            HotkeyHandler(hotkey="unknownkey")

        with pytest.raises(ValueError):
            HotkeyHandler(hotkey="space")  # No modifier
