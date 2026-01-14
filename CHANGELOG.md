# Changelog

All notable changes to Murmur will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release preparation
- GitHub Actions CI/CD workflows
- Contributing guidelines
- Comprehensive test suite

## [0.1.0] - 2025-01-14

### Added
- Real-time speech-to-text transcription using Parakeet-MLX
- Global hotkey support (default: Cmd+Shift+Space)
- Menu bar application with status indicator
- Visual overlay bar showing recording/transcribing state
- Automatic paste of transcribed text into active application
- Settings window for customizing:
  - Hotkey configuration
  - Model selection
  - Audio input device
- Command-line interface with options:
  - `--hotkey` for custom hotkey
  - `--model` for model selection
  - `--list-devices` to list audio devices

### Technical
- Thread-safe audio capture using sounddevice
- Native macOS UI using PyObjC (AppKit/Quartz)
- Lazy model loading for fast startup
- Support for Python 3.10, 3.11, and 3.12

[Unreleased]: https://github.com/FujiwaraChoki/murmur/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/FujiwaraChoki/murmur/releases/tag/v0.1.0
