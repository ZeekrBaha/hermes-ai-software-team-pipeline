"""Smoke test — verifies the package is importable."""

import team_pipeline


def test_package_importable() -> None:
    assert team_pipeline.__version__ == "0.1.0"
