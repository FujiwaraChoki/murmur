"""Tests for snippet expansion helpers."""

from __future__ import annotations


class TestNormalizeSnippets:
    """Tests for config normalization."""

    def test_normalize_snippets_filters_empty_triggers(self):
        """Blank triggers are discarded."""
        from murmur.snippets import normalize_snippets

        snippets = normalize_snippets(
            [
                {"trigger": "  ", "replacement": "ignored"},
                {"trigger": "brb", "replacement": "be right back"},
            ]
        )

        assert snippets == [{"trigger": "brb", "replacement": "be right back"}]

    def test_normalize_snippets_coerces_values_to_strings(self):
        """Non-string values do not break config loading."""
        from murmur.snippets import normalize_snippets

        snippets = normalize_snippets([{"trigger": 123, "replacement": 456}])

        assert snippets == [{"trigger": "123", "replacement": "456"}]


class TestExpandSnippets:
    """Tests for phrase replacement."""

    def test_expand_snippets_replaces_phrase_case_insensitively(self):
        """Configured phrases are replaced regardless of spoken casing."""
        from murmur.snippets import expand_snippets

        result = expand_snippets(
            "Please add my email signature here.",
            [{"trigger": "My Email Signature", "replacement": "Best regards,\nChoki"}],
        )

        assert result == "Please add Best regards,\nChoki here."

    def test_expand_snippets_prefers_longer_matches(self):
        """Longer phrases win over shorter overlapping triggers."""
        from murmur.snippets import expand_snippets

        result = expand_snippets(
            "Let's use support email today.",
            [
                {"trigger": "support", "replacement": "help"},
                {"trigger": "support email", "replacement": "support@example.com"},
            ],
        )

        assert result == "Let's use support@example.com today."

    def test_expand_snippets_respects_word_boundaries(self):
        """Standalone triggers do not replace inside larger words."""
        from murmur.snippets import expand_snippets

        result = expand_snippets(
            "A catalog is not the same as a cat.",
            [{"trigger": "cat", "replacement": "dog"}],
        )

        assert result == "A catalog is not the same as a dog."
