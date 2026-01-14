"""Global hotkey handler for macOS using PyObjC."""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard


class HotkeyHandler:
    """Handles global hotkey detection on macOS with hold-to-record support."""

    # Key mappings for parsing hotkey strings
    MODIFIER_KEYS = {
        "cmd": keyboard.Key.cmd,
        "command": keyboard.Key.cmd,
        "ctrl": keyboard.Key.ctrl,
        "control": keyboard.Key.ctrl,
        "alt": keyboard.Key.alt,
        "option": keyboard.Key.alt,
        "shift": keyboard.Key.shift,
    }

    def __init__(
        self,
        hotkey: str = "cmd+shift+space",
        on_press_start: Callable[[], None] | None = None,
        on_release_end: Callable[[], None] | None = None,
    ):
        """Initialize the hotkey handler.

        Args:
            hotkey: Hotkey combination string (e.g., "cmd+shift+space").
            on_press_start: Callback when hotkey is first pressed (start recording).
            on_release_end: Callback when hotkey is released (stop recording).
        """
        self.hotkey_str = hotkey.lower()
        self.on_press_start = on_press_start
        self.on_release_end = on_release_end
        self._listener: keyboard.Listener | None = None
        self._pressed_keys: set = set()
        self._target_modifiers: set = set()
        self._target_key: keyboard.Key | keyboard.KeyCode | None = None
        self._is_hotkey_held = False
        self._lock = threading.Lock()
        self._parse_hotkey()

    def _parse_hotkey(self) -> None:
        """Parse the hotkey string into modifiers and key."""
        parts = self.hotkey_str.split("+")
        self._target_modifiers = set()
        self._target_key = None

        for part in parts:
            part = part.strip()
            if part in self.MODIFIER_KEYS:
                self._target_modifiers.add(self.MODIFIER_KEYS[part])
            elif part == "space":
                self._target_key = keyboard.Key.space
            elif part == "enter" or part == "return":
                self._target_key = keyboard.Key.enter
            elif part == "tab":
                self._target_key = keyboard.Key.tab
            elif part == "escape" or part == "esc":
                self._target_key = keyboard.Key.esc
            elif len(part) == 1:
                self._target_key = keyboard.KeyCode.from_char(part)
            else:
                # Try to get from Key enum
                try:
                    self._target_key = getattr(keyboard.Key, part)
                except AttributeError:
                    self._target_key = keyboard.KeyCode.from_char(part[0])

    def _is_hotkey_pressed(self) -> bool:
        """Check if the hotkey combination is currently pressed."""
        # Check if all modifiers are pressed
        modifiers_pressed = all(mod in self._pressed_keys for mod in self._target_modifiers)

        if not modifiers_pressed:
            return False

        # Check if the target key is pressed
        if self._target_key is None:
            return modifiers_pressed

        if self._target_key in self._pressed_keys:
            return True

        # Also check for KeyCode matches
        for pressed in self._pressed_keys:
            if isinstance(pressed, keyboard.KeyCode) and isinstance(
                self._target_key, keyboard.KeyCode
            ):
                if pressed.char == self._target_key.char:
                    return True

        return False

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key press events."""
        with self._lock:
            self._pressed_keys.add(key)

            # Check if hotkey is now pressed and we weren't already holding it
            if not self._is_hotkey_held and self._is_hotkey_pressed():
                self._is_hotkey_held = True
                if self.on_press_start:
                    # Run callback in separate thread to avoid blocking
                    threading.Thread(target=self.on_press_start, daemon=True).start()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key release events."""
        with self._lock:
            self._pressed_keys.discard(key)

            # Check if we were holding the hotkey but now released it
            if self._is_hotkey_held and not self._is_hotkey_pressed():
                self._is_hotkey_held = False
                if self.on_release_end:
                    # Run callback in separate thread to avoid blocking
                    threading.Thread(target=self.on_release_end, daemon=True).start()

    def start(self) -> None:
        """Start listening for the hotkey."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for the hotkey."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def set_hotkey(self, hotkey: str) -> None:
        """Change the hotkey combination.

        Args:
            hotkey: New hotkey combination string.
        """
        self.hotkey_str = hotkey.lower()
        self._parse_hotkey()

    @property
    def is_held(self) -> bool:
        """Check if the hotkey is currently being held."""
        return self._is_hotkey_held
