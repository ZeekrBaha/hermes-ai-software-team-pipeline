"""Environment diagnostics — preflight checks for the team pipeline (FR11, US6)."""
from __future__ import annotations

from dataclasses import dataclass, field

from team_pipeline.kanban_client import HermesError, KanbanClient

# ---------------------------------------------------------------------------
# Required profiles
# ---------------------------------------------------------------------------

REQUIRED_PROFILES: list[str] = [
    "pm-agent",
    "ux-designer-agent",
    "architect-agent",
    "junior-dev-agent",
    "senior-dev-reviewer",
    "junior-qa-agent",
    "senior-qa-agent",
    "release-agent",
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DoctorResult:
    hermes_present: bool
    hermes_version: str | None      # e.g. "Hermes Agent v0.16.0 (2026.6.5)"
    missing_profiles: list[str] = field(default_factory=list)
    ok: bool = False


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def run_doctor(client: KanbanClient) -> DoctorResult:
    """Run preflight checks using the given client.

    - Calls client.version() to get the hermes version string.
      If that raises HermesError, hermes is absent.
    - Calls client.assignees() to discover available profiles.
    - Computes missing_profiles = REQUIRED_PROFILES − found_profiles.
    - ok is True only when hermes is present AND no profiles are missing.
    """
    # --- version check ---
    try:
        hermes_version = client.version()
        hermes_present = True
    except HermesError:
        hermes_present = False
        hermes_version = None

    # --- profile check ---
    if hermes_present:
        found = set(client.assignees())
        missing_profiles = [p for p in REQUIRED_PROFILES if p not in found]
    else:
        # Cannot query assignees without hermes; report all as missing.
        missing_profiles = list(REQUIRED_PROFILES)

    ok = hermes_present and not missing_profiles

    return DoctorResult(
        hermes_present=hermes_present,
        hermes_version=hermes_version,
        missing_profiles=missing_profiles,
        ok=ok,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_doctor_result(result: DoctorResult) -> str:
    """Format DoctorResult as a human-readable checklist string."""
    lines: list[str] = []

    # --- hermes version line ---
    if result.hermes_present:
        lines.append(f"✓ hermes installed: {result.hermes_version}")
    else:
        lines.append("✗ hermes not found — install hermes and re-run")

    # --- profile lines ---
    if not result.missing_profiles:
        lines.append("✓ all required profiles present")
    else:
        lines.append(f"✗ missing profiles ({len(result.missing_profiles)}):")
        for profile in result.missing_profiles:
            lines.append(f"    - {profile}")

    # --- overall verdict ---
    verdict = "PASS" if result.ok else "FAIL"
    lines.append(f"\nOverall: {verdict}")

    return "\n".join(lines)
