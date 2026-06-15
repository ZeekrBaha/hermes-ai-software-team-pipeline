"""Jinja2 template rendering."""
from __future__ import annotations

from pathlib import Path

import jinja2

from team_pipeline.idea import IdeaRecord

# Map role key → template filename
_ROLE_TEMPLATES: dict[str, str] = {
    "pm": "pm_spec.md.j2",
    "ux": "ux_design.md.j2",
    "architect": "architecture.md.j2",
    "junior-dev": "impl_task.md.j2",
    "senior-dev": "senior_dev_review.md.j2",
    "junior-qa": "junior_qa_report.md.j2",
    "senior-qa": "senior_qa_audit.md.j2",
    "release": "handoff.md.j2",
}

# Resolve templates/ directory relative to this file's package root.
# src/team_pipeline/templates.py → project root is two levels up.
_TEMPLATES_DIR: Path = Path(__file__).parent.parent.parent / "templates"

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=False,
    keep_trailing_newline=True,
)


def render(role: str, idea: IdeaRecord) -> str:
    """Render the Jinja2 template for ``role`` with the given idea context.

    ``role`` maps to a template filename:
        pm → pm_spec.md.j2, ux → ux_design.md.j2, etc.

    Raises:
        ValueError: when ``role`` is not a known role key.

    Returns:
        Rendered markdown string.
    """
    if role not in _ROLE_TEMPLATES:
        raise ValueError(
            f"{role!r} is not a valid role. Valid keys: {sorted(_ROLE_TEMPLATES)}"
        )
    template = _env.get_template(_ROLE_TEMPLATES[role])
    return template.render(idea=idea)
