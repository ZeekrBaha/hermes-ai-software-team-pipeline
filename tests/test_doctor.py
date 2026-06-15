"""Tests for doctor.py — preflight checks (T10, FR11, US6, AC6.1)."""
from __future__ import annotations

from team_pipeline.doctor import (
    REQUIRED_PROFILES,
    DoctorResult,
    format_doctor_result,
    run_doctor,
)
from team_pipeline.kanban_client import FakeKanbanClient, HermesError

# ---------------------------------------------------------------------------
# Test double — extends FakeKanbanClient with configurable version/assignees
# ---------------------------------------------------------------------------


class FakeClientWith(FakeKanbanClient):
    """FakeKanbanClient subclass with configurable version/assignees."""

    def __init__(
        self,
        version_str: str = "Hermes Agent v0.16.0 (2026.6.5)",
        assignee_list: list[str] | None = None,
        raise_on_version: bool = False,
        raise_file_not_found: bool = False,
    ) -> None:
        super().__init__()
        self._version_str = version_str
        self._assignee_list = assignee_list if assignee_list is not None else []
        self._raise_on_version = raise_on_version
        self._raise_file_not_found = raise_file_not_found

    def version(self) -> str:
        if self._raise_file_not_found:
            raise FileNotFoundError("No such file or directory: 'hermes'")
        if self._raise_on_version:
            raise HermesError(
                cmd=["hermes", "--version"],
                returncode=127,
                stderr="hermes: command not found",
            )
        return self._version_str

    def assignees(self) -> list[str]:
        return self._assignee_list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_PROFILES = list(REQUIRED_PROFILES)


# ---------------------------------------------------------------------------
# REQUIRED_PROFILES constant
# ---------------------------------------------------------------------------


class TestRequiredProfiles:
    def test_required_profiles_is_list_of_strings(self) -> None:
        assert isinstance(REQUIRED_PROFILES, list)
        assert all(isinstance(p, str) for p in REQUIRED_PROFILES)

    def test_required_profiles_has_eight_entries(self) -> None:
        assert len(REQUIRED_PROFILES) == 8

    def test_required_profiles_contains_expected_names(self) -> None:
        expected = {
            "pm-agent",
            "ux-designer-agent",
            "architect-agent",
            "junior-dev-agent",
            "senior-dev-reviewer",
            "junior-qa-agent",
            "senior-qa-agent",
            "release-agent",
        }
        assert set(REQUIRED_PROFILES) == expected


# ---------------------------------------------------------------------------
# run_doctor — happy path
# ---------------------------------------------------------------------------


class TestRunDoctorHappy:
    def test_returns_doctor_result(self) -> None:
        client = FakeClientWith(assignee_list=ALL_PROFILES)
        result = run_doctor(client)
        assert isinstance(result, DoctorResult)

    def test_ok_true_when_all_profiles_present(self) -> None:
        client = FakeClientWith(assignee_list=ALL_PROFILES)
        result = run_doctor(client)
        assert result.ok is True

    def test_hermes_present_true(self) -> None:
        client = FakeClientWith(assignee_list=ALL_PROFILES)
        result = run_doctor(client)
        assert result.hermes_present is True

    def test_missing_profiles_empty(self) -> None:
        client = FakeClientWith(assignee_list=ALL_PROFILES)
        result = run_doctor(client)
        assert result.missing_profiles == []

    def test_hermes_version_captured(self) -> None:
        client = FakeClientWith(
            version_str="Hermes Agent v0.16.0 (2026.6.5)",
            assignee_list=ALL_PROFILES,
        )
        result = run_doctor(client)
        assert result.hermes_version == "Hermes Agent v0.16.0 (2026.6.5)"

    def test_extra_profiles_in_assignees_are_ignored(self) -> None:
        # Kanban may list more assignees than required; that's fine.
        client = FakeClientWith(
            assignee_list=ALL_PROFILES + ["some-extra-agent"],
        )
        result = run_doctor(client)
        assert result.ok is True
        assert result.missing_profiles == []


# ---------------------------------------------------------------------------
# run_doctor — missing profiles
# ---------------------------------------------------------------------------


