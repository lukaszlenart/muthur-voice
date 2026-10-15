import contextlib
import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest
from PIL import features

GOLDEN = Path(__file__).resolve().parent
FIXTURES = GOLDEN.parent / "fixtures"

SCENARIOS = {
    "preview": ["<FIX>/short.txt", "--no-tts", "-o", "<TMP>/out.mp4"],
    "own_audio": ["<FIX>/short.txt", "--audio", "<FIX>/voice.mp3", "--srt", "<FIX>/short.srt",
                  "--image", "<FIX>/bg.png", "--no-hum", "--no-upper", "--wrap", "30",
                  "--title", "MU/TH/UR :: ŁĄCZNOŚĆ", "-o", "<TMP>/out.mp4"],
}

requires_menlo = pytest.mark.skipif(not os.path.exists("/System/Library/Fonts/Menlo.ttc"),
                                    reason="golden hashes were recorded with Menlo")


def require_raqm():
    if not features.check("raqm"):
        pytest.fail("golden hashes need Raqm text layout; Pillow loads FriBiDi at runtime: brew install fribidi")


class FakeFFmpeg:
    def __init__(self, cmd, stdin=None):
        self.cmd = list(cmd)
        self.frames = []
        self.returncode = 0
        self.stdin = self

    def write(self, data):
        self.frames.append(hashlib.sha256(data).hexdigest())

    def close(self):
        pass

    def wait(self):
        return self.returncode


def golden_path(name):
    return GOLDEN / f"{name}.json"


def run_scenario(name, main, tmp):
    subs = {"<FIX>": str(FIXTURES), "<TMP>": str(tmp)}
    procs = []

    def popen(cmd, stdin=None):
        procs.append(FakeFFmpeg(cmd, stdin))
        return procs[-1]

    with mock.patch("subprocess.Popen", popen), contextlib.chdir(tmp):
        main([_replace(a, subs) for a in SCENARIOS[name]])
    (proc,) = procs
    back = {v: k for k, v in subs.items()}
    return {"cmd": [_replace(a, back) for a in proc.cmd], "frames": proc.frames}


def _replace(s, mapping):
    for old, new in mapping.items():
        s = s.replace(old, new)
    return s
