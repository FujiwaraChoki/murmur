"""Tests for the Murmur app runtime."""

from __future__ import annotations

import importlib
import signal
import sys
import types
from unittest.mock import MagicMock, Mock, patch


def import_app_module():
    """Import murmur.app with lightweight macOS stubs."""
    sys.modules.pop("murmur.app", None)

    appkit = types.ModuleType("AppKit")
    shared_app = MagicMock()

    class NSObject:
        pass

    class NSApplication:
        @staticmethod
        def sharedApplication():  # noqa: N802 - mirrors AppKit API name
            return shared_app

    appkit.NSObject = NSObject
    appkit.NSApplication = NSApplication
    appkit.NSApplicationActivationPolicyAccessory = 1
    appkit._shared_application = shared_app

    objc = types.ModuleType("objc")
    objc.python_method = lambda func: func
    objc.super = super

    sounddevice = types.ModuleType("sounddevice")
    sounddevice.default = types.SimpleNamespace(device=[None, None])

    app_helper = types.ModuleType("PyObjCTools.AppHelper")
    app_helper.runEventLoop = Mock()
    app_helper.stopEventLoop = Mock()

    mach_signals = types.ModuleType("PyObjCTools.MachSignals")
    mach_signals.signal = Mock()

    pyobjc_tools = types.ModuleType("PyObjCTools")
    pyobjc_tools.AppHelper = app_helper
    pyobjc_tools.MachSignals = mach_signals

    overlay = types.ModuleType("murmur.overlay")
    overlay.IndicatorState = types.SimpleNamespace(
        RECORDING="recording",
        TRANSCRIBING="transcribing",
        IDLE="idle",
    )
    overlay.IndicatorWindow = MagicMock()

    updater = types.ModuleType("murmur.updater")
    updater.UpdateChecker = MagicMock()
    updater.UpdateResult = object

    fake_modules = {
        "AppKit": appkit,
        "objc": objc,
        "sounddevice": sounddevice,
        "PyObjCTools": pyobjc_tools,
        "PyObjCTools.AppHelper": app_helper,
        "PyObjCTools.MachSignals": mach_signals,
        "murmur.audio": types.SimpleNamespace(AudioRecorder=MagicMock()),
        "murmur.hotkey": types.SimpleNamespace(HotkeyHandler=MagicMock()),
        "murmur.overlay": overlay,
        "murmur.paste": types.SimpleNamespace(paste_text=Mock()),
        "murmur.settings": types.SimpleNamespace(
            SettingsWindow=MagicMock(),
            load_config=Mock(return_value={}),
        ),
        "murmur.snippets": types.SimpleNamespace(expand_snippets=lambda text, snippets: text),
        "murmur.transcribe": types.SimpleNamespace(Transcriber=MagicMock()),
        "murmur.updater": updater,
    }

    with patch.dict(sys.modules, fake_modules):
        return importlib.import_module("murmur.app")


class TestMurmurAppRunLoop:
    """Tests for event loop and shutdown behavior."""

    def test_run_enables_pyobjc_interrupt_bridge(self):
        """run() enables AppHelper's SIGINT bridge so Ctrl+C can quit."""
        app_module = import_app_module()
        app = app_module.MurmurApp()

        fake_status_bar = MagicMock()
        app_module.StatusBarController = MagicMock()
        app_module.StatusBarController.alloc.return_value.initWithCallbacks_quit_app_.return_value = (
            fake_status_bar
        )

        fake_indicator = MagicMock()
        app_module.IndicatorWindow = MagicMock(return_value=fake_indicator)

        fake_hotkey = MagicMock()
        fake_hotkey.start.return_value = True
        app_module.HotkeyHandler = MagicMock(return_value=fake_hotkey)

        class FakeThread:
            def __init__(self, target=None, daemon=None):
                self.target = target
                self.daemon = daemon

            def start(self):
                return None

        with patch.object(app_module.threading, "Thread", FakeThread):
            app.run()

        app_module.AppHelper.runEventLoop.assert_called_once_with(installInterrupt=True)

    def test_setup_signal_handlers_stops_event_loop_on_sigterm(self):
        """SIGTERM triggers a clean shutdown path through AppHelper."""
        app_module = import_app_module()
        app = app_module.MurmurApp()
        app.stop = Mock()

        app._setup_signal_handlers()

        app_module.MachSignals.signal.assert_called_once()
        signum, handler = app_module.MachSignals.signal.call_args.args
        assert signum == signal.SIGTERM

        handler(signal.SIGTERM)

        app.stop.assert_called_once()
        app_module.AppHelper.stopEventLoop.assert_called_once()

    def test_quit_terminates_nsapplication(self):
        """Menu-bar quit should terminate the NSApplication instance."""
        app_module = import_app_module()
        app = app_module.MurmurApp()
        app.stop = Mock()

        app._quit()

        app.stop.assert_called_once()
        app_module.AppHelper.stopEventLoop.assert_called_once()
        app_module.AppKit._shared_application.terminate_.assert_called_once_with(None)
