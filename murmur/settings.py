"""Settings window module for Murmur configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import AppKit
import objc
from AppKit import NSEvent
from Foundation import NSObject

from murmur.audio import list_audio_devices
from murmur.hotkey import HotkeyHandler
from murmur.snippets import normalize_snippets

# Config file location
CONFIG_DIR = Path.home() / ".config" / "murmur"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "hotkey": "alt+shift",
    "microphone_index": None,  # None means default device
    "model": "mlx-community/parakeet-tdt-0.6b-v2",
    "check_updates": True,  # Check for updates on startup
    "snippets": [],
}

# Modifier key mappings for display
MODIFIER_FLAGS = {
    AppKit.NSEventModifierFlagCommand: "cmd",
    AppKit.NSEventModifierFlagShift: "shift",
    AppKit.NSEventModifierFlagOption: "alt",
    AppKit.NSEventModifierFlagControl: "ctrl",
}

# Special key code mappings
SPECIAL_KEYCODES = {
    49: "space",
    36: "enter",
    48: "tab",
    53: "escape",
    51: "backspace",
    117: "delete",
    126: "up",
    125: "down",
    123: "left",
    124: "right",
    115: "home",
    119: "end",
    116: "page_up",
    121: "page_down",
    122: "f1",
    120: "f2",
    99: "f3",
    118: "f4",
    96: "f5",
    97: "f6",
    98: "f7",
    100: "f8",
    101: "f9",
    109: "f10",
    103: "f11",
    111: "f12",
}


def _copy_config(config: dict | None = None) -> dict:
    """Create a config copy with normalized snippet data."""
    merged = {**DEFAULT_CONFIG, **(config or {})}
    merged["snippets"] = normalize_snippets(merged.get("snippets"))
    return merged


class ShortcutRecorderView(AppKit.NSView):
    """A view that records keyboard shortcuts when clicked."""

    def initWithFrame_onChange_(self, frame, on_change: Callable[[str], None] | None):
        """Initialize the shortcut recorder.

        Args:
            frame: The frame rectangle for the view.
            on_change: Callback when the shortcut changes.
        """
        self = objc.super(ShortcutRecorderView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._shortcut = ""
        self._is_recording = False
        self._on_change = on_change
        self._local_monitor = None
        self._current_modifiers = []  # Modifiers currently held during recording
        return self

    @objc.python_method
    def set_shortcut(self, shortcut: str) -> None:
        """Set the current shortcut string."""
        self._shortcut = shortcut
        self.setNeedsDisplay_(True)

    @objc.python_method
    def get_shortcut(self) -> str:
        """Get the current shortcut string."""
        return self._shortcut

    def acceptsFirstResponder(self) -> bool:
        return True

    def drawRect_(self, rect):
        """Draw the view."""
        bounds = self.bounds()

        # Background
        if self._is_recording:
            AppKit.NSColor.selectedControlColor().set()
        else:
            AppKit.NSColor.controlBackgroundColor().set()
        AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, 4.0, 4.0
        ).fill()

        # Border
        if self._is_recording:
            AppKit.NSColor.keyboardFocusIndicatorColor().set()
        else:
            AppKit.NSColor.separatorColor().set()
        AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            bounds, 4.0, 4.0
        ).stroke()

        # Text
        if self._is_recording:
            if self._current_modifiers:
                # Show currently held modifiers
                if len(self._current_modifiers) >= 2:
                    text = "+".join(self._current_modifiers) + " (Enter to confirm)"
                else:
                    text = "+".join(self._current_modifiers) + "+..."
                color = AppKit.NSColor.labelColor()
            else:
                text = "Press shortcut..."
                color = AppKit.NSColor.secondaryLabelColor()
        elif self._shortcut:
            text = self._shortcut
            color = AppKit.NSColor.labelColor()
        else:
            text = "Click to record"
            color = AppKit.NSColor.placeholderTextColor()

        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_(13),
            AppKit.NSForegroundColorAttributeName: color,
        }
        attr_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(text, attrs)
        text_size = attr_str.size()
        text_point = AppKit.NSMakePoint(
            (bounds.size.width - text_size.width) / 2,
            (bounds.size.height - text_size.height) / 2,
        )
        attr_str.drawAtPoint_(text_point)

    def mouseDown_(self, event):
        """Handle mouse click to start/stop recording."""
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    @objc.python_method
    def _start_recording(self) -> None:
        """Start recording keyboard input."""
        self._is_recording = True
        self._current_modifiers = []  # Track currently held modifiers
        self.setNeedsDisplay_(True)

        # Install local event monitor for key events AND modifier changes
        def handle_event(event):
            event_type = event.type()
            if event_type == AppKit.NSEventTypeKeyDown:
                self._handle_key_event(event)
                return None  # Consume the event
            elif event_type == AppKit.NSEventTypeFlagsChanged:
                self._handle_flags_changed(event)
            return event

        # Monitor both keyDown and flagsChanged events
        event_mask = AppKit.NSEventMaskKeyDown | AppKit.NSEventMaskFlagsChanged
        self._local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            event_mask, handle_event
        )

    @objc.python_method
    def _stop_recording(self) -> None:
        """Stop recording keyboard input."""
        self._is_recording = False
        self._current_modifiers = []
        if self._local_monitor:
            NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None
        self.setNeedsDisplay_(True)

    @objc.python_method
    def _handle_flags_changed(self, event) -> None:
        """Handle modifier key changes to show current modifiers."""
        raw_modifiers = event.modifierFlags()

        # Build list of currently held modifiers
        parts = []
        if raw_modifiers & AppKit.NSEventModifierFlagCommand:
            parts.append("cmd")
        if raw_modifiers & AppKit.NSEventModifierFlagControl:
            parts.append("ctrl")
        if raw_modifiers & AppKit.NSEventModifierFlagOption:
            parts.append("alt")
        if raw_modifiers & AppKit.NSEventModifierFlagShift:
            parts.append("shift")

        self._current_modifiers = parts
        self.setNeedsDisplay_(True)  # Redraw to show current modifiers

    @objc.python_method
    def _handle_key_event(self, event) -> None:
        """Handle a key event and build the shortcut string."""
        keycode = event.keyCode()

        # Escape cancels recording
        if keycode == 53:
            self._stop_recording()
            return

        # Enter confirms modifier-only shortcut (if at least 2 modifiers held)
        if keycode == 36 and len(self._current_modifiers) >= 2:
            shortcut = "+".join(self._current_modifiers)
            is_valid, error = HotkeyHandler.validate_hotkey(shortcut)
            if is_valid:
                self._shortcut = shortcut
                if self._on_change:
                    self._on_change(shortcut)
                self._stop_recording()
                return

        # Get the key from keycode
        key = None
        if keycode in SPECIAL_KEYCODES:
            key = SPECIAL_KEYCODES[keycode]
        else:
            chars = event.charactersIgnoringModifiers()
            if chars and len(chars) == 1:
                char = chars.lower()
                if char.isalnum():
                    key = char

        # Need at least one modifier and a key
        if self._current_modifiers and key:
            parts = self._current_modifiers + [key]
            shortcut = "+".join(parts)

            # Validate the shortcut
            is_valid, error = HotkeyHandler.validate_hotkey(shortcut)
            if is_valid:
                self._shortcut = shortcut
                if self._on_change:
                    self._on_change(shortcut)
                self._stop_recording()

    def viewDidMoveToWindow(self):
        """Clean up when view is removed from window."""
        if self.window() is None and self._local_monitor:
            NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None


def load_config() -> dict:
    """Load configuration from file.

    Returns:
        Configuration dictionary.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                merged = _copy_config(config)
                config_changed = merged.get("snippets") != config.get("snippets", [])
                is_valid, _ = HotkeyHandler.validate_hotkey(merged["hotkey"])
                if not is_valid:
                    merged["hotkey"] = DEFAULT_CONFIG["hotkey"]
                    config_changed = True
                if config_changed:
                    save_config(merged)
                return merged
        except Exception:
            pass
    return _copy_config()


