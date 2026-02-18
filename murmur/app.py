"""Application module for Murmur with overlay indicator bar."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time

import AppKit
import objc
import sounddevice as sd
from PyObjCTools import AppHelper

from murmur.audio import AudioRecorder
from murmur.hotkey import HotkeyHandler
from murmur.overlay import IndicatorState, IndicatorWindow
from murmur.paste import paste_text
from murmur.settings import SettingsWindow, load_config
from murmur.transcribe import Transcriber
from murmur.updater import UpdateChecker, UpdateResult

logger = logging.getLogger("murmur.app")


class StatusBarController(AppKit.NSObject):
    """Simple menu bar icon with settings access."""

    def initWithCallbacks_quit_app_(
        self, on_settings: callable, on_quit: callable, app: "MurmurApp"
    ):
        self = objc.super(StatusBarController, self).init()
        if self is None:
            return None
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._app = app
        self._status_item = None
        self._update_menu_item = None
        self._update_result: UpdateResult | None = None
        return self

    def setup(self):
        """Create the status bar item."""
        status_bar = AppKit.NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)

        # Load menu bar icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "menubar-icon.png"
        )
        if os.path.exists(icon_path):
            icon = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
            icon.setTemplate_(True)  # Adapts to light/dark mode
            self._status_item.button().setImage_(icon)
        else:
            self._status_item.setTitle_("M")

        # Create menu
        menu = AppKit.NSMenu.alloc().init()

        # Check for Updates item
        self._update_menu_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Check for Updates", "checkForUpdates:", ""
        )
        self._update_menu_item.setTarget_(self)
        menu.addItem_(self._update_menu_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Settings item
        settings_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "openSettings:", ""
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # Quit item
        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Murmur", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

    @objc.python_method
    def remove(self):
        """Remove the status bar item."""
        if self._status_item:
            status_bar = AppKit.NSStatusBar.systemStatusBar()
            status_bar.removeStatusItem_(self._status_item)
            self._status_item = None

    def openSettings_(self, sender):
        """Handle settings menu click."""
        if self._on_settings:
            self._on_settings()

    def quitApp_(self, sender):
        """Handle quit menu click."""
        if self._on_quit:
            self._on_quit()

    def checkForUpdates_(self, sender):
        """Handle check for updates menu click."""
        if self._update_result and self._update_result.available:
            # If update is available, open the release page
            self._open_release_page()
        else:
            # Trigger manual update check
            if self._app:
                threading.Thread(
                    target=self._app._check_for_updates,
                    kwargs={"force": True},
                    daemon=True,
                ).start()

    @objc.python_method
    def _open_release_page(self):
        """Open the GitHub release page in browser."""
        if self._update_result and self._update_result.release_url:
            url = AppKit.NSURL.URLWithString_(self._update_result.release_url)
            AppKit.NSWorkspace.sharedWorkspace().openURL_(url)

    def updateMenuForNewVersion_(self, result):
        """Update menu item to show available version (called from main thread)."""
        if result is None:
            return
        self._update_result = result
        if result.available and self._update_menu_item:
            self._update_menu_item.setTitle_(f"Update Available (v{result.latest_version})")

    @objc.python_method
    def set_update_result(self, result: UpdateResult | None):
        """Set the update result and update menu on main thread."""
        if result is None:
            return
        # Update on main thread
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateMenuForNewVersion:", result, False
        )


class MurmurApp:
    """Murmur application with overlay indicator bar."""

    def __init__(
        self,
        model_name: str | None = None,
        hotkey: str | None = None,
        microphone_index: int | None = None,
    ):
        """Initialize the Murmur app.

        Args:
            model_name: HuggingFace model name for parakeet-mlx (overrides config).
            hotkey: Hotkey combination string (overrides config).
            microphone_index: Audio input device index (overrides config).
        """
        # Load configuration
        self._config = load_config()

        # Override config with CLI arguments if provided
        if model_name:
            self._config["model"] = model_name
        if hotkey:
            self._config["hotkey"] = hotkey
        if microphone_index is not None:
            self._config["microphone_index"] = microphone_index

        self._transcriber: Transcriber | None = None
        self._recorder: AudioRecorder | None = None
        self._hotkey_handler: HotkeyHandler | None = None
        self._indicator: IndicatorWindow | None = None
        self._settings_window: SettingsWindow | None = None
        self._status_bar: StatusBarController | None = None
        self._update_checker = UpdateChecker()
        self._lock = threading.Lock()
        self._running = False
        self._model_loaded = False

    @property
    def model_name(self) -> str:
        """Get the model name from config."""
        return self._config.get("model", "mlx-community/parakeet-tdt-0.6b-v2")

    @property
    def hotkey_str(self) -> str:
        """Get the hotkey from config."""
        return self._config.get("hotkey", "alt+shift")

    @property
    def microphone_index(self) -> int | None:
        """Get the microphone index from config."""
        return self._config.get("microphone_index")

    def _start_recording(self) -> None:
        """Start recording audio (called when hotkey is pressed)."""
        with self._lock:
            if not self._model_loaded:
                logger.debug("Hotkey pressed but model not loaded yet")
                return

            if self._recorder is None:
                logger.debug("Hotkey pressed but recorder not initialized")
                return

            if self._recorder.is_recording:
                return

            logger.info("Recording started")
            self._recorder.start()
            if self._indicator:
                self._indicator.set_state(IndicatorState.RECORDING)

    def _stop_recording(self) -> None:
        """Stop recording and transcribe (called when hotkey is released)."""
        with self._lock:
            if self._recorder is None or not self._recorder.is_recording:
                return

            audio = self._recorder.stop()
            logger.info("Recording stopped — %d samples captured", audio.size)

            if self._indicator:
                self._indicator.set_state(IndicatorState.TRANSCRIBING)

        # Transcribe in background thread
        def transcribe():
            try:
                if audio.size > 0 and self._transcriber:
                    logger.debug("Starting transcription (%d samples)", audio.size)
                    text = self._transcriber.transcribe(audio)
                    if text:
                        logger.info("Transcription result: %r", text)
                        # Small delay to ensure we're not still in hotkey release
                        time.sleep(0.15)
                        paste_text(text)
                    else:
                        logger.info("Transcription returned empty text")
                else:
                    logger.debug("Skipping transcription (no audio or no model)")
            except Exception:
                logger.exception("Transcription error")
            finally:
                if self._indicator:
                    self._indicator.set_state(IndicatorState.IDLE)

        threading.Thread(target=transcribe, daemon=True).start()

    def _load_model(self) -> None:
        """Load the transcription model."""
        logger.info("Loading model: %s", self.model_name)

        try:
            self._transcriber = Transcriber(self.model_name)
            self._transcriber.load_model()

            # Initialize audio recorder with model's sample rate
            # Set microphone device if configured
            mic_idx = self.microphone_index
            if mic_idx is not None:
                sd.default.device[0] = mic_idx
                logger.debug("Microphone device set to index %d", mic_idx)

            self._recorder = AudioRecorder(sample_rate=self._transcriber.sample_rate)

            self._model_loaded = True
            logger.info(
                "Model loaded — sample rate %d Hz. Hold %s to record.",
                self._transcriber.sample_rate,
                self.hotkey_str,
            )

            if self._indicator:
                self._indicator.set_state(IndicatorState.IDLE)

        except Exception:
            logger.exception("Failed to load model")
            # This runs on a background thread; exiting here only stops that thread.
            # Stop the app cleanly on the main thread instead.
            AppHelper.callAfter(self._quit)

    def _check_for_updates(self, force: bool = False) -> None:
        """Check for updates in background thread."""
        # Check if update checking is enabled
        if not force and not self._config.get("check_updates", True):
            logger.debug("Update checking disabled in config")
            return

        logger.debug("Checking for updates (force=%s)", force)
        result = self._update_checker.check_for_update()
        if result and self._status_bar:
            self._status_bar.set_update_result(result)
            if result.available:
                logger.info("Update available: v%s", result.latest_version)
            else:
                logger.debug("Already on latest version")

    def _open_settings(self) -> None:
        """Open the settings window."""
        if self._settings_window is not None:
            return

        def on_save(new_config: dict) -> bool:
            """Handle settings save."""
            old_hotkey = self._config.get("hotkey")
            old_mic = self._config.get("microphone_index")
            hotkey_updated = False

            # Update hotkey if changed
            if new_config.get("hotkey") != old_hotkey and self._hotkey_handler:
                new_hotkey = new_config.get("hotkey", "alt+shift")
                try:
                    # Validate first before stopping the old handler
                    is_valid, error = HotkeyHandler.validate_hotkey(new_hotkey)
                    if not is_valid:
                        logger.warning("Invalid hotkey '%s': %s", new_hotkey, error)
                        return False

                    self._hotkey_handler.stop()
                    self._hotkey_handler = HotkeyHandler(
                        hotkey=new_hotkey,
                        on_press_start=self._start_recording,
                        on_release_end=self._stop_recording,
                    )
                    self._hotkey_handler.start()
                    hotkey_updated = True
                    logger.info("Hotkey updated to: %s", new_hotkey)
                except Exception:
                    logger.exception("Failed to update hotkey, restoring %s", old_hotkey)
                    # Try to restart the old handler
                    try:
                        self._hotkey_handler = HotkeyHandler(
                            hotkey=old_hotkey,
                            on_press_start=self._start_recording,
                            on_release_end=self._stop_recording,
                        )
                        self._hotkey_handler.start()
                    except Exception:
                        logger.critical("Could not restore hotkey handler")
                    return False

            # Update microphone if changed
            if new_config.get("microphone_index") != old_mic:
                try:
                    mic_idx = new_config.get("microphone_index")
                    if mic_idx is not None:
                        sd.default.device[0] = mic_idx
                        logger.info("Microphone updated to device index: %d", mic_idx)
                    else:
                        sd.default.device[0] = None
                        logger.info("Microphone set to system default")
                except Exception:
                    logger.exception("Failed to update microphone")
                    if hotkey_updated and old_hotkey is not None:
                        try:
                            self._hotkey_handler.stop()
                            self._hotkey_handler = HotkeyHandler(
                                hotkey=old_hotkey,
                                on_press_start=self._start_recording,
                                on_release_end=self._stop_recording,
                            )
                            self._hotkey_handler.start()
                            logger.info("Restored previous hotkey: %s", old_hotkey)
                        except Exception:
                            logger.critical("Could not restore hotkey handler")
                    return False

            self._config = new_config.copy()
            self._settings_window = None
            return True

        def on_close():
            """Handle settings window close."""
            self._settings_window = None

        self._settings_window = SettingsWindow.alloc().initWithConfig_onSave_onClose_(
            self._config, on_save, on_close
        )
        self._settings_window.show()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for clean shutdown."""

        def signal_handler(signum, frame):
            logger.info("Received signal %s, shutting down", signum)
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self) -> None:
        """Run the Murmur application."""
        self._running = True
        self._setup_signal_handlers()

        # Initialize NSApplication - required for receiving mouse events
        app = AppKit.NSApplication.sharedApplication()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        app.activateIgnoringOtherApps_(True)

        # Create menu bar icon
        self._status_bar = StatusBarController.alloc().initWithCallbacks_quit_app_(
            self._open_settings,
            self._quit,
            self,
        )
        self._status_bar.setup()

        # Check for updates in background
        threading.Thread(target=self._check_for_updates, daemon=True).start()

        # Create and show the indicator window
        self._indicator = IndicatorWindow(
            width=70,
            height=10,
            on_click=self._open_settings,
        )
        self._indicator.show()

        # Load model in background
        load_thread = threading.Thread(target=self._load_model, daemon=True)
        load_thread.start()

        # Setup hotkey handler
        self._hotkey_handler = HotkeyHandler(
            hotkey=self.hotkey_str,
            on_press_start=self._start_recording,
            on_release_end=self._stop_recording,
        )
        self._hotkey_handler.start()

        # Run the macOS event loop
        logger.info("Murmur is running. Press Ctrl+C to quit.")
        try:
            # Use AppHelper for proper event loop handling
            AppHelper.runEventLoop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _quit(self) -> None:
        """Quit the application from menu."""
        self.stop()
        AppHelper.stopEventLoop()

    def stop(self) -> None:
        """Stop the application."""
        self._running = False

        if self._recorder and self._recorder.is_recording:
            try:
                self._recorder.stop()
            except Exception:
                pass

        if self._hotkey_handler:
            self._hotkey_handler.stop()
            self._hotkey_handler = None

        if self._settings_window:
            self._settings_window.close()
            self._settings_window = None

        if self._status_bar:
            self._status_bar.remove()
            self._status_bar = None

        if self._indicator:
            self._indicator.hide()
            self._indicator = None

        self._recorder = None
        self._transcriber = None


def run_app(
    model_name: str | None = None,
    hotkey: str | None = None,
    microphone_index: int | None = None,
) -> None:
    """Run the Murmur application.

    Args:
        model_name: HuggingFace model name for parakeet-mlx.
        hotkey: Hotkey combination string.
        microphone_index: Audio input device index.
    """
    app = MurmurApp(
        model_name=model_name,
        hotkey=hotkey,
        microphone_index=microphone_index,
    )
    app.run()
