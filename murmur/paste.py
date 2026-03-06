"""Text insertion module for pasting transcribed text."""

from __future__ import annotations

import logging
import time

import pyperclip
import Quartz

logger = logging.getLogger("murmur.paste")


def paste_text(text: str, restore_clipboard: bool = True) -> None:
    """Paste text to the active application.

    Copies text to clipboard and simulates Cmd+V using native macOS APIs.

    Args:
        text: Text to paste.
        restore_clipboard: Whether to restore the original clipboard content after pasting.
    """
    if not text:
        return

    logger.debug("Pasting text (%d chars)", len(text))

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

    # Simulate Cmd+V using native macOS Quartz CGEvents
    # Key code 9 is 'v' on macOS
    _simulate_key_with_modifier(keycode=9, modifier=Quartz.kCGEventFlagMaskCommand)

    # Restore original clipboard content after a delay
    if restore_clipboard and original_clipboard is not None:
        time.sleep(0.1)
        try:
            pyperclip.copy(original_clipboard)
        except Exception:
            pass


def _simulate_key_with_modifier(keycode: int, modifier: int) -> None:
    """Simulate a key press with a modifier key using Quartz CGEvents.

    Args:
        keycode: The macOS virtual key code.
        modifier: The modifier flag (e.g., kCGEventFlagMaskCommand).
    """
    # Create key down event
    key_down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
    Quartz.CGEventSetFlags(key_down, modifier)

    # Create key up event
    key_up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
    Quartz.CGEventSetFlags(key_up, modifier)

    # Post events to the system
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)


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

    for char in text:
        _type_character(char)
        if delay > 0:
            time.sleep(delay)


def _type_character(char: str) -> None:
    """Type a single character using Quartz CGEvents.

    Args:
        char: The character to type.
    """
    # Create a keyboard event source
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)

    # Create key event with the character
    # Use CGEventKeyboardSetUnicodeString for Unicode support
    key_down = Quartz.CGEventCreateKeyboardEvent(source, 0, True)
    key_up = Quartz.CGEventCreateKeyboardEvent(source, 0, False)

    # Set the Unicode string for the event
    Quartz.CGEventKeyboardSetUnicodeString(key_down, len(char), char)
    Quartz.CGEventKeyboardSetUnicodeString(key_up, len(char), char)

    # Post the events
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)
