"""Role definitions for the SDLC pipeline."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceRule:
    name: str
    pattern: str
    description: str


@dataclass(frozen=True)
class RoleContract:
    role_key: str
    profile: str
    required_sections: tuple[str, ...]
    evidence_rules: tuple[EvidenceRule, ...]


Roles: dict[str, RoleContract] = {
    "pm": RoleContract(
        role_key="pm",
        profile="pm-agent",
        required_sections=(
            "Problem",
            "Target user",
            "MVP scope",
            "Non-goals",
            "User stories",
            "Acceptance criteria",
            "Risks & assumptions",
            "Definition of done",
        ),
        evidence_rules=(),
    ),
    "ux": RoleContract(
        role_key="ux",
        profile="ux-designer-agent",
        required_sections=(
            "User journey",
            "Page/screen list",
            "Wireframe descriptions",
            "Accessibility notes",
        ),
        evidence_rules=(),
    ),
    "architect": RoleContract(
        role_key="architect",
        profile="architect-agent",
        required_sections=(
            "System architecture",
            "Data model",
            "API/interface boundaries",
            "Module structure",
            "Tech choices",
            "Security considerations",
            "Test strategy",
            "Implementation task split",
        ),
        evidence_rules=(),
    ),
    "junior-dev": RoleContract(
        role_key="junior-dev",
        profile="junior-dev-agent",
        required_sections=(
            "Known limitations",
            "Changed files",
        ),
        evidence_rules=(
            EvidenceRule(
                name="test command output block",
                pattern=r"```[\s\S]*?```",
                description="Output of test command must appear in a fenced code block",
            ),
        ),
    ),
    "senior-dev": RoleContract(
        role_key="senior-dev",
        profile="senior-dev-reviewer",
        required_sections=(
            "Verdict",
            "Issues",
            "Required fixes",
        ),
        evidence_rules=(
            EvidenceRule(
                name="file:line citation",
                pattern=r"\w[\w./\-]*\.\w+:\d+",
                description=(
                    "At least one file:line citation required (e.g. src/foo.py:42)"
                ),
            ),
        ),
    ),
    "junior-qa": RoleContract(
        role_key="junior-qa",
        profile="junior-qa-agent",
        required_sections=(
            "Test plan",
            "Defect list",
        ),
        evidence_rules=(
            EvidenceRule(
                name="command output block",
                pattern=r"```[\s\S]*?```",
                description="Command output must appear in a fenced code block",
            ),
        ),
    ),
    "senior-qa": RoleContract(
        role_key="senior-qa",
        profile="senior-qa-agent",
        required_sections=(
            "Coverage audit",
            "Gaps",
            "Risk level",
        ),
        evidence_rules=(
            EvidenceRule(
                name="ship/no-ship line",
                pattern=r"(?i)(ship|no.ship)",
                description="Explicit ship or no-ship verdict line required",
            ),
        ),
    ),
    "release": RoleContract(
        role_key="release",
        profile="release-agent",
        required_sections=(
            "What was built",
            "How to run",
            "How to test",
            "Changed files",
            "Known limitations",
            "Next steps",
        ),
        evidence_rules=(
            EvidenceRule(
                name="run command",
                pattern=r"`[^`]+`",
                description="A run command must appear inline-coded or in a code block",
            ),
        ),
    ),
}


def get_role(role_key: str) -> RoleContract:
    """Return the RoleContract for the given role_key.

    Raises KeyError for an unknown role_key.
    """
    return Roles[role_key]
