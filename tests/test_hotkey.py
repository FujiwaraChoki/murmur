"""Tests for the hotkey module."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from pynput import keyboard


class TestHotkeyParsing:
    """Tests for hotkey parsing."""

    def test_parse_cmd_shift_space(self):
        """Parses 'cmd+shift+space' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert keyboard.Key.cmd in handler._target_modifiers
        assert keyboard.Key.shift in handler._target_modifiers
        assert handler._target_key == keyboard.Key.space

    def test_parse_ctrl_alt_r(self):
        """Parses 'ctrl+alt+r' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="ctrl+alt+r")
        assert keyboard.Key.ctrl in handler._target_modifiers
        assert keyboard.Key.alt in handler._target_modifiers
        # Single char key becomes KeyCode
        assert isinstance(handler._target_key, keyboard.KeyCode)

    def test_parse_single_modifier_key(self):
        """Parses 'cmd+d' correctly."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+d")
        assert keyboard.Key.cmd in handler._target_modifiers
        assert len(handler._target_modifiers) == 1

    def test_parse_case_insensitive(self):
        """'CMD+SHIFT+SPACE' works same as lowercase."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="CMD+SHIFT+SPACE")
        assert keyboard.Key.cmd in handler._target_modifiers
        assert keyboard.Key.shift in handler._target_modifiers
        assert handler._target_key == keyboard.Key.space

    def test_parse_command_alias(self):
        """'command' maps to cmd."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="command+space")
        assert keyboard.Key.cmd in handler._target_modifiers

    def test_parse_option_alias(self):
        """'option' maps to alt."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="option+space")
        assert keyboard.Key.alt in handler._target_modifiers

    def test_parse_control_alias(self):
        """'control' maps to ctrl."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="control+space")
        assert keyboard.Key.ctrl in handler._target_modifiers

    def test_parse_special_keys_space(self):
        """'space' maps to Key.space."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+space")
        assert handler._target_key == keyboard.Key.space

    def test_parse_special_keys_enter(self):
        """'enter' and 'return' map to Key.enter."""
        from murmur.hotkey import HotkeyHandler

        handler1 = HotkeyHandler(hotkey="cmd+enter")
        handler2 = HotkeyHandler(hotkey="cmd+return")
        assert handler1._target_key == keyboard.Key.enter
        assert handler2._target_key == keyboard.Key.enter

    def test_parse_special_keys_tab(self):
        """'tab' maps to Key.tab."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+tab")
        assert handler._target_key == keyboard.Key.tab

    def test_parse_special_keys_escape(self):
        """'escape' and 'esc' map to Key.esc."""
        from murmur.hotkey import HotkeyHandler

        handler1 = HotkeyHandler(hotkey="cmd+escape")
        handler2 = HotkeyHandler(hotkey="cmd+esc")
        assert handler1._target_key == keyboard.Key.esc
        assert handler2._target_key == keyboard.Key.esc

    def test_parse_single_char_key(self):
        """Single characters become KeyCode."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+a")
        assert isinstance(handler._target_key, keyboard.KeyCode)


class TestHotkeyDetection:
    """Tests for hotkey detection."""

    def test_is_hotkey_pressed_all_modifiers(self):
        """Returns True when all modifiers pressed."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._pressed_keys = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.space}
        assert handler._is_hotkey_pressed() is True

    def test_is_hotkey_pressed_missing_modifier(self):
        """Returns False when modifier missing."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._pressed_keys = {keyboard.Key.cmd, keyboard.Key.space}  # Missing shift
        assert handler._is_hotkey_pressed() is False

    def test_is_hotkey_pressed_with_key(self):
        """Returns True when modifiers + key pressed."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+d")
        key_d = keyboard.KeyCode.from_char("d")
        handler._pressed_keys = {keyboard.Key.cmd, key_d}
        handler._target_key = key_d
        assert handler._is_hotkey_pressed() is True

    def test_is_hotkey_pressed_missing_key(self):
        """Returns False when key missing."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._pressed_keys = {keyboard.Key.cmd, keyboard.Key.shift}  # Missing space
        assert handler._is_hotkey_pressed() is False

    def test_keycode_char_matching(self):
        """KeyCode comparison by char works."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+a")
        key_a = keyboard.KeyCode.from_char("a")
        handler._pressed_keys = {keyboard.Key.cmd, key_a}
        assert handler._is_hotkey_pressed() is True


