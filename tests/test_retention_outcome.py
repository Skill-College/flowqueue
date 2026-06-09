"""Unit test for outcome-based retention window selection (no DB)."""

from types import SimpleNamespace

from app.workers.retention_janitor import _retention_for


def _queue(success=86400, failed=604800):
    return SimpleNamespace(
        success_retention_seconds=success, failed_retention_seconds=failed
    )


def test_success_outcome_uses_success_window():
    assert _retention_for(False, _queue()) == 86400


def test_failed_outcome_uses_failed_window():
    assert _retention_for(True, _queue()) == 604800


def test_custom_windows_are_respected():
    q = _queue(success=10, failed=99)
    assert _retention_for(False, q) == 10
    assert _retention_for(True, q) == 99