def save_config(config: dict) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
    """
    config = _copy_config(config)
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


class SettingsWindow(NSObject):
    """Settings window for configuring Murmur."""

    def initWithConfig_onSave_onClose_(
        self,
        current_config: dict,
        on_save: Callable[[dict], None] | None,
        on_close: Callable[[], None] | None,
    ):
        """Initialize the settings window.

        Args:
            current_config: Current configuration dictionary.
            on_save: Callback when settings are saved.
            on_close: Callback when window is closed.
        """
        self = objc.super(SettingsWindow, self).init()
        if self is None:
            return None
        self._config = _copy_config(current_config)
        self._on_save = on_save
        self._on_close = on_close
        self._window = None
        self._hotkey_recorder = None
        self._mic_popup = None
        self._update_checkbox = None
        self._snippet_scroll = None
        self._snippet_document = None
        self._snippet_rows = []
        self._snippet_empty_label = None
        self._devices = []
        return self

    @objc.python_method
    def _on_hotkey_changed(self, shortcut: str) -> None:
        """Handle hotkey change from recorder."""
        pass  # The recorder validates internally; shortcut is stored in the recorder

    @objc.python_method
    def _create_snippet_row(self, trigger: str = "", replacement: str = "") -> dict:
        """Create a snippet editor row."""
        row_view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 52))

        trigger_field = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 30))
        trigger_field.setPlaceholderString_("Spoken phrase")
        trigger_field.setStringValue_(trigger)
        row_view.addSubview_(trigger_field)

        replacement_field = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 1, 30)
        )
        replacement_field.setPlaceholderString_("Insert this text")
        replacement_field.setStringValue_(replacement)
        row_view.addSubview_(replacement_field)

        remove_button = AppKit.NSButton.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 72, 30))
        remove_button.setTitle_("Remove")
        remove_button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        remove_button.setTarget_(self)
        remove_button.setAction_(objc.selector(self.removeSnippetRow_, signature=b"v@:@"))
        row_view.addSubview_(remove_button)

        return {
            "view": row_view,
            "trigger_field": trigger_field,
            "replacement_field": replacement_field,
            "remove_button": remove_button,
        }

    @objc.python_method
    def _layout_snippet_rows(self) -> None:
        """Lay out snippet rows within the scroll view."""
        if self._snippet_document is None:
            return

        row_height = 52
        row_spacing = 10
        content_width = self._snippet_scroll.contentSize().width
        row_width = max(content_width - 12, 320)
        trigger_width = max(120, int(row_width * 0.32))
        remove_width = 72
        gutter = 10
        replacement_width = max(120, row_width - trigger_width - remove_width - gutter * 2)

        total_height = max(
            120,
            len(self._snippet_rows) * row_height
            + max(0, len(self._snippet_rows) - 1) * row_spacing,
        )
        self._snippet_document.setFrame_(AppKit.NSMakeRect(0, 0, content_width, total_height))

        for index, row in enumerate(self._snippet_rows):
            y_pos = total_height - row_height - index * (row_height + row_spacing)
            row["view"].setFrame_(AppKit.NSMakeRect(6, y_pos, row_width, row_height))
            row["trigger_field"].setFrame_(AppKit.NSMakeRect(0, 20, trigger_width, 30))
            row["replacement_field"].setFrame_(
                AppKit.NSMakeRect(trigger_width + gutter, 20, replacement_width, 30)
            )
            row["remove_button"].setFrame_(
                AppKit.NSMakeRect(
                    trigger_width + gutter + replacement_width + gutter,
                    20,
                    remove_width,
                    30,
                )
            )
            row["remove_button"].setTag_(index)

        if self._snippet_empty_label is not None:
            self._snippet_empty_label.setHidden_(bool(self._snippet_rows))
            self._snippet_empty_label.setFrame_(AppKit.NSMakeRect(8, 42, row_width - 16, 32))

    @objc.python_method
    def _add_snippet_row(self, trigger: str = "", replacement: str = "") -> None:
        """Append a snippet row to the editor."""
        if self._snippet_document is None:
            return

        row = self._create_snippet_row(trigger=trigger, replacement=replacement)
        self._snippet_rows.append(row)
        self._snippet_document.addSubview_(row["view"])
        self._layout_snippet_rows()

    @objc.python_method
    def _collect_snippets(self) -> list[dict[str, str]]:
        """Collect snippet rows into normalized config data."""
        raw_snippets = []
        for row in self._snippet_rows:
            raw_snippets.append(
                {
                    "trigger": row["trigger_field"].stringValue(),
                    "replacement": row["replacement_field"].stringValue(),
                }
            )
        return normalize_snippets(raw_snippets)

    def addSnippetRow_(self, sender) -> None:
        """Add a new blank snippet row."""
        self._add_snippet_row()

    def removeSnippetRow_(self, sender) -> None:
        """Remove an existing snippet row."""
        index = sender.tag()
        if 0 <= index < len(self._snippet_rows):
            row = self._snippet_rows.pop(index)
            row["view"].removeFromSuperview()
            self._layout_snippet_rows()

    def show(self) -> None:
        """Show the settings window."""
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)
            return

        # Window dimensions
        width = 620
        height = 470

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
        y_pos = height - 58
        hotkey_label = AppKit.NSTextField.labelWithString_("Hotkey:")
        hotkey_label.setFrame_(AppKit.NSMakeRect(padding, y_pos, label_width, 24))
        content.addSubview_(hotkey_label)

        self._hotkey_recorder = ShortcutRecorderView.alloc().initWithFrame_onChange_(
            AppKit.NSMakeRect(control_x, y_pos, control_width, 24),
            self._on_hotkey_changed,
        )
        self._hotkey_recorder.set_shortcut(self._config.get("hotkey", "alt+shift"))
        content.addSubview_(self._hotkey_recorder)

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

        # Snippets section
        y_pos -= 48
        snippets_label = AppKit.NSTextField.labelWithString_("Snippets:")
        snippets_label.setFrame_(AppKit.NSMakeRect(padding, y_pos, label_width, 24))
        content.addSubview_(snippets_label)

        snippet_help = AppKit.NSTextField.labelWithString_(
            "Replace spoken words or phrases with saved text before Murmur pastes it."
        )
        snippet_help.setFrame_(AppKit.NSMakeRect(control_x, y_pos, control_width - 110, 24))
        snippet_help.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        content.addSubview_(snippet_help)

        add_button = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(width - padding - 94, y_pos - 2, 94, 28)
        )
        add_button.setTitle_("Add Snippet")
        add_button.setBezelStyle_(AppKit.NSBezelStyleRounded)
        add_button.setTarget_(self)
        add_button.setAction_(objc.selector(self.addSnippetRow_, signature=b"v@:@"))
        content.addSubview_(add_button)

        y_pos -= 28
        trigger_header = AppKit.NSTextField.labelWithString_("Trigger")
        trigger_header.setFrame_(AppKit.NSMakeRect(control_x, y_pos, 120, 18))
        trigger_header.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        content.addSubview_(trigger_header)

        replacement_header = AppKit.NSTextField.labelWithString_("Replacement")
        replacement_header.setFrame_(AppKit.NSMakeRect(control_x + 175, y_pos, 160, 18))
        replacement_header.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        content.addSubview_(replacement_header)

        scroll_height = 170
        y_pos -= scroll_height + 8
        self._snippet_scroll = AppKit.NSScrollView.alloc().initWithFrame_(
            AppKit.NSMakeRect(control_x, y_pos, control_width, scroll_height)
        )
        self._snippet_scroll.setHasVerticalScroller_(True)
        self._snippet_scroll.setBorderType_(AppKit.NSBezelBorder)
        self._snippet_scroll.setAutohidesScrollers_(True)

        self._snippet_document = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, control_width, scroll_height)
        )
        self._snippet_scroll.setDocumentView_(self._snippet_document)
        content.addSubview_(self._snippet_scroll)

        self._snippet_empty_label = AppKit.NSTextField.labelWithString_(
            "No snippets yet. Add one to expand a spoken phrase into reusable text."
        )
        self._snippet_empty_label.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        self._snippet_document.addSubview_(self._snippet_empty_label)

        for snippet in self._config.get("snippets", []):
            self._add_snippet_row(
                trigger=snippet.get("trigger", ""),
                replacement=snippet.get("replacement", ""),
            )
        self._layout_snippet_rows()

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
        hotkey = self._hotkey_recorder.get_shortcut()
        mic_idx = self._mic_popup.indexOfSelectedItem()
        mic_device = self._devices[mic_idx] if mic_idx < len(self._devices) else None
        check_updates = self._update_checkbox.state() == AppKit.NSControlStateValueOn

        # Validate hotkey before saving
        is_valid, error = HotkeyHandler.validate_hotkey(hotkey)
        if not is_valid:
            # Show alert
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Invalid Hotkey")
            alert.setInformativeText_(error)
            alert.setAlertStyle_(AppKit.NSAlertStyleWarning)
            alert.runModal()
            return

        # Update config
        self._config["hotkey"] = hotkey
        self._config["microphone_index"] = mic_device
        self._config["check_updates"] = check_updates
        self._config["snippets"] = self._collect_snippets()

        # Save to file
        save_config(self._config)

        # Notify callback
        if self._on_save:
            self._on_save(self._config)

        # Stop any active recording to clean up event monitors
        if self._hotkey_recorder:
            self._hotkey_recorder._stop_recording()

        # Close window
        self._window.close()

    def cancelSettings_(self, sender) -> None:
        """Cancel and close window."""
        # Stop any active recording to clean up event monitors
        if self._hotkey_recorder:
            self._hotkey_recorder._stop_recording()
        self._window.close()

    def _handle_close(self) -> None:
        """Handle window close."""
        # Ensure recording is stopped
        if self._hotkey_recorder:
            self._hotkey_recorder._stop_recording()
        self._window = None
        if self._on_close:
            self._on_close()

    def close(self) -> None:
        """Close the settings window."""
        if self._window is not None:
            self._window.close()
            self._window = None
