"""Main entry point for Murmur."""

from __future__ import annotations

import argparse
import sys


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
        default="cmd+shift+space",
        help="Hotkey combination to hold for recording (default: cmd+shift+space)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
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

    # Run the app with overlay indicator
    from murmur.app import run_app

    print(f"Starting Murmur with hotkey: {args.hotkey}")
    print(f"Using model: {args.model}")
    print("Hold the hotkey to record, release to transcribe.")
    print("Look for the indicator bar at the bottom of your screen.")

    try:
        run_app(model_name=args.model, hotkey=args.hotkey)
    except KeyboardInterrupt:
        print("\nMurmur stopped.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
