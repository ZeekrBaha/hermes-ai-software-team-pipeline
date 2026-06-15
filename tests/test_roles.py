"""Tests for roles.py — RoleContract registry (T3)."""
from __future__ import annotations

import re

import pytest

from team_pipeline.roles import EvidenceRule, RoleContract, Roles, get_role

EXPECTED_ROLE_KEYS = {
    "pm",
    "ux",
    "architect",
    "junior-dev",
    "senior-dev",
    "junior-qa",
    "senior-qa",
    "release",
}

EXPECTED_PROFILES = {
    "pm": "pm-agent",
    "ux": "ux-designer-agent",
    "architect": "architect-agent",
    "junior-dev": "junior-dev-agent",
    "senior-dev": "senior-dev-reviewer",
    "junior-qa": "junior-qa-agent",
    "senior-qa": "senior-qa-agent",
    "release": "release-agent",
}


class TestRolesRegistry:
    def test_roles_has_exactly_8_keys(self) -> None:
        assert len(Roles) == 8

    def test_all_8_role_keys_present(self) -> None:
        assert set(Roles.keys()) == EXPECTED_ROLE_KEYS

    def test_every_value_is_role_contract(self) -> None:
        for key, contract in Roles.items():
            assert isinstance(contract, RoleContract), f"{key} is not a RoleContract"

    def test_every_contract_has_non_empty_required_sections(self) -> None:
        for key, contract in Roles.items():
            assert len(contract.required_sections) > 0, (
                f"{key} has empty required_sections"
            )

    def test_all_8_profiles_match_expected(self) -> None:
        for role_key, expected_profile in EXPECTED_PROFILES.items():
            assert Roles[role_key].profile == expected_profile, (
                f"{role_key}: expected profile {expected_profile!r}, "
                f"got {Roles[role_key].profile!r}"
            )


class TestPmContract:
    def setup_method(self) -> None:
        self.contract = Roles["pm"]

    def test_pm_role_key(self) -> None:
        assert self.contract.role_key == "pm"

    def test_pm_has_problem_section(self) -> None:
        assert "Problem" in self.contract.required_sections

    def test_pm_has_definition_of_done_section(self) -> None:
        assert "Definition of done" in self.contract.required_sections

    def test_pm_has_all_required_sections(self) -> None:
        expected = {
            "Problem",
            "Target user",
            "MVP scope",
            "Non-goals",
            "User stories",
            "Acceptance criteria",
            "Risks & assumptions",
            "Definition of done",
        }
        assert expected.issubset(set(self.contract.required_sections))

    def test_pm_has_no_evidence_rules(self) -> None:
        assert self.contract.evidence_rules == ()


class TestSeniorDevContract:
    def setup_method(self) -> None:
        self.contract = Roles["senior-dev"]

    def test_senior_dev_has_verdict_section(self) -> None:
        assert "Verdict" in self.contract.required_sections

    def test_senior_dev_has_issues_section(self) -> None:
        assert "Issues" in self.contract.required_sections

    def test_senior_dev_has_required_fixes_section(self) -> None:
        assert "Required fixes" in self.contract.required_sections

    def test_senior_dev_has_file_line_evidence_rule(self) -> None:
        assert len(self.contract.evidence_rules) > 0, (
            "senior-dev must have at least one evidence rule"
        )

    def test_senior_dev_file_line_pattern_matches_typical_citation(self) -> None:
        """Pattern must match a citation like 'src/foo.py:42'."""
        rule = self.contract.evidence_rules[0]
        assert re.search(rule.pattern, "src/foo.py:42"), (
            f"Pattern {rule.pattern!r} should match 'src/foo.py:42'"
        )

    def test_senior_dev_file_line_pattern_has_word_colon_digit(self) -> None:
        """Pattern must contain \\w, ':', and \\d (or equivalents)."""
        rule = self.contract.evidence_rules[0]
        # Pattern should match file:line style — verify structural components
        assert re.search(rule.pattern, "utils.py:10")

    def test_senior_dev_evidence_rule_has_name_and_description(self) -> None:
        rule = self.contract.evidence_rules[0]
        assert rule.name
        assert rule.description


class TestJuniorQaContract:
    def setup_method(self) -> None:
        self.contract = Roles["junior-qa"]

    def test_junior_qa_has_test_plan_section(self) -> None:
        assert "Test plan" in self.contract.required_sections

    def test_junior_qa_has_defect_list_section(self) -> None:
        assert "Defect list" in self.contract.required_sections

    def test_junior_qa_has_command_output_evidence_rule(self) -> None:
        assert len(self.contract.evidence_rules) > 0, (
            "junior-qa must have at least one evidence rule"
        )

    def test_junior_qa_command_output_pattern_matches_code_block(self) -> None:
        """Pattern must match a fenced code block like ```...```."""
        rule = self.contract.evidence_rules[0]
        sample = "```\npytest output here\n```"
        assert re.search(rule.pattern, sample, re.DOTALL), (
            f"Pattern {rule.pattern!r} should match a fenced code block"
        )


class TestGetRole:
    def test_get_role_returns_pm_contract(self) -> None:
        contract = get_role("pm")
        assert isinstance(contract, RoleContract)
        assert contract.role_key == "pm"

    def test_get_role_returns_correct_contract_for_each_key(self) -> None:
        for key in EXPECTED_ROLE_KEYS:
            contract = get_role(key)
            assert contract.role_key == key

    def test_get_role_raises_key_error_for_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_role("nonexistent")

    def test_get_role_raises_key_error_for_empty_string(self) -> None:
        with pytest.raises(KeyError):
            get_role("")


class TestEvidenceRule:
    def test_evidence_rule_is_frozen(self) -> None:
        rule = EvidenceRule(
            name="test",
            pattern=r"\w+:\d+",
            description="test rule",
        )
        with pytest.raises(AttributeError):
            rule.name = "changed"  # type: ignore[misc]

    def test_role_contract_is_frozen(self) -> None:
        contract = RoleContract(
            role_key="test",
            profile="test-agent",
            required_sections=("Section A",),
            evidence_rules=(),
        )
        with pytest.raises(AttributeError):
            contract.role_key = "changed"  # type: ignore[misc]
