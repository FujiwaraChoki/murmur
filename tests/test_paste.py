"""Tests for the paste module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, Mock, call, patch

import pytest


class TestPasteText:
    """Tests for paste_text function."""

    def test_paste_empty_text_noop(self, mock_pyperclip, mock_quartz):
        """Empty string does nothing."""
        from murmur.paste import paste_text

        paste_text("")
        # CGEventPost should not have been called
        mock_quartz["CGEventPost"].assert_not_called()

    def test_paste_copies_to_clipboard(self, mock_pyperclip, mock_quartz):
        """Text is copied to clipboard."""
        from murmur.paste import paste_text

        paste_text("Hello World", restore_clipboard=False)
        assert mock_pyperclip["content"] == "Hello World"

    def test_paste_simulates_cmd_v(self, mock_pyperclip, mock_quartz):
        """Cmd+V key sequence is sent via CGEvents."""
        from murmur.paste import paste_text

        paste_text("test", restore_clipboard=False)

        # Should create keyboard events and post them
        mock_quartz["CGEventCreateKeyboardEvent"].assert_called()
        mock_quartz["CGEventSetFlags"].assert_called()
        mock_quartz["CGEventPost"].assert_called()

    def test_paste_restores_clipboard(self, mock_pyperclip, mock_quartz):
        """Original clipboard restored when flag True."""
        from murmur.paste import paste_text

        # Set original clipboard content
        mock_pyperclip["content"] = "original content"

        with patch("murmur.paste.time.sleep"):  # Speed up test
            paste_text("new content", restore_clipboard=True)

        # Clipboard should be restored to original
        assert mock_pyperclip["content"] == "original content"

    def test_paste_no_restore_when_disabled(self, mock_pyperclip, mock_quartz):
        """Clipboard not restored when flag False."""
        from murmur.paste import paste_text

        mock_pyperclip["content"] = "original content"

        with patch("murmur.paste.time.sleep"):
            paste_text("new content", restore_clipboard=False)

        # Clipboard should have new content
        assert mock_pyperclip["content"] == "new content"

    def test_paste_handles_clipboard_error(self, mock_quartz, monkeypatch):
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

    def test_type_empty_text_noop(self, mock_quartz):
        """Empty string does nothing."""
        from murmur.paste import type_text

        type_text("")
        mock_quartz["CGEventPost"].assert_not_called()

    def test_type_sends_each_character(self, mock_quartz):
        """Each character is typed via CGEvents."""
        from murmur.paste import type_text

        with patch("murmur.paste.time.sleep"):
            type_text("abc")

        # Should have created events for each character (key down + key up = 2 events per char)
        # 3 characters = 6 CGEventPost calls
        assert mock_quartz["CGEventPost"].call_count == 6

    def test_type_respects_delay(self, mock_quartz):
        """Delay between keystrokes observed."""
        from murmur.paste import type_text

        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        with patch("murmur.paste.time.sleep", mock_sleep):
            type_text("ab", delay=0.05)

        # Should have called sleep twice (once per character)
        assert len(sleep_calls) == 2
        assert all(d == 0.05 for d in sleep_calls)

    def test_type_zero_delay(self, mock_quartz):
        """Zero delay types immediately."""
        from murmur.paste import type_text

        sleep_called = {"value": False}

        def mock_sleep(duration):
            sleep_called["value"] = True

        with patch("murmur.paste.time.sleep", mock_sleep):
            type_text("abc", delay=0)

        # Sleep should not be called with 0 delay
        assert sleep_called["value"] is False
