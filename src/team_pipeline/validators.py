"""Artifact validators for the SDLC pipeline — T5."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from team_pipeline.roles import ROLES


@dataclass
class ValidationResult:
    ok: bool
    role: str
    missing: list[str] = field(default_factory=list)
    evidence_failures: list[str] = field(default_factory=list)


def validate(artifact_text: str, role: str) -> ValidationResult:
    """Validate artifact_text against the contract for role.

    Returns ValidationResult with ok=True if all required sections are present
    and all evidence rules match.

    Raises ValueError for an unknown role.
    """
    if role not in ROLES:
        raise ValueError(
            f"{role!r} is not a valid role. Valid keys: {sorted(ROLES)}"
        )

    contract = ROLES[role]

    # Extract section headings: lines starting with '#'.
    # Strip leading '#' chars and whitespace, compare case-insensitively.
    headings: set[str] = set()
    for line in artifact_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip().lower()
            if heading_text:
                headings.add(heading_text)

    missing: list[str] = [
        section
        for section in contract.required_sections
        if section.lower() not in headings
    ]

    evidence_failures: list[str] = [
        rule.name
        for rule in contract.evidence_rules
        if not re.search(rule.pattern, artifact_text)
    ]

    return ValidationResult(
        ok=not missing and not evidence_failures,
        role=role,
        missing=missing,
        evidence_failures=evidence_failures,
    )
