"""Tests for the updater module."""

from __future__ import annotations


class TestVersionParsing:
    """Tests for version parsing and comparison."""

    def test_parse_version_handles_v_prefix(self):
        """Versions with 'v' prefix parse correctly."""
        from murmur.updater import UpdateChecker

        checker = UpdateChecker()
        assert checker._parse_version("v1.2.3") == (1, 2, 3)

    def test_parse_version_handles_prerelease_suffix(self):
        """Prerelease/build suffixes don't break numeric parsing."""
        from murmur.updater import UpdateChecker

        checker = UpdateChecker()
        assert checker._parse_version("v1.2.3-beta.1") == (1, 2, 3)

    def test_is_newer_treats_missing_patch_as_equal(self):
        """1.2 and 1.2.0 are treated as equivalent."""
        from murmur.updater import UpdateChecker

        checker = UpdateChecker()
        assert checker._is_newer("1.2", "1.2.0") is False
        assert checker._is_newer("1.2.0", "1.2") is False

    def test_is_newer_detects_actual_update(self):
        """Higher patch/minor versions are detected."""
        from murmur.updater import UpdateChecker

        checker = UpdateChecker()
        assert checker._is_newer("1.2.3", "1.2.4") is True
        assert checker._is_newer("1.2.3", "1.3.0") is True