class TestRunDoctorMissingProfiles:
    def test_ok_false_when_one_profile_missing(self) -> None:
        profiles_minus_one = [p for p in ALL_PROFILES if p != "junior-qa-agent"]
        client = FakeClientWith(assignee_list=profiles_minus_one)
        result = run_doctor(client)
        assert result.ok is False

    def test_missing_profile_name_reported(self) -> None:
        profiles_minus_one = [p for p in ALL_PROFILES if p != "junior-qa-agent"]
        client = FakeClientWith(assignee_list=profiles_minus_one)
        result = run_doctor(client)
        assert "junior-qa-agent" in result.missing_profiles

    def test_no_profiles_returns_all_eight_missing(self) -> None:
        client = FakeClientWith(assignee_list=[])
        result = run_doctor(client)
        assert result.ok is False
        assert set(result.missing_profiles) == set(REQUIRED_PROFILES)
        assert len(result.missing_profiles) == 8

    def test_ok_false_even_when_hermes_present(self) -> None:
        # hermes is installed but profiles are absent — ok must still be False
        client = FakeClientWith(
            version_str="Hermes Agent v0.16.0",
            assignee_list=[],
        )
        result = run_doctor(client)
        assert result.hermes_present is True
        assert result.ok is False


# ---------------------------------------------------------------------------
# run_doctor — hermes absent (version raises HermesError)
# ---------------------------------------------------------------------------


class TestRunDoctorHermesAbsent:
    def test_hermes_present_false(self) -> None:
        client = FakeClientWith(raise_on_version=True)
        result = run_doctor(client)
        assert result.hermes_present is False

    def test_ok_false(self) -> None:
        client = FakeClientWith(raise_on_version=True)
        result = run_doctor(client)
        assert result.ok is False

    def test_hermes_version_none(self) -> None:
        client = FakeClientWith(raise_on_version=True)
        result = run_doctor(client)
        assert result.hermes_version is None

    def test_all_profiles_reported_missing(self) -> None:
        # When hermes is absent we cannot call assignees; treat all as missing.
        client = FakeClientWith(raise_on_version=True)
        result = run_doctor(client)
        assert set(result.missing_profiles) == set(REQUIRED_PROFILES)


# ---------------------------------------------------------------------------
# run_doctor — hermes binary missing (FileNotFoundError from subprocess)
# ---------------------------------------------------------------------------


class TestRunDoctorFileNotFound:
    def test_hermes_present_false_on_file_not_found(self) -> None:
        """FileNotFoundError from version() must result in hermes_present=False."""
        client = FakeClientWith(raise_file_not_found=True)
        result = run_doctor(client)
        assert result.hermes_present is False

    def test_ok_false_on_file_not_found(self) -> None:
        """FileNotFoundError from version() must result in ok=False."""
        client = FakeClientWith(raise_file_not_found=True)
        result = run_doctor(client)
        assert result.ok is False

    def test_hermes_version_none_on_file_not_found(self) -> None:
        """hermes_version must be None when binary is missing."""
        client = FakeClientWith(raise_file_not_found=True)
        result = run_doctor(client)
        assert result.hermes_version is None


# ---------------------------------------------------------------------------
# format_doctor_result
# ---------------------------------------------------------------------------


class TestFormatDoctorResult:
    def _ok_result(self) -> DoctorResult:
        return DoctorResult(
            hermes_present=True,
            hermes_version="Hermes Agent v0.16.0",
            missing_profiles=[],
            ok=True,
        )

    def _fail_result(self) -> DoctorResult:
        return DoctorResult(
            hermes_present=True,
            hermes_version="Hermes Agent v0.16.0",
            missing_profiles=["junior-qa-agent", "senior-qa-agent"],
            ok=False,
        )

    def _absent_result(self) -> DoctorResult:
        return DoctorResult(
            hermes_present=False,
            hermes_version=None,
            missing_profiles=list(REQUIRED_PROFILES),
            ok=False,
        )

    def test_returns_non_empty_string(self) -> None:
        assert format_doctor_result(self._ok_result()) != ""

    def test_ok_result_contains_pass_indicator(self) -> None:
        output = format_doctor_result(self._ok_result())
        # Must contain at least one positive indicator
        assert any(token in output for token in ("✓", "PASS", "OK", "ok", "pass"))

    def test_fail_result_contains_fail_indicator(self) -> None:
        output = format_doctor_result(self._fail_result())
        assert any(
            token in output
            for token in ("✗", "FAIL", "fail", "missing", "Missing")
        )

    def test_missing_profiles_appear_in_output(self) -> None:
        result = self._fail_result()
        output = format_doctor_result(result)
        for profile in result.missing_profiles:
            assert profile in output, f"Expected '{profile}' in formatted output"

    def test_hermes_version_appears_in_output_when_present(self) -> None:
        result = self._ok_result()
        output = format_doctor_result(result)
        assert "v0.16.0" in output

    def test_absent_hermes_shows_not_found(self) -> None:
        output = format_doctor_result(self._absent_result())
        assert any(
            token in output
            for token in ("not found", "not installed", "absent", "missing", "✗")
        )
