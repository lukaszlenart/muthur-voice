import pytest

from golden import harness


def test_require_raqm_fails_with_the_fix_when_layout_is_basic(monkeypatch):
    monkeypatch.setattr(harness.features, "check", lambda name: False)
    with pytest.raises(pytest.fail.Exception, match="brew install fribidi"):
        harness.require_raqm()


def test_require_raqm_passes_when_raqm_is_available(monkeypatch):
    monkeypatch.setattr(harness.features, "check", lambda name: name == "raqm")
    harness.require_raqm()
