"""Global hotkey handler for macOS using native Quartz CGEventTap."""

from __future__ import annotations

import logging
import threading
from typing import Callable

import Quartz
from AppKit import NSEvent
from Foundation import NSObject

logger = logging.getLogger("murmur.hotkey")


class HotkeyHandler:
    """Handles global hotkey detection on macOS using native CGEventTap.

    This implementation uses macOS native APIs instead of pynput for better
    stability on Apple Silicon and newer macOS/Python versions.
    """

    # Modifier key masks (from Carbon/Events.h)
    MODIFIER_MAP = {
        "cmd": Quartz.kCGEventFlagMaskCommand,
        "command": Quartz.kCGEventFlagMaskCommand,
        "ctrl": Quartz.kCGEventFlagMaskControl,
        "control": Quartz.kCGEventFlagMaskControl,
        "alt": Quartz.kCGEventFlagMaskAlternate,
        "option": Quartz.kCGEventFlagMaskAlternate,
        "shift": Quartz.kCGEventFlagMaskShift,
    }

    # Key code mappings (macOS virtual key codes)
    KEYCODE_MAP = {
        "space": 49,
        "enter": 36,
        "return": 36,
        "tab": 48,
        "escape": 53,
        "esc": 53,
        "backspace": 51,
        "delete": 117,
        "up": 126,
        "down": 125,
        "left": 123,
        "right": 124,
        "home": 115,
        "end": 119,
        "page_up": 116,
        "page_down": 121,
        "f1": 122,
        "f2": 120,
        "f3": 99,
        "f4": 118,
        "f5": 96,
        "f6": 97,
        "f7": 98,
        "f8": 100,
        "f9": 101,
        "f10": 109,
        "f11": 103,
        "f12": 111,
        # Letter keys (ANSI layout)
        "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
        "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31,
        "p": 35, "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9,
        "w": 13, "x": 7, "y": 16, "z": 6,
        # Number keys
        "0": 29, "1": 18, "2": 19, "3": 20, "4": 21,
        "5": 23, "6": 22, "7": 26, "8": 28, "9": 25,
    }

    def __init__(
        self,
        hotkey: str = "alt+shift+space",
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

        self._target_modifiers: int = 0
        self._target_keycode: int | None = None
        self._is_hotkey_held = False
        self._lock = threading.Lock()

        self._tap = None
        self._run_loop_source = None
        self._tap_thread: threading.Thread | None = None
        self._running = False

        self._parse_hotkey()

    def _parse_hotkey(self) -> None:
        """Parse the hotkey string into modifier mask and keycode.

        Raises:
            ValueError: If the hotkey string is invalid or empty.
        """
        if not self.hotkey_str or not self.hotkey_str.strip():
            raise ValueError("Hotkey string cannot be empty")

        parts = [p.strip() for p in self.hotkey_str.split("+") if p.strip()]
        if not parts:
            raise ValueError("Hotkey string cannot be empty")

        self._target_modifiers = 0
        self._target_keycode = None

        for part in parts:
            if part in self.MODIFIER_MAP:
                self._target_modifiers |= self.MODIFIER_MAP[part]
            elif part in self.KEYCODE_MAP:
                if self._target_keycode is not None:
                    raise ValueError("Hotkey can include only one non-modifier key")
                self._target_keycode = self.KEYCODE_MAP[part]
            else:
                raise ValueError(f"Unknown key: '{part}'")

        if self._target_modifiers == 0:
            raise ValueError("Hotkey must include at least one modifier (cmd, ctrl, alt, shift)")
        # Note: _target_keycode can be None for modifier-only hotkeys

    def _check_modifiers(self, flags: int) -> bool:
        """Check if the required modifiers are pressed (at minimum)."""
        # Mask to only check the modifier bits we care about
        modifier_mask = (
            Quartz.kCGEventFlagMaskCommand
            | Quartz.kCGEventFlagMaskControl
            | Quartz.kCGEventFlagMaskAlternate
            | Quartz.kCGEventFlagMaskShift
        )
        current_modifiers = flags & modifier_mask
        return (current_modifiers & self._target_modifiers) == self._target_modifiers

    def _check_modifiers_exact(self, flags: int) -> bool:
        """Check if EXACTLY the required modifiers are pressed (for modifier-only hotkeys)."""
        modifier_mask = (
            Quartz.kCGEventFlagMaskCommand
            | Quartz.kCGEventFlagMaskControl
            | Quartz.kCGEventFlagMaskAlternate
            | Quartz.kCGEventFlagMaskShift
        )
        current_modifiers = flags & modifier_mask
        return current_modifiers == self._target_modifiers

    def _event_callback(self, proxy, event_type, event, refcon):
        """Callback for CGEventTap events."""
        try:
            if event_type == Quartz.kCGEventTapDisabledByTimeout:
                # Re-enable the tap if it times out
                if self._tap:
                    Quartz.CGEventTapEnable(self._tap, True)
                return event

            flags = Quartz.CGEventGetFlags(event)

            with self._lock:
                # Modifier-only hotkey (e.g., alt+shift)
                if self._target_keycode is None:
                    if event_type == Quartz.kCGEventFlagsChanged:
                        modifiers_match = self._check_modifiers_exact(flags)
                        if modifiers_match and not self._is_hotkey_held:
                            self._is_hotkey_held = True
                            if self.on_press_start:
                                threading.Thread(
                                    target=self.on_press_start, daemon=True
                                ).start()
                        elif not modifiers_match and self._is_hotkey_held:
                            self._is_hotkey_held = False
                            if self.on_release_end:
                                threading.Thread(
                                    target=self.on_release_end, daemon=True
                                ).start()
                # Regular hotkey with a key (e.g., alt+shift+space)
                else:
                    keycode = Quartz.CGEventGetIntegerValueField(
                        event, Quartz.kCGKeyboardEventKeycode
                    )
                    if keycode == self._target_keycode and self._check_modifiers(flags):
                        if event_type == Quartz.kCGEventKeyDown:
                            if not self._is_hotkey_held:
                                self._is_hotkey_held = True
                                if self.on_press_start:
                                    threading.Thread(
                                        target=self.on_press_start, daemon=True
                                    ).start()
                        elif event_type == Quartz.kCGEventKeyUp:
                            if self._is_hotkey_held:
                                self._is_hotkey_held = False
                                if self.on_release_end:
                                    threading.Thread(
                                        target=self.on_release_end, daemon=True
                                    ).start()
        except Exception:
            logger.debug("Error in event callback", exc_info=True)

        return event

    def _run_tap(self) -> None:
        """Run the event tap in a separate thread."""
        # Create event tap for key events
        event_mask = (
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
            | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
        )

        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            event_mask,
            self._event_callback,
            None,
        )

        if self._tap is None:
            logger.error("Failed to create event tap. Check Accessibility permissions.")
            return

        self._run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
            None, self._tap, 0
        )

        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            self._run_loop_source,
            Quartz.kCFRunLoopDefaultMode,
        )

        Quartz.CGEventTapEnable(self._tap, True)

        # Run until stopped
        while self._running:
            Quartz.CFRunLoopRunInMode(
                Quartz.kCFRunLoopDefaultMode, 0.1, False
            )

    def start(self) -> None:
        """Start listening for the hotkey."""
        if self._running:
            return

        logger.debug("Starting hotkey listener for '%s'", self.hotkey_str)
        self._running = True
        self._tap_thread = threading.Thread(target=self._run_tap, daemon=True)
        self._tap_thread.start()

    def stop(self) -> None:
        """Stop listening for the hotkey."""
        logger.debug("Stopping hotkey listener")
        self._running = False

        if self._tap:
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None

        if self._tap_thread:
            self._tap_thread.join(timeout=1.0)
            self._tap_thread = None

    def set_hotkey(self, hotkey: str) -> None:
        """Change the hotkey combination.

        Args:
            hotkey: New hotkey combination string.

        Raises:
            ValueError: If the hotkey string is invalid.
        """
        self.hotkey_str = hotkey.lower()
        self._parse_hotkey()

    @classmethod
    def validate_hotkey(cls, hotkey: str) -> tuple[bool, str]:
        """Validate a hotkey string without creating a handler.

        Args:
            hotkey: Hotkey combination string to validate.

        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        if not hotkey or not hotkey.strip():
            return False, "Hotkey cannot be empty"

        hotkey = hotkey.lower()
        parts = [p.strip() for p in hotkey.split("+") if p.strip()]
        if not parts:
            return False, "Hotkey cannot be empty"

        has_modifier = False
        modifier_count = 0
        key_count = 0

        for part in parts:
            if part in cls.MODIFIER_MAP:
                has_modifier = True
                modifier_count += 1
            elif part in cls.KEYCODE_MAP:
                key_count += 1
            else:
                return False, f"Unknown key: '{part}'"

        if not has_modifier:
            return False, "Hotkey must include at least one modifier (cmd, ctrl, alt, shift)"

        if key_count > 1:
            return False, "Hotkey can include only one non-modifier key"

        # Modifier-only hotkeys need at least 2 modifiers to avoid accidental triggers
        if modifier_count == len(parts) and modifier_count < 2:
            return False, "Modifier-only hotkey needs at least 2 modifiers"

        return True, ""

    @property
    def is_held(self) -> bool:
        """Check if the hotkey is currently being held."""
        return self._is_hotkey_held
