import json
import os
import sys
import threading
import time
import urllib.request
from importlib import metadata

DIST = "muthur-voice"
LATEST_URL = "https://api.github.com/repos/lukaszlenart/muthur-voice/releases/latest"
UPGRADE = "uv tool upgrade muthur-voice"
DAY = 24 * 60 * 60


def installed_version():
    return metadata.version(DIST)


def from_source():
    try:
        info = json.loads(metadata.distribution(DIST).read_text("direct_url.json") or "{}")
    except (metadata.PackageNotFoundError, ValueError):
        return True
    return info.get("dir_info", {}).get("editable", False)


def disabled(env=None):
    env = os.environ if env is None else env
    return bool(env.get("MUTHUR_NO_UPDATE_CHECK") or env.get("CI")) or from_source()


def cache_path(env=None):
    env = os.environ if env is None else env
    if os.name == "nt":
        base = env.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = env.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "muthur", "latest.json")


def fetch_latest(timeout=2):
    req = urllib.request.Request(LATEST_URL, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": "muthur"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["tag_name"].removeprefix("v")


def latest(path, now, fetch=fetch_latest):
    try:
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        if now - cached["checked"] < DAY:
            return cached["latest"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        version = fetch()
    except Exception:  # offline, rate-limited or no release yet: never break a render
        return None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"checked": now, "latest": version}, f)
    except OSError:
        pass
    return version


def parse(version):
    try:
        return tuple(int(part) for part in version.split("."))
    except (AttributeError, ValueError):
        return None


def notice(current, newest):
    new, cur = parse(newest), parse(current)
    if new and cur and new > cur:
        return f"MU/TH/UR {newest} is available (you have {current}): {UPGRADE}"
    return None


def start():
    if disabled():
        return None
    result = []
    thread = threading.Thread(target=lambda: result.append(latest(cache_path(), time.time())), daemon=True)
    thread.start()
    return thread, result


def report(pending, wait=0.5):
    if not pending:
        return
    thread, result = pending
    thread.join(wait)
    if result and (message := notice(installed_version(), result[0])):
        sys.stdout.flush()
        print(f"  {message}", file=sys.stderr)
