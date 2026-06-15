"""Tests for idea.py — IdeaRecord + normalize (T1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from team_pipeline.idea import (
    EmptyIdeaError,
    IdeaRecord,
    normalize_file,
    normalize_string,
)


class TestNormalizeString:
    def test_basic_string_returns_idea_record(self) -> None:
        record = normalize_string("Build Prompt Regression Lab")
        assert isinstance(record, IdeaRecord)
        assert record.title == "Build Prompt Regression Lab"
        assert record.slug == "build-prompt-regression-lab"
        assert record.one_line == "Build Prompt Regression Lab"
        assert record.repo_path is None

    def test_empty_string_raises(self) -> None:
        with pytest.raises(EmptyIdeaError):
            normalize_string("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyIdeaError):
            normalize_string("   ")

    def test_slug_is_lowercase(self) -> None:
        record = normalize_string("Build Prompt Regression Lab")
        assert record.slug == record.slug.lower()

    def test_slug_has_no_spaces(self) -> None:
        record = normalize_string("Build Prompt Regression Lab")
        assert " " not in record.slug

    def test_slug_is_kebab_case(self) -> None:
        record = normalize_string("Build Prompt Regression Lab")
        assert record.slug == "build-prompt-regression-lab"

    def test_slug_max_40_chars(self) -> None:
        long_title = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa"
        record = normalize_string(long_title)
        assert len(record.slug) <= 40
        assert record.slug == "alpha-beta-gamma-delta-epsilon-zeta-eta"

    def test_slug_truncates_at_word_boundary(self) -> None:
        long_title = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa"
        record = normalize_string(long_title)
        assert record.slug == "alpha-beta-gamma-delta-epsilon-zeta-eta"
        assert len(record.slug) <= 40
        assert not record.slug.endswith("-")

    def test_slug_ascii_only_unicode_input(self) -> None:
        record = normalize_string("Build Ünïcödé Thïng")
        assert record.slug.isascii()
        assert len(record.slug) > 0

    def test_slug_non_ascii_transliterated(self) -> None:
        record = normalize_string("Build Ünïcödé Thïng")
        # Diacritics stripped via NFKD; base letters survive
        assert record.slug == "build-unicode-thing"

    def test_slug_all_cjk_raises(self) -> None:
        with pytest.raises(EmptyIdeaError):
            normalize_string("你好世界")

    def test_repo_path_stored(self) -> None:
        p = Path("/some/path")
        record = normalize_string("My Idea", repo_path=p)
        assert record.repo_path == p

    def test_multiline_uses_first_line_as_title(self) -> None:
        record = normalize_string("First Line\nSecond line details.")
        assert record.title == "First Line"
        assert record.one_line == "First Line"


class TestNormalizeFile:
    def test_h1_title_extracted(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text(
            "# Build Prompt Regression Lab\n\nThis is the description.\n"
        )
        record = normalize_file(idea_md)
        assert record.title == "Build Prompt Regression Lab"

    def test_slug_from_h1(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("# Build Prompt Regression Lab\n\nDescription.\n")
        record = normalize_file(idea_md)
        assert record.slug == "build-prompt-regression-lab"

    def test_one_line_from_first_non_heading_non_blank(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("# My Product Idea\n\nFirst real line here.\nSecond line.\n")
        record = normalize_file(idea_md)
        assert record.one_line == "First real line here."

    def test_pitch_block_used_as_one_line(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("# My Product\n\n> This is the pitch.\n\nMore text.\n")
        record = normalize_file(idea_md)
        assert record.one_line == "This is the pitch."

    def test_fallback_no_h1_uses_first_line_as_title(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("Build Prompt Regression Lab\n\nSome details.\n")
        record = normalize_file(idea_md)
        assert record.title == "Build Prompt Regression Lab"

    def test_repo_path_stored_in_file_mode(self, tmp_path: Path) -> None:
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("# My Idea\n\nDetails.\n")
        p = Path("/some/repo")
        record = normalize_file(idea_md, repo_path=p)
        assert record.repo_path == p

    def test_blockquote_wins_over_prose_before_it(self, tmp_path: Path) -> None:
        """Bug 1: prose appearing before the blockquote must not shadow it."""
        idea_md = tmp_path / "idea.md"
        idea_md.write_text(
            "# My Product\n\nSome prose before the pitch.\n\n> The real pitch.\n"
        )
        record = normalize_file(idea_md)
        assert record.one_line == "The real pitch."

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        """Minor #7: an empty file should raise EmptyIdeaError."""
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("")
        with pytest.raises(EmptyIdeaError):
            normalize_file(idea_md)

    def test_h1_only_file_one_line_equals_title(self, tmp_path: Path) -> None:
        """Minor #8: file with only an H1 and no body — one_line falls back to title."""
        idea_md = tmp_path / "idea.md"
        idea_md.write_text("# Just A Title\n")
        record = normalize_file(idea_md)
        assert record.one_line == record.title == "Just A Title"
