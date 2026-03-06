"""Snippet expansion helpers for user-configured dictation shortcuts."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

SnippetConfig = dict[str, str]


def normalize_snippets(snippets: Iterable[Mapping[str, object]] | None) -> list[SnippetConfig]:
    """Clean and normalize snippet configuration data.

    Empty triggers are discarded. Triggers and replacements are coerced to strings
    so partially-invalid config files do not crash the app.
    """
    normalized: list[SnippetConfig] = []
    if snippets is None:
        return normalized

    for snippet in snippets:
        if not isinstance(snippet, Mapping):
            continue

        trigger = str(snippet.get("trigger", "")).strip()
        if not trigger:
            continue

        replacement = str(snippet.get("replacement", ""))
        normalized.append({"trigger": trigger, "replacement": replacement})

    return normalized


def expand_snippets(text: str, snippets: Iterable[Mapping[str, object]] | None) -> str:
    """Apply user-defined snippet replacements to transcribed text."""
    normalized = normalize_snippets(snippets)
    if not text or not normalized:
        return text

    replacements: dict[str, str] = {}
    patterns: list[str] = []

    for snippet in sorted(normalized, key=lambda item: len(item["trigger"]), reverse=True):
        trigger = snippet["trigger"]
        replacements[trigger.casefold()] = snippet["replacement"]
        patterns.append(_trigger_pattern(trigger))

    combined_pattern = re.compile("|".join(patterns), re.IGNORECASE)
    return combined_pattern.sub(
        lambda match: replacements[match.group(0).casefold()],
        text,
    )


def _trigger_pattern(trigger: str) -> str:
    """Build a regex pattern that matches a trigger as a standalone phrase."""
    escaped = re.escape(trigger)

    if trigger and (trigger[0].isalnum() or trigger[0] == "_"):
        escaped = rf"(?<!\w){escaped}"
    if trigger and (trigger[-1].isalnum() or trigger[-1] == "_"):
        escaped = rf"{escaped}(?!\w)"

    return escaped
