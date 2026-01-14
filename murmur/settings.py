"""Settings window module for Murmur configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import AppKit
import objc
from Foundation import NSObject

from murmur.audio import list_audio_devices

# Config file location
CONFIG_DIR = Path.home() / ".config" / "murmur"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "hotkey": "cmd+shift+space",
    "microphone_index": None,  # None means default device
    "model": "mlx-community/parakeet-tdt-0.6b-v2",
    "check_updates": True,  # Check for updates on startup
}


def load_config() -> dict:
    """Load configuration from file.

    Returns:
        Configuration dictionary.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_CONFIG, **config}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class SettingsWindowDelegate(NSObject):
    """Delegate for the settings window."""

    def initWithCallback_(self, callback):
        self = objc.super(SettingsWindowDelegate, self).init()
        if self is None:
            return None
        self._callback = callback
        return self

    def windowWillClose_(self, notification):
        """Handle window close."""
        if self._callback:
            self._callback()


class SettingsWindow:
    """Settings window for configuring Murmur."""

    def __init__(
        self,
        current_config: dict,
        on_save: Callable[[dict], None] | None = None,
        on_close: Callable[[], None] | None = None,
    ):
        """Initialize the settings window.

        Args:
            current_config: Current configuration dictionary.
            on_save: Callback when settings are saved.
            on_close: Callback when window is closed.
        """
        self._config = current_config.copy()
        self._on_save = on_save
        self._on_close = on_close
        self._window = None
        self._hotkey_field = None
        self._mic_popup = None
        self._update_checkbox = None
        self._devices = []

    def show(self) -> None:
        """Show the settings window."""
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)
            return

        # Window dimensions
        width = 400
        height = 240

        # Get screen center
        screen = AppKit.NSScreen.mainScreen()
        screen_frame = screen.frame()
        x = (screen_frame.size.width - width) / 2
        y = (screen_frame.size.height - height) / 2

        # Create window
        window_rect = AppKit.NSMakeRect(x, y, width, height)
        self._window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskMiniaturizable,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._window.setTitle_("Murmur Settings")
        self._window.setLevel_(AppKit.NSFloatingWindowLevel)

        # Set delegate for close handling
        delegate = SettingsWindowDelegate.alloc().initWithCallback_(self._handle_close)
        self._window.setDelegate_(delegate)
        # Keep reference to prevent deallocation
        self._delegate = delegate

        # Create content view
        content = self._window.contentView()

        # Padding
        padding = 20
        label_width = 100
        control_x = padding + label_width + 10
        control_width = width - control_x - padding

        # Hotkey setting
        y_pos = height - 50
        hotkey_label = AppKit.NSTextField.labelWithString_("Hotkey:")
        hotkey_label.setFrame_(AppKit.NSMakeRect(padding, y_pos, label_width, 24))
        content.addSubview_(hotkey_label)

        self._hotkey_field = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(control_x, y_pos, control_width, 24)
        )
        self._hotkey_field.setStringValue_(self._config.get("hotkey", "cmd+shift+space"))
        self._hotkey_field.setPlaceholderString_("e.g., cmd+shift+space")
        content.addSubview_(self._hotkey_field)

        # Microphone setting
        y_pos -= 40
        mic_label = AppKit.NSTextField.labelWithString_("Microphone:")
        mic_label.setFrame_(AppKit.NSMakeRect(padding, y_pos, label_width, 24))
        content.addSubview_(mic_label)

        self._mic_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
            AppKit.NSMakeRect(control_x, y_pos, control_width, 24), False
        )
        self._populate_microphones()
        content.addSubview_(self._mic_popup)

        # Check for updates setting
        y_pos -= 40
        self._update_checkbox = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(padding, y_pos, width - 2 * padding, 24)
        )
        self._update_checkbox.setButtonType_(AppKit.NSButtonTypeSwitch)
        self._update_checkbox.setTitle_("Check for updates on startup")
        self._update_checkbox.setState_(
            AppKit.NSControlStateValueOn
            if self._config.get("check_updates", True)
            else AppKit.NSControlStateValueOff
        )
        content.addSubview_(self._update_checkbox)

        # Save button
        y_pos = padding
        save_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(width - padding - 100, y_pos, 100, 32)
        )
        save_button.setTitle_("Save")
        save_button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_button.setTarget_(self)
        save_button.setAction_(objc.selector(self.saveSettings_, signature=b"v@:@"))
        content.addSubview_(save_button)

        # Cancel button
        cancel_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(width - padding - 210, y_pos, 100, 32)
        )
        cancel_button.setTitle_("Cancel")
        cancel_button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        cancel_button.setTarget_(self)
        cancel_button.setAction_(objc.selector(self.cancelSettings_, signature=b"v@:@"))
        content.addSubview_(cancel_button)

        # Show window
        self._window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def _populate_microphones(self) -> None:
        """Populate the microphone dropdown."""
        self._mic_popup.removeAllItems()

        # Add default option
        self._mic_popup.addItemWithTitle_("System Default")
        self._devices = [None]  # None represents system default

        # Add available devices
        devices = list_audio_devices()
        for dev in devices:
            self._mic_popup.addItemWithTitle_(dev["name"])
            self._devices.append(dev["index"])

        # Select current device
        current_mic = self._config.get("microphone_index")
        if current_mic is None:
            self._mic_popup.selectItemAtIndex_(0)
        elif current_mic in self._devices:
            idx = self._devices.index(current_mic)
            self._mic_popup.selectItemAtIndex_(idx)

    def saveSettings_(self, sender) -> None:
        """Save settings and close window."""
        # Get values
        hotkey = self._hotkey_field.stringValue()
        mic_idx = self._mic_popup.indexOfSelectedItem()
        mic_device = self._devices[mic_idx] if mic_idx < len(self._devices) else None
        check_updates = self._update_checkbox.state() == AppKit.NSControlStateValueOn

        # Update config
        self._config["hotkey"] = hotkey
        self._config["microphone_index"] = mic_device
        self._config["check_updates"] = check_updates

        # Save to file
        save_config(self._config)

        # Notify callback
        if self._on_save:
            self._on_save(self._config)

        # Close window
        self._window.close()

    def cancelSettings_(self, sender) -> None:
        """Cancel and close window."""
        self._window.close()

    def _handle_close(self) -> None:
        """Handle window close."""
        self._window = None
        if self._on_close:
            self._on_close()

    def close(self) -> None:
        """Close the settings window."""
        if self._window is not None:
            self._window.close()
            self._window = None
