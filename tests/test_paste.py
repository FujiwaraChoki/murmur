"""Tests for the paste module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, Mock, call, patch

import pytest


class TestPasteText:
    """Tests for paste_text function."""

    def test_paste_empty_text_noop(self, mock_pyperclip, mock_keyboard_controller):
        """Empty string does nothing."""
        from murmur.paste import paste_text

        paste_text("")
        # Controller should not have been used
        mock_keyboard_controller.press.assert_not_called()

    def test_paste_copies_to_clipboard(self, mock_pyperclip, mock_keyboard_controller):
        """Text is copied to clipboard."""
        from murmur.paste import paste_text

        paste_text("Hello World", restore_clipboard=False)
        assert mock_pyperclip["content"] == "Hello World"

    def test_paste_simulates_cmd_v(self, mock_pyperclip, mock_keyboard_controller):
        """Cmd+V key sequence is sent."""
        from pynput.keyboard import Key

        from murmur.paste import paste_text

        paste_text("test", restore_clipboard=False)

        # Should press cmd, then v, then release both
        mock_keyboard_controller.press.assert_any_call(Key.cmd)
        mock_keyboard_controller.press.assert_any_call("v")
        mock_keyboard_controller.release.assert_any_call("v")
        mock_keyboard_controller.release.assert_any_call(Key.cmd)

    def test_paste_restores_clipboard(self, mock_pyperclip, mock_keyboard_controller):
        """Original clipboard restored when flag True."""
        from murmur.paste import paste_text

        # Set original clipboard content
        mock_pyperclip["content"] = "original content"

        with patch("murmur.paste.time.sleep"):  # Speed up test
            paste_text("new content", restore_clipboard=True)

        # Clipboard should be restored to original
        assert mock_pyperclip["content"] == "original content"

    def test_paste_no_restore_when_disabled(self, mock_pyperclip, mock_keyboard_controller):
        """Clipboard not restored when flag False."""
        from murmur.paste import paste_text

        mock_pyperclip["content"] = "original content"

        with patch("murmur.paste.time.sleep"):
            paste_text("new content", restore_clipboard=False)

        # Clipboard should have new content
        assert mock_pyperclip["content"] == "new content"

    def test_paste_handles_clipboard_error(self, mock_keyboard_controller, monkeypatch):
        """Gracefully handles clipboard errors."""
        from murmur.paste import paste_text

        # Make pyperclip.paste raise an exception
        def raise_error():
            raise Exception("Clipboard error")

        monkeypatch.setattr("murmur.paste.pyperclip.paste", raise_error)
        monkeypatch.setattr("murmur.paste.pyperclip.copy", lambda x: None)

        # Should not raise
        with patch("murmur.paste.time.sleep"):
            paste_text("test", restore_clipboard=True)


class TestTypeText:
    """Tests for type_text function."""

    def test_type_empty_text_noop(self, mock_keyboard_controller):
        """Empty string does nothing."""
        from murmur.paste import type_text

        type_text("")
        mock_keyboard_controller.type.assert_not_called()

    def test_type_sends_each_character(self, mock_keyboard_controller):
        """Each character is typed."""
        from murmur.paste import type_text

        with patch("murmur.paste.time.sleep"):
            type_text("abc")

        assert mock_keyboard_controller.type.call_count == 3
        mock_keyboard_controller.type.assert_any_call("a")
        mock_keyboard_controller.type.assert_any_call("b")
        mock_keyboard_controller.type.assert_any_call("c")

    def test_type_respects_delay(self, mock_keyboard_controller):
        """Delay between keystrokes observed."""
        from murmur.paste import type_text

        sleep_calls = []
        original_sleep = time.sleep

        def mock_sleep(duration):
            sleep_calls.append(duration)

        with patch("murmur.paste.time.sleep", mock_sleep):
            type_text("ab", delay=0.05)

        # Should have called sleep twice (once per character)
        assert len(sleep_calls) == 2
        assert all(d == 0.05 for d in sleep_calls)

    def test_type_zero_delay(self, mock_keyboard_controller):
        """Zero delay types immediately."""
        from murmur.paste import type_text

        sleep_called = {"value": False}

        def mock_sleep(duration):
            sleep_called["value"] = True

        with patch("murmur.paste.time.sleep", mock_sleep):
            type_text("abc", delay=0)

        # Sleep should not be called with 0 delay
        assert sleep_called["value"] is False
