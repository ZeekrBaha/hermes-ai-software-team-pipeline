"""Tests for validators.py — T5 (RED first)."""
from __future__ import annotations

import pytest

from team_pipeline.validators import validate

# ── Fixtures / sample artifacts ────────────────────────────────────────────────

PM_FULL = """\
## Problem
We need to solve a real user pain point.

## Target user
Software developers working on multi-agent pipelines.

## MVP scope
Core pipeline: PM → senior-dev → junior-dev flow.

## Non-goals
No mobile app, no analytics dashboard.

## User stories
As a developer, I want an automated pipeline so I can ship faster.

## Acceptance criteria
All 8 roles produce valid artifacts.

## Risks & assumptions
Assuming LLM APIs remain stable.

## Definition of done
All tests pass with 100% coverage on validators.
"""

PM_MISSING_NONGOALS = """\
## Problem
We need to solve a real user pain point.

## Target user
Software developers working on multi-agent pipelines.

## MVP scope
Core pipeline only.

## User stories
As a developer, I want an automated pipeline.

## Acceptance criteria
All roles produce valid artifacts.

## Risks & assumptions
Assuming LLM APIs remain stable.

## Definition of done
All tests pass.
"""

PM_NO_SECTIONS = "This is just plain text with no headings at all."

SENIOR_DEV_FULL = """\
## Verdict
Approved with minor fixes required.

## Issues
- src/validators.py:42 — missing null check
- tests/test_validators.py:10 — fixture not isolated

## Required fixes
Fix null guard at src/validators.py:42 before merging.
"""

SENIOR_DEV_NO_FILE_LINE = """\
## Verdict
Approved with minor fixes required.

## Issues
There are some issues to address.

## Required fixes
Fix the issues before merging.
"""

JUNIOR_QA_FULL = """\
## Test plan
1. Run unit tests
2. Run integration tests

## Defect list
No defects found.

```
$ pytest tests/ -v
PASSED 42 tests
```
"""

JUNIOR_QA_NO_CODE_BLOCK = """\
## Test plan
1. Run unit tests
2. Run integration tests

## Defect list
No defects found. All tests passed manually.
"""

JUNIOR_DEV_FULL = """\
## Known limitations
This is an MVP; no streaming support yet.

## Changed files
- src/team_pipeline/validators.py
- tests/test_validators.py

```
$ pytest tests/ -v
collected 42 items
PASSED
```
"""

JUNIOR_DEV_NO_EVIDENCE = """\
## Known limitations
This is an MVP.

## Changed files
See PR description.
"""


# ── PM tests ───────────────────────────────────────────────────────────────────

class TestPmValidation:
    def test_pm_full_artifact_ok(self) -> None:
        result = validate(PM_FULL, "pm")
        assert result.ok is True
        assert result.missing == []
        assert result.evidence_failures == []

    def test_pm_missing_nongoals_ok_false(self) -> None:
        result = validate(PM_MISSING_NONGOALS, "pm")
        assert result.ok is False
        assert "Non-goals" in result.missing

    def test_pm_no_sections_fails_with_all_8_missing(self) -> None:
        result = validate(PM_NO_SECTIONS, "pm")
        assert result.ok is False
        assert len(result.missing) == 8

    def test_pm_role_field(self) -> None:
        result = validate(PM_FULL, "pm")
        assert result.role == "pm"

    def test_pm_empty_string_all_8_missing(self) -> None:
        result = validate("", "pm")
        assert result.ok is False
        assert len(result.missing) == 8


# ── senior-dev tests ───────────────────────────────────────────────────────────

class TestSeniorDevValidation:
    def test_senior_dev_full_ok(self) -> None:
        result = validate(SENIOR_DEV_FULL, "senior-dev")
        assert result.ok is True

    def test_senior_dev_no_file_line_fails(self) -> None:
        result = validate(SENIOR_DEV_NO_FILE_LINE, "senior-dev")
        assert result.ok is False
        assert len(result.evidence_failures) > 0

    def test_senior_dev_evidence_failure_name_is_file_line_citation(self) -> None:
        result = validate(SENIOR_DEV_NO_FILE_LINE, "senior-dev")
        assert "file:line citation" in result.evidence_failures


# ── junior-qa tests ────────────────────────────────────────────────────────────

class TestJuniorQaValidation:
    def test_junior_qa_with_fenced_block_ok(self) -> None:
        result = validate(JUNIOR_QA_FULL, "junior-qa")
        assert result.ok is True

    def test_junior_qa_no_fenced_block_fails(self) -> None:
        result = validate(JUNIOR_QA_NO_CODE_BLOCK, "junior-qa")
        assert result.ok is False
        assert len(result.evidence_failures) > 0


# ── junior-dev tests ───────────────────────────────────────────────────────────

class TestJuniorDevValidation:
    def test_junior_dev_full_ok(self) -> None:
        result = validate(JUNIOR_DEV_FULL, "junior-dev")
        assert result.ok is True

    def test_junior_dev_missing_evidence_fails(self) -> None:
        result = validate(JUNIOR_DEV_NO_EVIDENCE, "junior-dev")
        assert result.ok is False


# ── Edge cases ─────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_case_insensitive_section_matching(self) -> None:
        """Artifact using '## target USER' must match required section 'Target user'."""
        artifact = """\
## problem
Something.

## target USER
Developers.

## mvp scope
Core features.

## non-goals
None.

## user stories
Stories.

## acceptance criteria
Criteria.

## risks & assumptions
Risks.

## definition of done
Done.
"""
        result = validate(artifact, "pm")
        assert result.ok is True
        assert result.missing == []

    def test_unknown_role_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            validate("text", "nonexistent")

    def test_ok_false_when_section_missing_but_evidence_present(self) -> None:
        """ok must be False when a section is absent, even if evidence passes."""
        # senior-dev: file:line citation present but "Required fixes" section absent
        artifact = """\
## Verdict
Approved.

## Issues
See src/foo.py:42 for the bug.
"""
        result = validate(artifact, "senior-dev")
        assert result.ok is False
        assert "Required fixes" in result.missing
        # evidence_failures should be empty (file:line is present)
        assert result.evidence_failures == []

    def test_validation_result_dataclass_fields(self) -> None:
        """ValidationResult must expose ok, role, missing, evidence_failures."""
        result = validate(PM_FULL, "pm")
        assert hasattr(result, "ok")
        assert hasattr(result, "role")
        assert hasattr(result, "missing")
        assert hasattr(result, "evidence_failures")
