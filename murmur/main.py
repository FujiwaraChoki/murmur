"""Main entry point for Murmur."""

from __future__ import annotations

import logging
import os

# Prevent macOS crash when libraries fork() after Cocoa initialization.
# Must be set before importing any PyObjC modules.
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

import argparse
import sys

from murmur.logging_config import setup_logging

logger = logging.getLogger("murmur.main")


def _ensure_model_cached(model_name: str) -> None:
    """Pre-download model files before starting the macOS app.

    Downloading large model files after macOS NSApplication is initialized
    can crash the process due to fork-safety issues with Cocoa. This
    function ensures the model is in the HuggingFace cache beforehand.
    """
    try:
        from huggingface_hub import snapshot_download

        logger.debug("Pre-downloading model %s to cache", model_name)
        snapshot_download(model_name)
        logger.debug("Model cache download complete")
    except Exception as e:
        logger.debug("Model cache pre-download skipped: %s", e)


def main() -> int:
    """Main entry point for the murmur command."""
    parser = argparse.ArgumentParser(
        prog="murmur",
        description="Open-source voice dictation using Nvidia Parakeet",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="mlx-community/parakeet-tdt-0.6b-v2",
        help="HuggingFace model name for parakeet-mlx (default: mlx-community/parakeet-tdt-0.6b-v2)",
    )
    parser.add_argument(
        "--hotkey",
        "-k",
        default="alt+shift",
        help="Hotkey combination to hold for recording (default: alt+shift)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index (see --list-devices)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Show version and exit",
    )

    args = parser.parse_args()

    if args.version:
        from murmur import __version__

        print(f"murmur {__version__}")
        return 0

    if args.list_devices:
        from murmur.audio import get_default_input_device, list_audio_devices

        print("Available audio input devices:")
        print("-" * 40)
        devices = list_audio_devices()
        default = get_default_input_device()
        default_idx = default["index"] if default else None

        for dev in devices:
            marker = " (default)" if dev["index"] == default_idx else ""
            print(f"  [{dev['index']}] {dev['name']}{marker}")
            print(f"      Channels: {dev['channels']}, Sample Rate: {dev['sample_rate']}")
        return 0

    # Initialize logging before starting the app
    setup_logging()
    logger.info("Murmur starting up")

    logger.info("Hotkey: %s | Model: %s", args.hotkey, args.model)
    if args.device is not None:
        logger.info("Using microphone device index: %d", args.device)

    # Pre-download model to cache before starting Cocoa app.
    # huggingface_hub may fork/use multiprocessing during downloads,
    # which crashes on macOS after NSApplication is initialized.
    _ensure_model_cached(args.model)

    # Run the app with overlay indicator
    from murmur.app import run_app

    try:
        run_app(
            model_name=args.model,
            hotkey=args.hotkey,
            microphone_index=args.device,
        )
    except KeyboardInterrupt:
        logger.info("Murmur stopped by user")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
