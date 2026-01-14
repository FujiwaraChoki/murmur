# Contributing to Murmur

Thank you for your interest in contributing to Murmur! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- macOS (required - Murmur uses macOS-specific APIs)
- Python 3.10 or higher
- Git

### Setting Up Your Development Environment

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/murmur.git
   cd murmur
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in development mode**

   ```bash
   pip install -e ".[dev]"
   ```

4. **Grant required permissions**

   Murmur requires macOS permissions for:
   - Microphone access
   - Accessibility (for paste simulation)
   - Input Monitoring (for global hotkeys)

## Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting.

### Before Committing

```bash
# Check formatting
ruff format --check murmur/

# Auto-format code
ruff format murmur/

# Run linter
ruff check murmur/

# Auto-fix linting issues
ruff check --fix murmur/
```

### Style Guidelines

- **Line length**: 100 characters maximum
- **Type hints**: Required for all function signatures
- **Docstrings**: Required for all public classes and functions
- **Imports**: Sorted by isort (handled by Ruff)

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_audio.py

# Run with coverage
pytest --cov=murmur --cov-report=term-missing
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names that explain what is being tested
- Mock macOS-specific APIs when possible for faster tests

## Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

   - Write clear, concise commit messages
   - Keep commits focused and atomic
   - Add tests for new functionality
   - Update documentation if needed

3. **Ensure quality**

   ```bash
   ruff format murmur/
   ruff check murmur/
   pytest
   ```

4. **Push and create PR**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a Pull Request on GitHub.

### PR Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what changes you made and why
- **Link issues**: Reference any related issues with `Fixes #123` or `Relates to #123`
- **Small PRs**: Prefer smaller, focused PRs over large changes
- **Screenshots**: Include screenshots/recordings for UI changes

## Architecture Overview

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

### Key Concepts

- **Threading Model**: Main thread runs NSRunLoop; background threads handle audio/transcription
- **State Machine**: App states are IDLE → RECORDING → TRANSCRIBING → IDLE
- **Thread Safety**: All shared state uses `threading.Lock`

### Module Structure

| Module | Responsibility |
|--------|----------------|
| `app.py` | Main application orchestration |
| `audio.py` | Audio capture via sounddevice |
| `transcribe.py` | ML model interface (parakeet-mlx) |
| `hotkey.py` | Global keyboard monitoring |
| `overlay.py` | Native macOS floating UI |
| `paste.py` | Clipboard and paste simulation |
| `settings.py` | Configuration management |
| `main.py` | CLI entry point |

## Reporting Issues

### Bug Reports

Include:
- macOS version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs if any

### Feature Requests

Include:
- Clear description of the feature
- Use case / why it would be useful
- Any implementation ideas (optional)

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Security**: See [SECURITY.md](SECURITY.md) (if you find a security vulnerability, please report it privately)

## License

By contributing to Murmur, you agree that your contributions will be licensed under the MIT License.
