"""Update checker module for Murmur."""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of an update check."""

    available: bool
    latest_version: str
    release_url: str
    release_notes: str | None = None


class UpdateChecker:
    """Checks for updates from GitHub releases."""

    GITHUB_API_URL = "https://api.github.com/repos/FujiwaraChoki/murmur/releases/latest"
    TIMEOUT_SECONDS = 5

    def __init__(self):
        """Initialize the update checker."""
        self._last_result: UpdateResult | None = None

    def get_current_version(self) -> str:
        """Get the current installed version.

        Returns:
            Current version string.
        """
        from murmur import __version__

        return __version__

    def _parse_version(self, version_str: str) -> tuple[int, ...]:
        """Parse a version string into comparable tuple.

        Handles version strings with or without 'v' prefix.

        Args:
            version_str: Version string like "0.1.0" or "v0.1.0"

        Returns:
            Tuple of version components.
        """
        clean = version_str.strip().lstrip("vV")
        if not clean:
            return (0,)

        # Ignore prerelease/build metadata (e.g. 1.2.3-beta.1, 1.2.3+build5).
        clean = clean.split("-", 1)[0].split("+", 1)[0]

        parts: list[int] = []
        for segment in clean.split("."):
            match = re.match(r"(\d+)", segment)
            if not match:
                break
            parts.append(int(match.group(1)))

        return tuple(parts) if parts else (0,)

    def _is_newer(self, current: str, latest: str) -> bool:
        """Compare two version strings.

        Args:
            current: Current version string.
            latest: Latest version string from GitHub.

        Returns:
            True if latest is newer than current.
        """
        current_parts = self._parse_version(current)
        latest_parts = self._parse_version(latest)
        width = max(len(current_parts), len(latest_parts))
        current_norm = current_parts + (0,) * (width - len(current_parts))
        latest_norm = latest_parts + (0,) * (width - len(latest_parts))
        return latest_norm > current_norm

    def check_for_update(self) -> UpdateResult | None:
        """Check GitHub releases for a newer version.

        Returns:
            UpdateResult if check succeeded, None on error.
        """
        try:
            request = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Murmur-UpdateChecker",
                },
            )

            with urllib.request.urlopen(request, timeout=self.TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            html_url = data.get("html_url", "")
            body = data.get("body", "")

            current = self.get_current_version()
            is_newer = self._is_newer(current, tag_name)

            # Strip 'v' prefix for display
            display_version = tag_name.lstrip("v")

            result = UpdateResult(
                available=is_newer,
                latest_version=display_version,
                release_url=html_url,
                release_notes=body if body else None,
            )

            self._last_result = result
            return result

        except urllib.error.URLError as e:
            logger.warning(f"Network error checking for updates: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid response from GitHub API: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error checking for updates: {e}")
            return None

    @property
    def last_result(self) -> UpdateResult | None:
        """Get the last update check result."""
        return self._last_result
