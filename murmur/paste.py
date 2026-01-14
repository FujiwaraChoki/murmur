"""Text insertion module for pasting transcribed text."""

from __future__ import annotations

import time

import pyperclip
from pynput.keyboard import Controller, Key


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    """Paste text to the active application.

    Copies text to clipboard and simulates Cmd+V.

    Args:
        text: Text to paste.
        restore_clipboard: Whether to restore the original clipboard content after pasting.
    """
    if not text:
        return

    # Save original clipboard content if requested
    original_clipboard = None
    if restore_clipboard:
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            original_clipboard = None

    # Copy text to clipboard
    pyperclip.copy(text)

    # Small delay to ensure clipboard is ready
    time.sleep(0.05)

    # Simulate Cmd+V
    keyboard = Controller()
    keyboard.press(Key.cmd)
    keyboard.press("v")
    keyboard.release("v")
    keyboard.release(Key.cmd)

    # Restore original clipboard content after a delay
    if restore_clipboard and original_clipboard is not None:
        time.sleep(0.1)
        try:
            pyperclip.copy(original_clipboard)
        except Exception:
            pass


def type_text(text: str, delay: float = 0.01) -> None:
    """Type text character by character.

    Alternative to paste_text that types each character individually.
    Slower but works in more applications.

    Args:
        text: Text to type.
        delay: Delay between keystrokes in seconds.
    """
    if not text:
        return

    keyboard = Controller()
    for char in text:
        keyboard.type(char)
        if delay > 0:
            time.sleep(delay)
