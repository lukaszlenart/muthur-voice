import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_package_is_importable():
    import muthur

    assert muthur.__name__ == "muthur"


def test_requires_python_matches_python_version():
    pinned = (ROOT / ".python-version").read_text().strip()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["requires-python"] == f">={pinned}"
