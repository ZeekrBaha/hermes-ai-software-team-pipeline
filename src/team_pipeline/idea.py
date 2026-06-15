"""Product idea parsing."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


class EmptyIdeaError(ValueError):
    """Raised when the idea text is empty or whitespace-only."""


@dataclass(frozen=True)
class IdeaRecord:
    title: str
    slug: str
    one_line: str
    repo_path: Path | None


def _make_slug(text: str) -> str:
    """Convert text to a kebab-case ASCII slug, max 40 chars, word-boundary cut."""
    # Transliterate unicode via NFKD + ASCII encoding
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", errors="ignore").decode("ascii")

    # Lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")

    # Truncate at word boundary (on a hyphen) to <= 40 chars
    if len(slug) > 40:
        truncated = slug[:40]
        # Walk back to the last hyphen to avoid splitting a word
        last_hyphen = truncated.rfind("-")
        if last_hyphen != -1:
            truncated = truncated[:last_hyphen]
        slug = truncated.rstrip("-")

    if not slug:
        raise EmptyIdeaError(
            "Title produces an empty slug after ASCII transliteration."
        )

    return slug


def normalize_string(raw: str, *, repo_path: Path | None = None) -> IdeaRecord:
    """Parse a raw idea string into an IdeaRecord."""
    stripped = raw.strip()
    if not stripped:
        raise EmptyIdeaError("Idea text must not be empty.")

    first_line = stripped.splitlines()[0].strip()
    title = first_line
    one_line = first_line
    slug = _make_slug(title)

    return IdeaRecord(title=title, slug=slug, one_line=one_line, repo_path=repo_path)


def normalize_file(path: Path, *, repo_path: Path | None = None) -> IdeaRecord:
    """Parse a markdown idea file into an IdeaRecord."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    title: str | None = None
    one_line: str | None = None

    # Pass 1: look for a blockquote pitch anywhere in the file.
    # This ensures a blockquote wins over prose that appears before it.
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("> "):
            one_line = stripped[2:].strip()
            break

    # Pass 2: extract H1 title and (when no blockquote found) first prose line.
    for line in lines:
        stripped = line.strip()

        # Extract H1 as title (first occurrence)
        if title is None and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue

        # First non-heading, non-blank, non-blockquote line as one_line fallback
        if (
            one_line is None
            and stripped
            and not stripped.startswith("#")
            and not stripped.startswith("> ")
        ):
            one_line = stripped

    # Fallback: use first non-blank line as title if no H1 found
    if title is None:
        for line in lines:
            stripped = line.strip()
            if stripped:
                title = stripped.lstrip("#").strip()
                break

    if title is None:
        raise EmptyIdeaError("No title found in idea file.")

    if one_line is None:
        one_line = title

    slug = _make_slug(title)
    return IdeaRecord(title=title, slug=slug, one_line=one_line, repo_path=repo_path)
