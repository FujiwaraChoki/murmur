"""Convenience entry point for `uv run main.py` from the repo root."""

from __future__ import annotations

import sys

from murmur.main import main

if __name__ == "__main__":
    sys.exit(main())