class TestEventHandling:
    """Tests for event handling."""

    def test_on_press_adds_to_pressed_keys(self):
        """Press event adds key to set."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._on_press(keyboard.Key.cmd)
        assert keyboard.Key.cmd in handler._pressed_keys

    def test_on_release_removes_from_pressed_keys(self):
        """Release event removes key from set."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        handler._pressed_keys = {keyboard.Key.cmd, keyboard.Key.shift}
        handler._on_release(keyboard.Key.cmd)
        assert keyboard.Key.cmd not in handler._pressed_keys

    def test_on_press_triggers_callback(self):
        """First hotkey press calls on_press_start."""
        from murmur.hotkey import HotkeyHandler

        callback_called = {"value": False}

        def callback():
            callback_called["value"] = True

        handler = HotkeyHandler(
            hotkey="cmd+shift+space",
            on_press_start=callback,
        )
        # Simulate pressing all keys
        handler._on_press(keyboard.Key.cmd)
        handler._on_press(keyboard.Key.shift)
        handler._on_press(keyboard.Key.space)
        # Give thread time to execute
        time.sleep(0.1)
        assert callback_called["value"] is True

    def test_on_press_callback_only_once(self):
        """Holding hotkey doesn't repeat callback."""
        from murmur.hotkey import HotkeyHandler

        call_count = {"value": 0}

        def callback():
            call_count["value"] += 1

        handler = HotkeyHandler(
            hotkey="cmd+shift+space",
            on_press_start=callback,
        )
        # Simulate pressing all keys multiple times
        handler._on_press(keyboard.Key.cmd)
        handler._on_press(keyboard.Key.shift)
        handler._on_press(keyboard.Key.space)
        handler._on_press(keyboard.Key.space)  # Repeat
        time.sleep(0.1)
        assert call_count["value"] == 1

    def test_on_release_triggers_callback(self):
        """Releasing hotkey calls on_release_end."""
        from murmur.hotkey import HotkeyHandler

        callback_called = {"value": False}

        def callback():
            callback_called["value"] = True

        handler = HotkeyHandler(
            hotkey="cmd+shift+space",
            on_release_end=callback,
        )
        # Simulate pressing and then releasing
        handler._pressed_keys = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.Key.space}
        handler._is_hotkey_held = True
        handler._on_release(keyboard.Key.space)
        time.sleep(0.1)
        assert callback_called["value"] is True

    def test_callbacks_run_in_thread(self):
        """Callbacks don't block event handling."""
        from murmur.hotkey import HotkeyHandler

        slow_callback_started = {"value": False}
        slow_callback_finished = {"value": False}

        def slow_callback():
            slow_callback_started["value"] = True
            time.sleep(0.5)
            slow_callback_finished["value"] = True

        handler = HotkeyHandler(
            hotkey="cmd+shift+space",
            on_press_start=slow_callback,
        )
        # Simulate pressing hotkey
        start_time = time.time()
        handler._on_press(keyboard.Key.cmd)
        handler._on_press(keyboard.Key.shift)
        handler._on_press(keyboard.Key.space)
        elapsed = time.time() - start_time
        # _on_press should return quickly (< 0.1s) because callback runs in thread
        assert elapsed < 0.2
        time.sleep(0.1)
        assert slow_callback_started["value"] is True


class TestLifecycle:
    """Tests for lifecycle management."""

    def test_start_creates_listener(self):
        """start() creates keyboard.Listener."""
        from murmur.hotkey import HotkeyHandler

        # Mock the Listener to avoid macOS API issues
        mock_listener = MagicMock()
        with patch.object(keyboard, "Listener", return_value=mock_listener):
            handler = HotkeyHandler(hotkey="cmd+shift+space")
            assert handler._listener is None
            handler.start()
            assert handler._listener is not None
            handler.stop()

    def test_start_idempotent(self):
        """Multiple start() calls don't crash."""
        from murmur.hotkey import HotkeyHandler

        # Mock the Listener to avoid macOS API issues
        mock_listener = MagicMock()
        with patch.object(keyboard, "Listener", return_value=mock_listener):
            handler = HotkeyHandler(hotkey="cmd+shift+space")
            handler.start()
            listener1 = handler._listener
            handler.start()  # Second call
            listener2 = handler._listener
            assert listener1 is listener2
            handler.stop()

    def test_stop_cleans_up_listener(self):
        """stop() sets listener to None."""
        from murmur.hotkey import HotkeyHandler

        # Mock the Listener to avoid macOS API issues
        mock_listener = MagicMock()
        with patch.object(keyboard, "Listener", return_value=mock_listener):
            handler = HotkeyHandler(hotkey="cmd+shift+space")
            handler.start()
            handler.stop()
            assert handler._listener is None

    def test_set_hotkey_updates_parsing(self):
        """set_hotkey() re-parses hotkey string."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert keyboard.Key.space == handler._target_key
        handler.set_hotkey("cmd+enter")
        assert handler._target_key == keyboard.Key.enter

    def test_is_held_property(self):
        """is_held reflects current state."""
        from murmur.hotkey import HotkeyHandler

        handler = HotkeyHandler(hotkey="cmd+shift+space")
        assert handler.is_held is False
        handler._is_hotkey_held = True
        assert handler.is_held is True
