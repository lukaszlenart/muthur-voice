import io
import json
import urllib.error

import pytest

from muthur import cli, update

DAY = 24 * 60 * 60


def test_notice_names_the_new_version_and_the_upgrade_command():
    assert update.notice("0.1.0", "0.2.0") == (
        "MU/TH/UR 0.2.0 is available (you have 0.1.0): uv tool upgrade muthur-voice")


@pytest.mark.parametrize("newest", ["0.1.0", "0.0.9", None, "0.2.0-rc1", "garbage"])
def test_no_notice_unless_the_release_is_newer(newest):
    assert update.notice("0.1.0", newest) is None


def test_versions_compare_numerically():
    assert update.notice("0.9.0", "0.10.0") is not None


def test_fetches_and_caches_the_latest_release(tmp_path):
    path = tmp_path / "muthur" / "latest.json"
    assert update.latest(str(path), now=1000.0, fetch=lambda: "0.2.0") == "0.2.0"
    assert json.loads(path.read_text(encoding="utf-8")) == {"checked": 1000.0, "latest": "0.2.0"}


def test_a_fresh_cache_skips_the_network(tmp_path):
    path = tmp_path / "latest.json"
    path.write_text(json.dumps({"checked": 1000.0, "latest": "0.3.0"}), encoding="utf-8")

    def offline():
        raise AssertionError("must not fetch within a day of the last check")

    assert update.latest(str(path), now=1000.0 + DAY - 1, fetch=offline) == "0.3.0"


@pytest.mark.parametrize("content", [json.dumps({"checked": 0.0, "latest": "0.3.0"}), "not json", "[]"])
def test_a_stale_or_broken_cache_fetches_again(tmp_path, content):
    path = tmp_path / "latest.json"
    path.write_text(content, encoding="utf-8")
    assert update.latest(str(path), now=DAY + 1, fetch=lambda: "0.4.0") == "0.4.0"


def test_network_failure_is_silent_and_not_cached(tmp_path):
    path = tmp_path / "latest.json"

    def offline():
        raise urllib.error.URLError("no network")

    assert update.latest(str(path), now=1000.0, fetch=offline) is None
    assert not path.exists()


def test_fetch_reads_the_release_tag(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.full_url, timeout))
        return io.BytesIO(json.dumps({"tag_name": "v0.2.0"}).encode())

    monkeypatch.setattr(update.urllib.request, "urlopen", fake_urlopen)
    assert update.fetch_latest() == "0.2.0"
    assert seen == [("https://api.github.com/repos/lukaszlenart/muthur-voice/releases/latest", 2)]


@pytest.mark.parametrize("env", [{"MUTHUR_NO_UPDATE_CHECK": "1"}, {"CI": "true"}])
def test_check_is_off_by_env(monkeypatch, env):
    monkeypatch.setattr(update, "from_source", lambda: False)
    assert update.disabled(env)


def test_check_is_off_in_a_source_checkout():
    assert update.from_source()  # the test run uses the editable install from `uv sync`
    assert update.disabled({})


def test_check_is_on_for_an_installed_tool(monkeypatch):
    monkeypatch.setattr(update, "from_source", lambda: False)
    assert not update.disabled({})


@pytest.mark.parametrize("os_name,env,expected", [
    ("posix", {"XDG_CACHE_HOME": "/xdg"}, ["/xdg", "muthur", "latest.json"]),
    ("nt", {"LOCALAPPDATA": "C:/AppData/Local"}, ["C:/AppData/Local", "muthur", "latest.json"]),
])
def test_cache_lives_in_the_platform_cache_folder(monkeypatch, os_name, env, expected):
    monkeypatch.setattr(update.os, "name", os_name)
    assert update.cache_path(env) == update.os.path.join(*expected)


def test_report_prints_the_notice_to_stderr(monkeypatch, capsys):
    monkeypatch.setattr(update, "disabled", lambda env=None: False)
    monkeypatch.setattr(update, "latest", lambda path, now: "9.0.0")
    monkeypatch.setattr(update, "installed_version", lambda: "0.1.0")
    update.report(update.start())
    assert "MU/TH/UR 9.0.0 is available" in capsys.readouterr().err


def test_start_does_nothing_when_disabled(monkeypatch):
    monkeypatch.setattr(update, "disabled", lambda env=None: True)
    assert update.start() is None
    update.report(None)


def test_version_flag_prints_the_installed_version(capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--version"])
    assert capsys.readouterr().out.strip() == f"muthur {update.installed_version()}"
