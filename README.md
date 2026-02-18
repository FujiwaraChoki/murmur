# Murmur

[![Lint](https://github.com/FujiwaraChoki/murmur/actions/workflows/lint.yml/badge.svg)](https://github.com/FujiwaraChoki/murmur/actions/workflows/lint.yml)
[![Test](https://github.com/FujiwaraChoki/murmur/actions/workflows/test.yml/badge.svg)](https://github.com/FujiwaraChoki/murmur/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Open-source voice dictation for macOS using Nvidia's Parakeet ASR model, optimized for Apple Silicon.

## Features

- **Real-time transcription** - Fast, accurate speech-to-text using Parakeet-MLX
- **Global hotkey** - Start/stop recording from anywhere (default: Cmd+Shift+Space)
- **Menu bar app** - Unobtrusive status indicator lives in your menu bar
- **Visual feedback** - Floating overlay bar shows recording/transcribing state
- **Auto-paste** - Transcribed text is automatically pasted into the active application
- **Configurable** - Customize hotkey, model, and audio device via settings or CLI

## Requirements

- **macOS** (Apple Silicon recommended for best performance)
- **Python 3.10+**

## Installation

### Download DMG (Recommended)

Download the latest `.dmg` from [GitHub Releases](https://github.com/FujiwaraChoki/murmur/releases), open it, and drag Murmur to Applications.

### From Source

```bash
# Clone the repository
git clone https://github.com/FujiwaraChoki/murmur.git
cd murmur

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

## Usage

```bash
# Start Murmur with default settings
murmur

# Use a custom hotkey
murmur --hotkey "cmd+shift+r"

# Use a different model
murmur --model "mlx-community/parakeet-tdt-0.6b-v3"

# List available audio input devices
murmur --list-devices

# Use a specific audio device
murmur --device 1
```

### Hotkey Format

Hotkeys are specified as modifier keys joined with `+`:
- Modifiers: `cmd`, `ctrl`, `alt`, `shift`
- Keys: Any single character or special key name
- Examples: `cmd+shift+space`, `ctrl+alt+r`, `cmd+d`

## macOS Permissions

Murmur requires the following permissions to function. You'll be prompted to grant these on first run:

| Permission | Location | Purpose |
|------------|----------|---------|
| **Microphone** | System Settings → Privacy & Security → Microphone | Record audio for transcription |
| **Accessibility** | System Settings → Privacy & Security → Accessibility | Simulate paste (Cmd+V) |
| **Input Monitoring** | System Settings → Privacy & Security → Input Monitoring | Detect global hotkey |

> **Tip**: If hotkeys aren't working, check that your terminal or Python is added to Input Monitoring.

## How It Works

1. **Press the hotkey** (Cmd+Shift+Space by default) to start recording
2. **Speak naturally** - audio is captured in real-time
3. **Release the hotkey** to stop recording
4. **Murmur transcribes** your speech using Parakeet-MLX
5. **Text is pasted** directly into the active application

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Hotkey    │────▶│    Audio     │────▶│ Transcriber │
│   Handler   │     │   Recorder   │     │  (Parakeet) │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Overlay    │     │    Paste    │
                    │   (Visual)   │     │   Handler   │
                    └──────────────┘     └─────────────┘
```

- **Main thread**: Runs macOS NSRunLoop for UI and events
- **Background threads**: Model loading, audio capture, transcription
- **Thread safety**: All shared state protected by locks

## Configuration

Settings are stored in `~/.config/murmur/config.json`. You can also access settings via the menu bar icon.

```json
{
  "hotkey": "cmd+shift+space",
  "model": "mlx-community/parakeet-tdt-0.6b-v2",
  "microphone_index": null,
  "check_updates": true
}
```

## Troubleshooting

### Hotkey not working
- Ensure the app is added to **Input Monitoring** in System Settings
- Try running from Terminal to see any permission prompts
- Check if another app is using the same hotkey

### No audio / microphone not detected
- Grant **Microphone** permission in System Settings
- Run `murmur --list-devices` to see available devices
- Try specifying a device with `--device`

### Slow transcription
- First run downloads the model (~500MB) which takes time
- Subsequent runs use cached model for faster startup
- Apple Silicon provides best performance; Intel Macs will be slower

### Permission denied errors
- Restart the app after granting permissions
- On some macOS versions, you may need to restart System Settings

## Known Limitations

- **macOS only** - Uses native macOS APIs (AppKit, Quartz)
- **Apple Silicon optimized** - Works on Intel but significantly slower
- **English primary** - Parakeet model is optimized for English
- **Hold-to-record** - Currently only supports push-to-talk mode

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check murmur/

# Run tests
pytest
```

## Acknowledgments

- [Parakeet-MLX](https://github.com/ml-explore/mlx-examples) - The ASR model powering transcription
- [MLX](https://github.com/ml-explore/mlx) - Apple's machine learning framework
- [pynput](https://github.com/moses-palmer/pynput) - Global hotkey detection
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) - Audio capture

## License

MIT License - see [LICENSE](LICENSE) for details.
