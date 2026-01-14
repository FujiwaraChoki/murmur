# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Murmur is a macOS voice dictation app that provides real-time speech-to-text using Nvidia's Parakeet ASR model optimized for Apple Silicon. It uses a global hotkey to activate recording, shows a visual indicator bar, and automatically pastes transcribed text.

## Development Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the app
murmur                              # Default: cmd+shift+space hotkey
murmur --hotkey "cmd+shift+r"       # Custom hotkey
murmur --model "mlx-community/parakeet-tdt-0.6b-v3"
murmur --list-devices               # List audio input devices

# Linting and formatting
ruff check murmur/
ruff format murmur/

# Testing
pytest
```

## Architecture

### Threading Model
- **Main thread**: Runs macOS NSRunLoop for event handling and UI updates
- **Background threads**: Model loading, audio capture (sounddevice callback), transcription
- **Thread safety**: All shared state protected by `threading.Lock`

### Application Flow
1. `main.py` parses CLI args, creates `MurmurApp`
2. `app.py` shows overlay, loads model in background, sets up hotkey handler
3. On hotkey press: start recording (state → RECORDING)
4. On hotkey release: stop recording, transcribe async (state → TRANSCRIBING), paste result

### Module Responsibilities
- **app.py**: `MurmurApp` orchestrates all components, manages state
- **audio.py**: `AudioRecorder` captures audio via sounddevice callback into thread-safe buffer
- **transcribe.py**: `Transcriber` wraps parakeet-mlx, lazy-loads model
- **hotkey.py**: `HotkeyHandler` uses pynput for global keyboard monitoring
- **overlay.py**: `IndicatorWindow`/`IndicatorView` - native macOS floating UI with Quartz drawing
- **paste.py**: Clipboard manipulation and Cmd+V simulation
- **settings.py**: Config management (`~/.config/murmur/config.json`), native settings window

## Code Style

- **Ruff config**: Line length 100, Python 3.10 target
- **Lint rules**: E, F, I (isort), N (naming), W
- Type hints throughout (using `from __future__ import annotations`)
- Docstrings on all classes and public functions

## macOS-Specific Considerations

- Uses PyObjC extensively (AppKit, Quartz) - macOS only
- Requires permissions: Microphone, Accessibility, Input Monitoring
- UI updates must happen on main thread via `performSelectorOnMainThread_`
- Event loop is macOS NSRunLoop, not Python asyncio
