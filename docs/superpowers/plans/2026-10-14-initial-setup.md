# muthur-voice Initial Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the single-file prototype `mother_intro.py` into a uv-managed Python package with a `muthur` CLI (`render`, `voices`), split into modules, covered by tests, with README and CLAUDE.md — without changing the rendered output.

**Architecture:** A pixel-exact golden test is recorded from the prototype *before* any code moves: a fake `subprocess.Popen` captures the ffmpeg command and the SHA-256 of every raw RGB frame piped to it. The prototype is then moved, function by function, into `src/muthur/` (`text`, `timing`, `align`, `render`, `mux`, `narration`, `cli`). The golden test must stay green through every task. Deliberate behaviour changes (Unicode/BOM robustness) come only after the move, in their own task.

**Tech Stack:** Python 3.14 (Homebrew), uv 0.11 with the `uv_build` backend, Pillow 12, edge-tts 7.3, faster-whisper 1.2 (optional extra), pytest, ffmpeg 9, macOS `afplay`.

**Spec:** `docs/BRIEF.md` (copy of the project brief; section "What I want from the initial setup").

## Global Constraints

- Polish is the primary language: every text path (fonts, upper-casing, wrapping, Whisper word matching) must handle `ą ć ę ł ń ó ś ź ż`. English should work too.
- The prototype is the source of truth for the visual style: refactor it, don't rewrite the look. The golden frame hashes must match through Tasks 2–8.
- The user's shell is **fish**. No bash-only syntax in docs or commands (no heredocs, no `export X=`, no `$(...)`; use `(...)`). Commit with repeated `-m`.
- System pip is blocked (PEP 668): everything runs through `uv run` / the project `.venv`.
- `ffmpeg` is the plain Homebrew formula; libass is not needed (Pillow draws the text).
- Fonts: Menlo (`/System/Library/Fonts/Menlo.ttc`) on macOS, DejaVu Sans Mono as Linux fallback.
- Default voice `pl-PL-ZofiaNeural`, rate `-10%`; video 1920×1080 @ 25 fps, H.264 + AAC, `yuv420p`, `+faststart`; 2 s lead-in, 3 s tail.
- Git: remote `git@github.com:lukaszlenart/muthur-voice.git` (private, Apache-2.0). Never commit to `main`. All work happens on `feat/initial-setup`, branched from `origin/main`. When it's finished, run `/security-review` on the branch diff before `gh pr create`. Commit messages are Conventional Commits (`feat:`, `test:`, `refactor:`, `build:`, `docs:`, `chore:`) and end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Media files (`*.mp4`, `*.mp3`, generated `*_napisy.srt`) are never committed. `lektor.mp3` is the user's own recording: never overwrite or delete it.

## Review Focus

1. **Text saved in decomposed Unicode (NFD)**, e.g. pasted on macOS: `ż` arrives as `z` + U+0307. A person expects it to render and to match Whisper's output exactly like NFC text. Today `norm_word` turns NFD `żółć` into `zołc`, so alignment silently fails. → Task 8 tests `read_text`, `norm_word`, `parse_srt` with NFD input.
2. **UTF-8 BOM at the start of `intro.txt` or an SRT** (TextEdit, Windows editors). A person expects no stray glyph before the first word. → Task 8 tests `read_text` and `parse_srt` with a BOM.
3. **Hand-fixed `<out>_napisy.srt` fed back with `--srt`**: CRLF line endings, or a shortened fraction like `00:00:12,5`. A person expects 12.5 s. Today it parses as 12.005 s. → CRLF parse test in Task 3; short-fraction test in Task 8.
4. **`--rate -15%` (space form)**: argparse rejects a value starting with `-`. A person expects a clear rule. → Task 6 pins that `--rate=-15%` works and the space form exits, and README documents the `=` form.
5. **Voice audition where one voice fails** (typo, network) **or `afplay` is missing** (Linux). A person expects the remaining voices to still play, or the samples to be saved with their paths printed. → Task 7 tests `audition` skipping a failed voice and `voices` falling back to a saved `audition/` directory.

---

## File Structure

```
pyproject.toml               uv project, `muthur` entry point, optional `align` extra, pytest config
.python-version              3.14
.gitignore
src/muthur/__init__.py       empty package marker
src/muthur/text.py           split_sentences, norm_word, read_text (Task 8)
src/muthur/timing.py         SRT parse/write, edge-tts cue merging, estimated timing
src/muthur/align.py          Whisper transcription + difflib sentence alignment
src/muthur/render.py         Pillow frame drawing, constants (W, H, FPS, LEAD_IN, TAIL), frame generator
src/muthur/mux.py            ffmpeg command builder + frame piping
src/muthur/narration.py      edge-tts invocation, voice audition
src/muthur/cli.py            argparse: `muthur render`, `muthur voices`
tests/fixtures/short.txt     2-sentence Polish script for golden + render tests
tests/fixtures/short.srt     matching subtitles
tests/fixtures/bg.png        deterministic background image (800×600, exercises crop)
tests/golden/__init__.py
tests/golden/harness.py      FakeFFmpeg, scenarios, run_scenario
tests/golden/record.py       (re)records golden JSON
tests/golden/preview.json    recorded from the prototype
tests/golden/own_audio.json  recorded from the prototype
tests/test_*.py              unit tests per module + test_golden.py
README.md, CLAUDE.md
```

`mother_intro.py` is deleted in Task 6, once the package reproduces its output. Git history keeps it.

---

### Task 1: Repository and uv project bootstrap

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `.python-version`, `src/muthur/__init__.py`, `tests/test_package.py`
- Delete: `.venv/` (created by plain `python -m venv`; uv recreates it)

**Interfaces:**
- Produces: importable package `muthur` (src layout); `uv run pytest` works; dev group has `pytest`; extra `align` installs `faster-whisper`.

- [ ] **Step 1: Connect to the GitHub repo and branch off `main` (no commit to main)**

The remote `git@github.com:lukaszlenart/muthur-voice.git` (private) has one commit on `main`: an Apache-2.0 `LICENSE`. The local files aren't tracked in it, so nothing conflicts.

```fish
cd ~/Projects/Private/muthur-voice
git init -b main
git remote add origin git@github.com:lukaszlenart/muthur-voice.git
git fetch origin
git checkout -b feat/initial-setup origin/main
git status --short
```

Expected: `LICENSE` is checked out; the local files show as untracked (`??`). The branch tracks `origin/main` only as its starting point. Pushing and opening the PR happen when the branch is finished, never during the plan.

- [ ] **Step 2: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.egg-info/
*.mp4
*.mp3
*_napisy.srt
audition/
```

- [ ] **Step 3: Commit the prototype as-is (baseline for history)**

```fish
git add .gitignore CLAUDE.md intro.txt mother_intro.py docs/BRIEF.md docs/superpowers/plans/2026-10-14-initial-setup.md
git commit -m "chore: import prototype, brief and setup plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Write the failing smoke test** `tests/test_package.py`

```python
def test_package_is_importable():
    import muthur

    assert muthur.__name__ == "muthur"
```

- [ ] **Step 5: Write `pyproject.toml`**

```toml
[project]
name = "muthur-voice"
version = "0.1.0"
description = "MU/TH/UR terminal intro videos with Polish narration for Alien RPG sessions"
license = "Apache-2.0"
license-files = ["LICENSE"]
requires-python = ">=3.12"
dependencies = [
    "edge-tts>=7.3",
    "pillow>=12.0",
]

[project.optional-dependencies]
align = ["faster-whisper>=1.2"]

[project.scripts]
muthur = "muthur.cli:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["uv_build>=0.11,<0.12"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "muthur"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
markers = ["golden: pixel-exact comparison with the recorded prototype output (slow, needs Menlo)"]
```

`.python-version`:

```
3.14
```

Create an empty `src/muthur/__init__.py`.

The `muthur` script points at `muthur.cli:main`, which doesn't exist until Task 6. `uv sync` installs the script stub anyway, and only running `muthur` fails before then.

- [ ] **Step 6: Recreate the venv with uv and run the test**

```fish
rm -rf .venv
uv sync --extra align
uv run pytest -v
```

Expected: `test_package_is_importable PASSED`. `uv run python -c "import faster_whisper, edge_tts, PIL"` exits 0.

- [ ] **Step 7: Check that the prototype still runs in the new env**

```fish
uv run python mother_intro.py intro.txt --no-tts -o /tmp/muthur-smoke.mp4
```

Expected: ends with `done: /tmp/muthur-smoke.mp4 (…s)`. Delete the file afterwards.

- [ ] **Step 8: Commit**

```fish
git add pyproject.toml .python-version uv.lock src/muthur/__init__.py tests/test_package.py
git commit -m "build: add uv project with muthur package skeleton" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Golden characterization of the prototype

**Files:**
- Create: `tests/fixtures/short.txt`, `tests/fixtures/short.srt`, `tests/fixtures/bg.png`, `tests/golden/__init__.py` (empty), `tests/golden/harness.py`, `tests/golden/record.py`, `tests/golden/preview.json`, `tests/golden/own_audio.json`

**Interfaces:**
- Consumes: `mother_intro.main()` (reads `sys.argv`).
- Produces (used by Tasks 5, 6, 8, 9):
  - `golden.harness.FIXTURES: Path`
  - `golden.harness.SCENARIOS: dict[str, list[str]]` — render arguments *without* the `render` subcommand; contain `<FIX>` / `<TMP>` placeholders
  - `golden.harness.run_scenario(name: str, main: Callable[[list[str]], None], tmp: Path) -> dict` returning `{"cmd": list[str], "frames": list[str]}` with paths turned back into placeholders
  - `golden.harness.golden_path(name: str) -> Path`
  - `golden.harness.requires_menlo` — pytest skip marker

- [ ] **Step 1: Write fixtures**

`tests/fixtures/short.txt` (UTF-8, NFC, trailing newline):

```
Raport systemowy: załoga w hibernacji. Dlaczego Matka was obudziła?
```

`tests/fixtures/short.srt`:

```
1
00:00:00,000 --> 00:00:02,400
Raport systemowy: załoga w hibernacji.

2
00:00:02,800 --> 00:00:04,500
Dlaczego Matka was obudziła?
```

Generate `tests/fixtures/bg.png` once and commit it. Don't regenerate it in tests.

```fish
uv run python -c "from PIL import Image, ImageDraw; im = Image.linear_gradient('L').resize((800, 600)).convert('RGB'); ImageDraw.Draw(im).rectangle((200, 150, 600, 450), fill=(200, 40, 40)); im.save('tests/fixtures/bg.png')"
```

- [ ] **Step 2: Write `tests/golden/harness.py`**

```python
import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest

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

    with mock.patch("subprocess.Popen", popen):
        main([_replace(a, subs) for a in SCENARIOS[name]])
    (proc,) = procs
    back = {v: k for k, v in subs.items()}
    return {"cmd": [_replace(a, back) for a in proc.cmd], "frames": proc.frames}


def _replace(s, mapping):
    for old, new in mapping.items():
        s = s.replace(old, new)
    return s
```

`<FIX>/voice.mp3` doesn't need to exist: the fake ffmpeg never opens it.

- [ ] **Step 3: Write `tests/golden/record.py`**

```python
"""Record golden frame hashes: uv run python tests/golden/record.py prototype|package"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from golden.harness import SCENARIOS, golden_path, run_scenario  # noqa: E402


def prototype_main(args):
    import mother_intro
    sys.argv = ["mother_intro.py", *args]
    mother_intro.main()


def package_main(args):
    from muthur.cli import main
    main(["render", *args])


target = {"prototype": prototype_main, "package": package_main}[sys.argv[1]]
for name in SCENARIOS:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_scenario(name, target, Path(tmp))
    golden_path(name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{name}: {len(result['frames'])} frames")
```

- [ ] **Step 4: Record from the prototype**

```fish
uv run python tests/golden/record.py prototype
```

Expected: `preview: 260 frames` and `own_audio: 237 frames` (`4.5 + 2 + 3 = 9.5 s × 25 = 237`). Each takes about 7–10 s.

- [ ] **Step 5: Prove determinism by re-recording**

```fish
mkdir -p /tmp/muthur-golden; and cp tests/golden/*.json /tmp/muthur-golden/
uv run python tests/golden/record.py prototype
for f in preview own_audio; cmp tests/golden/$f.json /tmp/muthur-golden/$f.json; and echo "$f identical"; end
```

Expected: `preview identical` and `own_audio identical`. If the hashes differ between runs, stop: the golden approach doesn't work on this machine, so report back before going further.

- [ ] **Step 6: Commit**

```fish
git add tests/fixtures tests/golden
git commit -m "test: record golden frame hashes from the prototype" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `text` and `timing` modules

**Files:**
- Create: `src/muthur/text.py`, `src/muthur/timing.py`, `tests/test_text.py`, `tests/test_timing.py`

**Interfaces:**
- Produces:
  - `muthur.text.split_sentences(text: str) -> list[str]`
  - `muthur.text.norm_word(w: str) -> str`
  - `muthur.timing.srt_time(s: str) -> float`
  - `muthur.timing.parse_srt(path: str) -> list[list]` — cues `[start: float, end: float, text: str]`, merged into sentences
  - `muthur.timing.merge_into_sentences(cues: list[list]) -> list[list]`
  - `muthur.timing.write_srt(cues: list[list], path: str) -> None`
  - `muthur.timing.estimate_cues(text: str, cps: float = 13.0) -> list[list]`

Cues stay mutable `[start, end, text]` lists, exactly as in the prototype. `align` mutates them in place.

- [ ] **Step 1: Write the failing tests** `tests/test_text.py`

```python
from muthur.text import norm_word, split_sentences


def test_splits_on_terminal_punctuation_keeping_it():
    assert split_sentences("Ala ma kota... A kot? Nie! Koniec") == ["Ala ma kota...", "A kot?", "Nie!", "Koniec"]


def test_colon_does_not_end_a_sentence():
    assert split_sentences("Jednostka: USCSS Montero. Stan załogi: hibernacja.") == [
        "Jednostka: USCSS Montero.", "Stan załogi: hibernacja."]


def test_line_break_without_punctuation_stays_inside_sentence():
    assert split_sentences("Raport\nsystemowy. Druga linia") == ["Raport\nsystemowy.", "Druga linia"]


def test_empty_text_has_no_sentences():
    assert split_sentences("  \n") == []


def test_norm_word_lowercases_polish_and_drops_punctuation():
    assert norm_word("ŻÓŁĆ,") == "żółć"
    assert norm_word("MU/TH/UR") == "muthur"
    assert norm_word("6000.") == "6000"
    assert norm_word(" ...") == ""
```

`tests/test_timing.py`:

```python
import pytest

from muthur.timing import estimate_cues, merge_into_sentences, parse_srt, srt_time, write_srt


def test_srt_time_accepts_comma_and_dot():
    assert srt_time("00:01:02,345") == pytest.approx(62.345)
    assert srt_time("01:00:00.250") == pytest.approx(3600.25)


def test_merges_cues_split_mid_sentence():
    cues = [[0, 1, "Kurs został"], [1, 2, "skorygowany."], [2, 3, "Ale"], [3, 4, "coś: tak"]]
    assert merge_into_sentences(cues) == [[0, 2, "Kurs został skorygowany."], [2, 4, "Ale coś: tak"]]


def test_colon_closes_a_cue():
    assert merge_into_sentences([[0, 1, "Stan załogi:"], [1, 2, "hibernacja."]]) == [
        [0, 1, "Stan załogi:"], [1, 2, "hibernacja."]]


def test_parse_srt_handles_crlf_multiline_and_merging(tmp_path):
    srt = tmp_path / "n.srt"
    srt.write_bytes((
        "1\r\n00:00:00,000 --> 00:00:01,000\r\nKurs\r\nzostał\r\n\r\n"
        "2\r\n00:00:01,000 --> 00:00:02,500\r\nskorygowany.\r\n\r\n"
        "garbage block without timestamp\r\n\r\n"
        "3\r\n00:00:03,000 --> 00:00:04,000\r\nWitamy z powrotem, załogo.\r\n"
    ).encode("utf-8"))
    assert parse_srt(str(srt)) == [
        [0.0, 2.5, "Kurs został skorygowany."],
        [3.0, 4.0, "Witamy z powrotem, załogo."],
    ]


def test_write_srt_format_and_round_trip(tmp_path):
    path = tmp_path / "out.srt"
    cues = [[0.0, 1.5, "Raport systemowy."], [3723.4567, 3725.0, "Stan załogi: hibernacja."]]
    write_srt(cues, str(path))
    assert path.read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,500\nRaport systemowy.\n\n"
        "2\n01:02:03,457 --> 01:02:05,000\nStan załogi: hibernacja.\n\n")
    assert parse_srt(str(path)) == [[0.0, 1.5, "Raport systemowy."],
                                    [pytest.approx(3723.457), 3725.0, "Stan załogi: hibernacja."]]


def test_estimate_cues_uses_length_with_minimum_and_gap():
    cues = estimate_cues("Krótko. " + "a" * 26 + ".")
    assert cues[0] == [0.0, 1.5, "Krótko."]
    assert cues[1][0] == pytest.approx(1.85)
    assert cues[1][1] == pytest.approx(1.85 + 27 / 13)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_text.py tests/test_timing.py -v`
Expected: collection errors, `ModuleNotFoundError: No module named 'muthur.text'`.

- [ ] **Step 3: Move the code verbatim from `mother_intro.py`**

`src/muthur/text.py`:

```python
import re


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def norm_word(w):
    return re.sub(r"[^0-9a-ząćęłńóśźż]", "", w.lower())
```

`src/muthur/timing.py`:

```python
import re

from muthur.text import split_sentences


def srt_time(s):
    h, m, rest = s.strip().split(":")
    sec, ms = re.split(r"[,.]", rest)
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(path):
    cues = []
    with open(path, encoding="utf-8") as f:
        blocks = re.split(r"\n\s*\n", f.read().strip())
    for b in blocks:
        lines = [l for l in b.strip().splitlines() if l.strip()]
        ts = next((l for l in lines if "-->" in l), None)
        if not ts:
            continue
        a, z = ts.split("-->")
        text = " ".join(lines[lines.index(ts) + 1:]).strip()
        if text:
            cues.append([srt_time(a), srt_time(z), text])
    return merge_into_sentences(cues)


def merge_into_sentences(cues):
    """edge-tts may split cues mid-sentence; glue them so the screen shows whole sentences."""
    out = []
    for c in cues:
        if out and not re.search(r"[.!?:]$", out[-1][2]):
            out[-1][1] = c[1]
            out[-1][2] += " " + c[2]
        else:
            out.append(c)
    return out


def write_srt(cues, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, z, s) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(z)}\n{s}\n\n")


def estimate_cues(text, cps=13.0):
    sentences = split_sentences(text)
    t, cues = 0.0, []
    for s in sentences:
        d = max(1.5, len(s) / cps)
        cues.append([t, t + d, s])
        t += d + 0.35
    return cues
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_text.py tests/test_timing.py -v`
Expected: all PASS. `"garbage block without timestamp"` is a block of its own, so it's skipped (no `-->`).

- [ ] **Step 5: Commit**

```fish
git add src/muthur/text.py src/muthur/timing.py tests/test_text.py tests/test_timing.py
git commit -m "refactor: move sentence splitting and SRT timing into muthur.text and muthur.timing" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `align` module (Whisper alignment, testable without Whisper)

**Files:**
- Create: `src/muthur/align.py`, `tests/test_align.py`

**Interfaces:**
- Consumes: `muthur.text.norm_word`, `muthur.text.split_sentences`
- Produces:
  - `muthur.align.align_cues(text: str, audio: str, model_size: str = "small") -> list[list] | None` (same contract as the prototype; `None` means "fall back to estimated timing")
  - `muthur.align.transcribe(text: str, audio: str, model_size: str) -> list[tuple[str, float, float]] | None` — raw Whisper words, or `None` when faster-whisper isn't installed
  - `muthur.align.match_cues(text: str, words: list[tuple[str, float, float]]) -> list[list] | None` — pure, the unit-tested core

The split separates the Whisper call from the matching logic. Nothing else changes, apart from the install hint in one message (`uv sync --extra align` instead of `pip install`).

- [ ] **Step 1: Write the failing tests** `tests/test_align.py`

The expected values were produced by running the prototype's `align_cues` against these same fake transcripts.

```python
import sys
from types import ModuleType, SimpleNamespace

import pytest

from muthur import align
from muthur.align import match_cues

TEXT = "Raport systemowy. Stan załogi: hibernacja. Witamy z powrotem, załogo."
S1, S2, S3 = "Raport systemowy.", "Stan załogi: hibernacja.", "Witamy z powrotem, załogo."
# Whisper word tokens carry a leading space and punctuation
HEARD = [(" Raport", 0.0, 0.4), (" systemowy.", 0.4, 1.0),
         (" Stan", 1.5, 1.8), (" załogi:", 1.8, 2.2), (" hibernacja.", 2.2, 3.0),
         (" Witamy", 3.5, 3.9), (" z", 3.9, 4.0), (" powrotem,", 4.0, 4.5), (" załogo.", 4.5, 5.0)]


def assert_cues(actual, expected):
    assert [c[2] for c in actual] == [c[2] for c in expected]
    assert [c[:2] for c in actual] == [pytest.approx(c[:2]) for c in expected]


def test_perfect_transcript():
    assert_cues(match_cues(TEXT, HEARD), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_misrecognised_words_only_narrow_the_sentence():
    heard = list(HEARD)
    heard[0] = (" Rapport", 0.0, 0.4)
    heard[3] = (" załogę", 1.8, 2.2)
    heard[5] = (" Witam", 3.5, 3.9)
    assert_cues(match_cues(TEXT, heard), [[0.4, 1.0, S1], [1.5, 3.0, S2], [3.9, 5.0, S3]])


def test_missing_middle_sentence_fills_the_gap():
    assert_cues(match_cues(TEXT, HEARD[:2] + HEARD[5:]), [[0.0, 1.0, S1], [1.0, 3.5, S2], [3.5, 5.0, S3]])


def test_missing_first_sentence_starts_at_zero():
    assert_cues(match_cues(TEXT, HEARD[2:]), [[0.0, 1.5, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_missing_last_sentence_gets_minimum_slot_after_previous():
    assert_cues(match_cues(TEXT, HEARD[:5]), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.0, 3.3, S3]])


def test_consecutive_missing_sentences_split_gap_by_length():
    text = "Jeden. Dwa trzy. Cztery pięć sześć siedem. Osiem."
    cues = match_cues(text, [(" Jeden.", 0.0, 0.5), (" Osiem.", 8.0, 8.5)])
    split = 0.5 + 7.5 * 9 / 34
    assert_cues(cues, [[0.0, 0.5, "Jeden."], [0.5, split, "Dwa trzy."],
                       [split, 8.0, "Cztery pięć sześć siedem."], [8.0, 8.5, "Osiem."]])


def test_hallucinated_trailing_words_are_ignored():
    heard = HEARD + [(" Napisy", 5.5, 5.8), (" stworzone", 5.8, 6.2), (" przez", 6.2, 6.4), (" społeczność", 6.4, 7.0)]
    assert_cues(match_cues(TEXT, heard), [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.5, 5.0, S3]])


def test_word_heard_out_of_order_never_moves_time_backwards():
    heard = HEARD[:2] + [(" Witamy", 1.2, 1.4)] + HEARD[2:5]
    cues = match_cues(TEXT, heard)
    assert_cues(cues, [[0.0, 1.0, S1], [1.5, 3.0, S2], [3.0, 3.3, S3]])
    assert all(a[0] <= b[0] for a, b in zip(cues, cues[1:]))


@pytest.mark.parametrize("heard", [[], [(" ...", 0.0, 0.5)]])
def test_no_usable_words_means_fallback(heard):
    assert match_cues(TEXT, heard) is None


def test_transcribe_without_faster_whisper_returns_none(monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    assert align.transcribe(TEXT, "voice.mp3", "small") is None


def test_transcribe_asks_for_polish_word_timestamps_with_script_prompt(monkeypatch):
    seen = {}

    class WhisperModel:
        def __init__(self, size, **kwargs):
            seen["size"] = size

        def transcribe(self, audio, **kwargs):
            seen.update(kwargs)
            words = [SimpleNamespace(word=w, start=s, end=e) for w, s, e in HEARD]
            return [SimpleNamespace(words=words), SimpleNamespace(words=None)], None

    fake = ModuleType("faster_whisper")
    fake.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    assert align.transcribe(TEXT, "voice.mp3", "base") == HEARD
    assert seen == {"size": "base", "language": "pl", "word_timestamps": True, "initial_prompt": TEXT[:800]}


def test_align_cues_returns_none_when_whisper_unavailable(monkeypatch):
    monkeypatch.setattr(align, "transcribe", lambda *a: None)
    assert align.align_cues(TEXT, "voice.mp3") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_align.py -v`
Expected: `ModuleNotFoundError: No module named 'muthur.align'`.

- [ ] **Step 3: Write `src/muthur/align.py`**

The body of `match_cues` is the prototype's `align_cues` from `sm = …` onward, unchanged.

```python
import difflib

from muthur.text import norm_word, split_sentences


def align_cues(text, audio, model_size="small"):
    words = transcribe(text, audio, model_size)
    return None if words is None else match_cues(text, words)


def transcribe(text, audio, model_size):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  ! faster-whisper not installed (uv sync --extra align), estimating timing")
        return None

    print(f"  aligning subtitles with Whisper ({model_size}), first run downloads the model...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="pl", word_timestamps=True,
                                   initial_prompt=text[:800])
    return [(w.word, w.start, w.end) for s in segments for w in (s.words or [])]


def match_cues(text, words):
    """Find when each sentence of `text` is spoken, given Whisper's timed words.

    The recognised words are matched against the script words (difflib), so
    small recognition mistakes don't matter. Sentences with no matched word get
    a time slot interpolated from their neighbours.
    """
    rec = [(norm_word(w), st, en) for w, st, en in words]
    rec = [r for r in rec if r[0]]
    if not rec:
        print("  ! Whisper recognised no words, estimating timing")
        return None

    sentences = split_sentences(text)
    script, owner = [], []
    for i, s in enumerate(sentences):
        for w in s.split():
            n = norm_word(w)
            if n:
                script.append(n)
                owner.append(i)

    times = [[] for _ in sentences]
    sm = difflib.SequenceMatcher(None, script, [r[0] for r in rec], autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            _, st, en = rec[b + k]
            times[owner[a + k]].append((st, en))

    cues = [[min(t[0] for t in ts), max(t[1] for t in ts), s] if ts else [None, None, s]
            for ts, s in zip(times, sentences)]
    matched = sum(1 for c in cues if c[0] is not None)
    print(f"  matched {matched}/{len(cues)} sentences")

    # fill sentences Whisper missed, proportionally to their length
    end_of_audio = rec[-1][2]
    i = 0
    while i < len(cues):
        if cues[i][0] is not None:
            i += 1
            continue
        j = i
        while j < len(cues) and cues[j][0] is None:
            j += 1
        lo = cues[i - 1][1] if i > 0 else 0.0
        hi = cues[j][0] if j < len(cues) else end_of_audio
        total = sum(len(c[2]) for c in cues[i:j]) or 1
        t = lo
        for c in cues[i:j]:
            d = (hi - lo) * len(c[2]) / total
            c[0], c[1] = t, t + d
            t += d
        i = j
    for k in range(1, len(cues)):  # keep order monotonic
        cues[k][0] = max(cues[k][0], cues[k - 1][0])
        cues[k][1] = max(cues[k][1], cues[k][0] + 0.3)
    return cues
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_align.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```fish
git add src/muthur/align.py tests/test_align.py
git commit -m "refactor: move Whisper alignment into muthur.align with a pure matching core" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `render` and `mux` modules

**Files:**
- Create: `src/muthur/render.py`, `src/muthur/mux.py`, `tests/test_render.py`, `tests/test_mux.py`

**Interfaces:**
- Consumes: `golden.harness.FIXTURES`, `golden.harness.golden_path`, `golden.harness.requires_menlo`, `muthur.timing.estimate_cues`
- Produces:
  - `muthur.render.W, H, FPS, LEAD_IN, TAIL` constants
  - `muthur.render.load_font(size: int, path: str | None = None) -> ImageFont.FreeTypeFont`
  - `muthur.render.build_blocks(cues, wrap: int, upper: bool) -> list[tuple[float, float, list[str]]]`
  - `muthur.render.timeline(cues) -> tuple[list[list], float]` — cues shifted by `LEAD_IN`, total seconds
  - `muthur.render.iter_frames(cues, image: str | None, font_path: str | None, wrap: int, upper: bool, title: str) -> tuple[float, Iterator[tuple[float, bytes]]]` — total seconds and a lazy generator of `(t, raw RGB bytes)`
  - `muthur.mux.ffmpeg_command(total: float, audio: str | None, hum: bool, out: str) -> list[str]`
  - `muthur.mux.encode(frames: Iterable[tuple[float, bytes]], total: float, cmd: list[str], out: str) -> None` — exits with `"ffmpeg failed"` on non-zero return code

The prototype's `render_video` is split in three: frame production (`render.iter_frames`), the ffmpeg command (`mux.ffmpeg_command`) and the piping loop (`mux.encode`). Drawing code moves verbatim.

- [ ] **Step 1: Write the failing tests** `tests/test_render.py`

```python
import hashlib
import json

import pytest
from PIL import Image, ImageDraw

from golden.harness import FIXTURES, golden_path, requires_menlo
from muthur.render import build_blocks, iter_frames, load_font, timeline
from muthur.timing import estimate_cues

POLISH = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
BASE = "acelnoszzACELNOSZZ"


def test_upper_casing_and_wrapping_keep_polish_letters():
    assert build_blocks([[0, 1, "zażółć gęślą jaźń zażółć"]], 12, True) == [
        (0, 1, ["ZAŻÓŁĆ GĘŚLĄ", "JAŹŃ ZAŻÓŁĆ"])]


def test_no_upper_keeps_original_case():
    assert build_blocks([[0, 1, "Matka was obudziła"]], 54, False) == [(0, 1, ["Matka was obudziła"])]


def test_empty_cue_text_still_yields_one_line():
    assert build_blocks([[0, 1, ""]], 54, True) == [(0, 1, [""])]


def _glyph(font, ch):
    im = Image.new("L", (80, 80))
    ImageDraw.Draw(im).text((10, 10), ch, font=font, fill=255)
    return im.tobytes()


@requires_menlo
@pytest.mark.parametrize("ch,base", zip(POLISH, BASE))
def test_default_font_draws_polish_diacritics(ch, base):
    font = load_font(46)
    assert _glyph(font, ch) != _glyph(font, "͸")  # unassigned code point -> missing-glyph box
    assert _glyph(font, ch) != _glyph(font, base)


def test_missing_font_path_falls_back_to_system_font():
    assert load_font(46, "/nonexistent/font.ttf").size == 46


def test_timeline_adds_lead_in_and_tail():
    assert timeline([[0.0, 1.0, "a"]]) == ([[2.0, 3.0, "a"]], 6.0)
    assert timeline([]) == ([], 8.0)


@requires_menlo
@pytest.mark.golden
def test_preview_frames_match_prototype():
    expected = json.loads(golden_path("preview").read_text(encoding="utf-8"))
    raw = (FIXTURES / "short.txt").read_text(encoding="utf-8").strip()
    total, frames = iter_frames(estimate_cues(raw), None, None, 54, True, "MU/TH/UR 6000 :: USCSS MONTERO")
    assert [hashlib.sha256(data).hexdigest() for _, data in frames] == expected["frames"]
```

`tests/test_mux.py`:

```python
import pytest

from golden.harness import FakeFFmpeg
from muthur.mux import encode, ffmpeg_command

VIDEO_IN = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "1920x1080", "-r", "25", "-i", "-"]


def video_out(total, out):
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-t", total, "-movflags", "+faststart", out]


AAC = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
HUM = "anoisesrc=color=brown:amplitude=0.6:seed=7"


def test_voice_and_hum_are_mixed():
    assert ffmpeg_command(10.43, "voice.mp3", True, "o.mp4") == VIDEO_IN + [
        "-i", "voice.mp3", "-f", "lavfi", "-t", "10.43", "-i", HUM,
        "-filter_complex",
        "[1:a]adelay=2000|2000,aecho=0.8:0.5:40:0.12[v];"
        "[2:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,afade=t=out:st=8.43:d=2[h];"
        "[v][h]amix=inputs=2:duration=longest:normalize=0[a]",
        "-map", "0:v", *AAC] + video_out("10.43", "o.mp4")


def test_hum_only():
    assert ffmpeg_command(10.43, None, True, "o.mp4") == VIDEO_IN + [
        "-f", "lavfi", "-t", "10.43", "-i", HUM,
        "-filter_complex", "[1:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,afade=t=out:st=8.43:d=2[h];[h]anull[a]",
        "-map", "0:v", *AAC] + video_out("10.43", "o.mp4")


def test_voice_only():
    assert ffmpeg_command(6.0, "voice.mp3", False, "o.mp4") == VIDEO_IN + [
        "-i", "voice.mp3",
        "-filter_complex", "[1:a]adelay=2000|2000,aecho=0.8:0.5:40:0.12[v];[v]anull[a]",
        "-map", "0:v", *AAC] + video_out("6.00", "o.mp4")


def test_silent_video_has_no_audio_stream():
    assert ffmpeg_command(6.0, None, False, "o.mp4") == VIDEO_IN + ["-map", "0:v"] + video_out("6.00", "o.mp4")


def test_encode_pipes_every_frame(monkeypatch):
    procs = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, stdin=None: procs.append(FakeFFmpeg(cmd)) or procs[-1])
    encode([(0.0, b"a"), (0.04, b"b")], 0.08, ["ffmpeg"], "o.mp4")
    assert len(procs[0].frames) == 2


def test_encode_exits_when_ffmpeg_fails(monkeypatch):
    def failing(cmd, stdin=None):
        proc = FakeFFmpeg(cmd)
        proc.returncode = 1
        return proc
    monkeypatch.setattr("subprocess.Popen", failing)
    with pytest.raises(SystemExit, match="ffmpeg failed"):
        encode([(0.0, b"a")], 0.04, ["ffmpeg"], "o.mp4")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_render.py tests/test_mux.py -v`
Expected: `ModuleNotFoundError: No module named 'muthur.render'`.

- [ ] **Step 3: Write `src/muthur/render.py`**

Copy `W, H, FPS, LEAD_IN, TAIL, GREEN, DIM_GREEN, FONT_CANDIDATES, load_font, make_background, make_scanlines, build_blocks, render_text_layer` from `mother_intro.py` **byte for byte**, including their comments. Keep imports `os, random, sys, textwrap` and `from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont`. Then add:

```python
def timeline(cues):
    shifted = [[a + LEAD_IN, z + LEAD_IN, s] for a, z, s in cues]
    total = (shifted[-1][1] if shifted else 5) + TAIL
    return shifted, total


def iter_frames(cues, image, font_path, wrap, upper, title):
    font = load_font(46, font_path)
    font_small = load_font(28, font_path)
    line_h = 66
    max_lines = (H - 140 - 120) // line_h
    shifted, total = timeline(cues)
    blocks = build_blocks(shifted, wrap, upper)
    bg = make_background(image, title, font_small)
    return total, _frames(total, blocks, bg, font, line_h, max_lines)


def _frames(total, blocks, bg, font, line_h, max_lines):
    scan = make_scanlines()
    black = Image.new("RGB", (W, H))
    rnd = random.Random(42)
    for f in range(int(total * FPS)):
        t = f / FPS
        cursor_on = (int(t * 2.5) % 2) == 0
        text = render_text_layer(t, blocks, font, line_h, max_lines, cursor_on)
        glow = text.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(6)).resize((W, H))
        mask = text.convert("L").point(lambda p: 255 if p > 20 else 0)
        frame = Image.composite(text, bg, mask)
        frame = ImageChops.add(frame, glow)            # phosphor glow
        frame = Image.composite(frame, black, scan)    # CRT scanlines
        flicker = 0.94 + 0.06 * rnd.random()
        if t < 0.6:  # power-on fade
            flicker *= t / 0.6
        lut = [min(255, int(i * flicker)) for i in range(256)] * 3
        yield t, frame.point(lut).tobytes()
```

- [ ] **Step 4: Write `src/muthur/mux.py`**

```python
import subprocess
import sys

from muthur.render import FPS, H, LEAD_IN, W


def ffmpeg_command(total, audio, hum, out):
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    filters, maps = [], ["-map", "0:v"]
    inputs = 1
    mix = []
    if audio:
        cmd += ["-i", audio]
        ms = int(LEAD_IN * 1000)
        filters.append(f"[{inputs}:a]adelay={ms}|{ms},aecho=0.8:0.5:40:0.12[v]")
        mix.append("[v]")
        inputs += 1
    if hum:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anoisesrc=color=brown:amplitude=0.6:seed=7"]
        filters.append(f"[{inputs}:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,"
                       f"afade=t=out:st={max(0, total - 2):.2f}:d=2[h]")
        mix.append("[h]")
        inputs += 1
    if mix:
        if len(mix) > 1:
            filters.append("".join(mix) + f"amix=inputs={len(mix)}:duration=longest:normalize=0[a]")
        else:
            filters.append(f"{mix[0]}anull[a]")
        cmd += ["-filter_complex", ";".join(filters)]
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    return cmd + maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
                         "-pix_fmt", "yuv420p", "-t", f"{total:.2f}", "-movflags", "+faststart", out]


def encode(frames, total, cmd, out):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f, (t, data) in enumerate(frames):
        proc.stdin.write(data)
        if f % (FPS * 5) == 0:
            print(f"\r  rendering {t:5.1f}s / {total:.1f}s", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\r  done: {out} ({total:.1f}s)            ")
    if proc.returncode:
        sys.exit("ffmpeg failed")
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_render.py tests/test_mux.py -v`
Expected: all PASS, including `test_preview_frames_match_prototype`. If that one fails, diff the moved functions against `mother_intro.py`. Don't touch the golden JSON.

- [ ] **Step 6: Commit**

```fish
git add src/muthur/render.py src/muthur/mux.py tests/test_render.py tests/test_mux.py
git commit -m "refactor: split frame rendering and ffmpeg muxing into muthur.render and muthur.mux" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `narration` (edge-tts) and `muthur render` CLI; retire the prototype

**Files:**
- Create: `src/muthur/narration.py`, `src/muthur/cli.py`, `tests/test_narration.py`, `tests/test_cli.py`, `tests/test_golden.py`
- Modify: `tests/golden/record.py` (drop the `prototype` target)
- Delete: `mother_intro.py`

**Interfaces:**
- Consumes: everything from Tasks 3–5; `golden.harness.SCENARIOS`, `run_scenario`, `golden_path`, `requires_menlo`
- Produces:
  - `muthur.narration.edge_tts_cmd(voice: str, rate: str, mp3: str, *, file: str | None = None, text: str | None = None, srt: str | None = None) -> list[str]`
  - `muthur.narration.require_edge_tts() -> None` — exits if `edge-tts` isn't on PATH
  - `muthur.narration.run_tts(text_file: str, voice: str, rate: str, workdir: str) -> tuple[str, list[list]]` (Task 8 changes the first parameter to the script text)
  - `muthur.cli.build_parser() -> argparse.ArgumentParser`
  - `muthur.cli.render_video(cues, audio, out, image, font_path, wrap, upper, hum, title) -> None`
  - `muthur.cli.render_command(a: argparse.Namespace) -> None`
  - `muthur.cli.main(argv: list[str] | None = None) -> None`

- [ ] **Step 1: Write the failing tests**

`tests/test_narration.py`:

```python
from pathlib import Path

from muthur import narration


def test_edge_tts_cmd_for_a_file_matches_prototype():
    assert narration.edge_tts_cmd("pl-PL-ZofiaNeural", "-10%", "n.mp3", file="intro.txt", srt="n.srt") == [
        "edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%", "--file", "intro.txt",
        "--write-media", "n.mp3", "--write-subtitles", "n.srt"]


def test_edge_tts_cmd_for_inline_text_survives_leading_dash():
    assert narration.edge_tts_cmd("pl-PL-MarekNeural", "+0%", "s.mp3", text="-- Raport.") == [
        "edge-tts", "--voice", "pl-PL-MarekNeural", "--rate=+0%", "--text=-- Raport.", "--write-media", "s.mp3"]


def test_run_tts_returns_sentence_cues(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        Path(cmd[cmd.index("--write-subtitles") + 1]).write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nKurs został\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nskorygowany.\n", encoding="utf-8")

    monkeypatch.setattr(narration.subprocess, "run", fake_run)
    mp3, cues = narration.run_tts("intro.txt", "pl-PL-ZofiaNeural", "-10%", str(tmp_path))
    assert mp3 == str(tmp_path / "narration.mp3")
    assert seen == [["edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%", "--file", "intro.txt",
                     "--write-media", str(tmp_path / "narration.mp3"),
                     "--write-subtitles", str(tmp_path / "narration.srt")]]
    assert cues == [[0.0, 2.0, "Kurs został skorygowany."]]
```

`tests/test_cli.py`:

```python
import os

import pytest

from muthur import cli
from muthur.timing import estimate_cues


@pytest.fixture
def rendered(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "render_video", lambda *args: calls.append(args))
    return calls


@pytest.fixture
def script(tmp_path):
    path = tmp_path / "intro.txt"
    path.write_text("Raport systemowy. Witamy z powrotem, załogo.\n", encoding="utf-8")
    return path


def test_rate_with_leading_minus_needs_equals_form():
    assert cli.build_parser().parse_args(["render", "intro.txt", "--rate=-15%"]).rate == "-15%"
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["render", "intro.txt", "--rate", "-15%"])


def test_render_defaults_match_prototype():
    a = cli.build_parser().parse_args(["render", "intro.txt"])
    assert (a.voice, a.rate, a.wrap, a.whisper_model, a.title) == (
        "pl-PL-ZofiaNeural", "-10%", 54, "small", "MU/TH/UR 6000 :: USCSS MONTERO")


def test_tts_mode_saves_narration_next_to_video(script, monkeypatch, rendered):
    def fake_tts(source, voice, rate, workdir):
        mp3 = os.path.join(workdir, "narration.mp3")
        with open(mp3, "wb") as f:
            f.write(b"mp3")
        return mp3, [[0.0, 1.0, "Raport systemowy."]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(script)])
    assert (script.parent / "intro_lektor.mp3").read_bytes() == b"mp3"
    cues, _audio, out, image, font, wrap, upper, hum, title = rendered[0]
    assert cues == [[0.0, 1.0, "Raport systemowy."]]
    assert out == str(script.parent / "intro.mp4")
    assert (image, font, wrap, upper, hum) == (None, None, 54, True, True)


def test_own_audio_alignment_writes_editable_srt(script, tmp_path, monkeypatch, rendered):
    monkeypatch.setattr(cli.align, "align_cues", lambda text, audio, size: [[0.5, 1.5, "Raport systemowy."]])
    cli.main(["render", str(script), "--audio", "voice.mp3", "-o", str(tmp_path / "film.mp4")])
    assert "00:00:00,500 --> 00:00:01,500" in (tmp_path / "film_napisy.srt").read_text(encoding="utf-8")
    assert rendered[0][1] == "voice.mp3"


def test_own_audio_without_whisper_estimates_timing(script, tmp_path, monkeypatch, rendered):
    monkeypatch.setattr(cli.align, "align_cues", lambda *a: None)
    cli.main(["render", str(script), "--audio", "voice.mp3"])
    assert rendered[0][0] == estimate_cues("Raport systemowy. Witamy z powrotem, załogo.")
    assert not (tmp_path / "intro_napisy.srt").exists()


def test_no_align_never_calls_whisper(script, monkeypatch, rendered):
    def boom(*a):
        raise AssertionError("Whisper must not run with --no-align")
    monkeypatch.setattr(cli.align, "align_cues", boom)
    cli.main(["render", str(script), "--audio", "voice.mp3", "--no-align"])
    assert rendered
```

`tests/test_golden.py`:

```python
import json

import pytest

from golden.harness import SCENARIOS, golden_path, requires_menlo, run_scenario
from muthur.cli import main

pytestmark = [pytest.mark.golden, requires_menlo]


@pytest.mark.parametrize("name", SCENARIOS)
def test_render_matches_prototype(name, tmp_path):
    expected = json.loads(golden_path(name).read_text(encoding="utf-8"))
    actual = run_scenario(name, lambda args: main(["render", *args]), tmp_path)
    assert actual["cmd"] == expected["cmd"]
    assert len(actual["frames"]) == len(expected["frames"])
    first_diff = next((i for i, (a, b) in enumerate(zip(actual["frames"], expected["frames"])) if a != b), None)
    assert first_diff is None, f"frame {first_diff} differs from the prototype"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_narration.py tests/test_cli.py tests/test_golden.py -v`
Expected: `ModuleNotFoundError: No module named 'muthur.narration'` / `'muthur.cli'`.

- [ ] **Step 3: Write `src/muthur/narration.py`**

```python
import os
import shutil
import subprocess
import sys

from muthur.timing import parse_srt


def edge_tts_cmd(voice, rate, mp3, *, file=None, text=None, srt=None):
    cmd = ["edge-tts", "--voice", voice, f"--rate={rate}"]
    cmd += ["--file", file] if file else [f"--text={text}"]
    cmd += ["--write-media", mp3]
    if srt:
        cmd += ["--write-subtitles", srt]
    return cmd


def require_edge_tts():
    if not shutil.which("edge-tts"):
        sys.exit("edge-tts not found: run `uv sync`")


def run_tts(text_file, voice, rate, workdir):
    require_edge_tts()
    mp3 = os.path.join(workdir, "narration.mp3")
    srt = os.path.join(workdir, "narration.srt")
    subprocess.run(edge_tts_cmd(voice, rate, mp3, file=text_file, srt=srt), check=True)
    return mp3, parse_srt(srt)
```

`test_run_tts_returns_sentence_cues` runs inside `uv run`, where `edge-tts` is on PATH, so `require_edge_tts` passes.

- [ ] **Step 4: Write `src/muthur/cli.py`**

```python
"""MU/TH/UR intro generator: text -> Polish narration + terminal-style video for TV.

  muthur render intro.txt                        # edge-tts narration -> intro.mp4
  muthur render intro.txt --image montero.jpg    # image behind the text
  muthur render intro.txt --voice pl-PL-MarekNeural --rate=-15%
  muthur render intro.txt --audio lektor.mp3     # own narration, subtitles aligned by Whisper
  muthur render intro.txt --no-tts               # silent preview, estimated timing
"""
import argparse
import os
import shutil
import tempfile

from muthur import align, mux, narration, render, timing


def build_parser():
    ap = argparse.ArgumentParser(prog="muthur", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="text file -> MU/TH/UR video")
    r.add_argument("text")
    r.add_argument("-o", "--out")
    r.add_argument("--image", help="background image (darkened behind the text)")
    r.add_argument("--voice", default="pl-PL-ZofiaNeural", help="or pl-PL-MarekNeural")
    r.add_argument("--rate", default="-10%", help="speech rate, e.g. --rate=-15%%")
    r.add_argument("--audio", help="use your own narration (e.g. from ElevenLabs) instead of edge-tts")
    r.add_argument("--srt", help="subtitles matching --audio (skips auto-alignment)")
    r.add_argument("--whisper-model", default="small",
                   help="model for aligning --audio: base (fast), small (default), medium (most accurate)")
    r.add_argument("--no-align", action="store_true", help="with --audio: estimate timing instead of Whisper")
    r.add_argument("--no-tts", action="store_true", help="no voice, estimated timing (preview)")
    r.add_argument("--no-hum", action="store_true", help="no ship-hum background")
    r.add_argument("--no-upper", action="store_true", help="keep original letter case")
    r.add_argument("--wrap", type=int, default=54, help="characters per line")
    r.add_argument("--font")
    r.add_argument("--title", default="MU/TH/UR 6000 :: USCSS MONTERO")
    return ap


def render_video(cues, audio, out, image, font_path, wrap, upper, hum, title):
    total, frames = render.iter_frames(cues, image, font_path, wrap, upper, title)
    mux.encode(frames, total, mux.ffmpeg_command(total, audio, hum, out), out)


def render_command(a):
    out = a.out or os.path.splitext(a.text)[0] + ".mp4"
    with open(a.text, encoding="utf-8") as f:
        raw = f.read().strip()

    with tempfile.TemporaryDirectory() as tmp:
        if a.audio:
            audio = a.audio
            if a.srt:
                cues = timing.parse_srt(a.srt)
            else:
                cues = None if a.no_align else align.align_cues(raw, audio, a.whisper_model)
                if cues is None:
                    cues = timing.estimate_cues(raw)
                else:
                    srt_out = os.path.splitext(out)[0] + "_napisy.srt"
                    timing.write_srt(cues, srt_out)
                    print(f"  subtitles saved: {srt_out} (fix by hand and pass with --srt if needed)")
        elif a.no_tts:
            audio, cues = None, timing.estimate_cues(raw)
        else:
            print(f"  narration: {a.voice} ({a.rate})")
            audio, cues = narration.run_tts(a.text, a.voice, a.rate, tmp)
            shutil.copy(audio, os.path.splitext(out)[0] + "_lektor.mp3")
        render_video(cues, audio, out, a.image, a.font, a.wrap, not a.no_upper, not a.no_hum, a.title)


def main(argv=None):
    a = build_parser().parse_args(argv)
    {"render": render_command}[a.command](a)
```

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v`
Expected: all PASS, including both `test_render_matches_prototype[preview]` and `[own_audio]`.

- [ ] **Step 6: Smoke-test the real entry point**

```fish
uv run muthur render intro.txt --no-tts -o /tmp/muthur-smoke.mp4
uv run muthur --help
```

Expected: `done: /tmp/muthur-smoke.mp4 (…s)`. The help lists `render`. Open the MP4 and check it looks like the prototype's `intro.mp4`, then delete it.

- [ ] **Step 7: Retire the prototype**

Delete `mother_intro.py`. In `tests/golden/record.py`, remove `prototype_main`, drop `str(ROOT)` from `sys.path`, and make the script record from the package without arguments:

```python
"""Re-record golden frame hashes after an intended look change: uv run python tests/golden/record.py"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from golden.harness import SCENARIOS, golden_path, run_scenario  # noqa: E402
from muthur.cli import main  # noqa: E402

for name in SCENARIOS:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_scenario(name, lambda args: main(["render", *args]), Path(tmp))
    golden_path(name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{name}: {len(result['frames'])} frames")
```

Run `uv run python tests/golden/record.py`, then `git diff --stat tests/golden/`. Expected: no diff (the package reproduces the prototype exactly). Run `uv run pytest`: all PASS.

- [ ] **Step 8: Commit**

```fish
git add src/muthur/narration.py src/muthur/cli.py tests/test_narration.py tests/test_cli.py tests/test_golden.py tests/golden/record.py
git rm mother_intro.py
git commit -m "feat: add muthur render command and retire the prototype script" -m "Golden frame hashes recorded from mother_intro.py match the package output exactly." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `muthur voices` audition command

**Files:**
- Modify: `src/muthur/narration.py` (add `DEFAULT_VOICES`, `SAMPLE`, `synthesize`, `find_player`, `audition`)
- Modify: `src/muthur/cli.py` (add `voices` subparser and `voices_command`)
- Test: `tests/test_narration.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `narration.edge_tts_cmd`, `narration.require_edge_tts`
- Produces:
  - `muthur.narration.DEFAULT_VOICES: list[str]`, `muthur.narration.SAMPLE: str`
  - `muthur.narration.synthesize(voice: str, rate: str, text: str, mp3: str) -> bool`
  - `muthur.narration.find_player() -> Callable[[str], object] | None` — `afplay` wrapper, or `None` if unavailable
  - `muthur.narration.audition(voices: list[str], text: str, rate: str, outdir: str, synth=synthesize, player=None) -> list[tuple[str, str]]` — `(voice, mp3)` for each voice that synthesised
  - `muthur.cli.voices_command(a: argparse.Namespace) -> None`

Default voices are the two native Polish voices plus four `*MultilingualNeural` voices. All six were confirmed with `edge-tts --list-voices` on 2026-10-14.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_narration.py`:

```python
def test_audition_plays_each_voice_in_order_and_skips_failures(tmp_path):
    played = []

    def synth(voice, rate, text, mp3):
        assert (rate, text) == ("-10%", "Witamy z powrotem, załogo.")
        if voice == "xx-XX-BrokenNeural":
            return False
        Path(mp3).write_bytes(b"mp3")
        return True

    results = narration.audition(["pl-PL-ZofiaNeural", "xx-XX-BrokenNeural", "pl-PL-MarekNeural"],
                                 "Witamy z powrotem, załogo.", "-10%", str(tmp_path),
                                 synth=synth, player=played.append)
    assert results == [("pl-PL-ZofiaNeural", str(tmp_path / "01_pl-PL-ZofiaNeural.mp3")),
                       ("pl-PL-MarekNeural", str(tmp_path / "03_pl-PL-MarekNeural.mp3"))]
    assert played == [mp3 for _, mp3 in results]


def test_find_player_is_none_without_afplay(monkeypatch):
    monkeypatch.setattr(narration.shutil, "which", lambda name: None)
    assert narration.find_player() is None


def test_default_voices_start_with_native_polish():
    assert narration.DEFAULT_VOICES[:2] == ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]
```

Append to `tests/test_cli.py`:

```python
@pytest.fixture
def auditioned(monkeypatch):
    calls = []

    def fake_audition(voices, text, rate, outdir, player=None):
        calls.append({"voices": voices, "text": text, "rate": rate, "outdir": outdir, "player": player})
        return [(v, os.path.join(outdir, f"{v}.mp3")) for v in voices]

    monkeypatch.setattr(cli.narration, "audition", fake_audition)
    return calls


def test_voices_defaults(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices"])
    (call,) = auditioned
    assert call["voices"] == cli.narration.DEFAULT_VOICES
    assert (call["text"], call["rate"], call["player"]) == (cli.narration.SAMPLE, "-10%", print)


def test_voices_repeatable_voice_and_equals_rate(monkeypatch, auditioned):
    monkeypatch.setattr(cli.narration, "find_player", lambda: print)
    cli.main(["voices", "--voice", "pl-PL-MarekNeural", "--voice", "de-DE-SeraphinaMultilingualNeural",
              "--rate=-15%", "--text", "Matka was obudziła."])
    assert auditioned[0]["voices"] == ["pl-PL-MarekNeural", "de-DE-SeraphinaMultilingualNeural"]
    assert auditioned[0]["rate"] == "-15%"


def test_voices_without_afplay_saves_samples(tmp_path, monkeypatch, auditioned):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.narration, "find_player", lambda: None)
    cli.main(["voices"])
    assert auditioned[0]["outdir"] == "audition"
    assert auditioned[0]["player"] is None
    assert (tmp_path / "audition").is_dir()


def test_voices_fails_when_nothing_synthesised(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.narration, "find_player", lambda: None)
    monkeypatch.setattr(cli.narration, "audition", lambda *a, **k: [])
    with pytest.raises(SystemExit, match="no voice"):
        cli.main(["voices", "--no-play"])
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_narration.py tests/test_cli.py -v`
Expected: new tests FAIL (`AttributeError: module 'muthur.narration' has no attribute 'audition'`, `invalid choice: 'voices'`).

- [ ] **Step 3: Implement in `src/muthur/narration.py`**

Add after `run_tts`:

```python
DEFAULT_VOICES = [
    "pl-PL-ZofiaNeural",
    "pl-PL-MarekNeural",
    "de-DE-SeraphinaMultilingualNeural",
    "de-DE-FlorianMultilingualNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
]
SAMPLE = "Procedura wybudzania zakończona. Witamy z powrotem, załogo."


def synthesize(voice, rate, text, mp3):
    require_edge_tts()
    return subprocess.run(edge_tts_cmd(voice, rate, mp3, text=text)).returncode == 0


def find_player():
    afplay = shutil.which("afplay")
    if not afplay:
        return None
    return lambda mp3: subprocess.run([afplay, mp3])


def audition(voices, text, rate, outdir, synth=synthesize, player=None):
    results = []
    for i, voice in enumerate(voices, 1):
        mp3 = os.path.join(outdir, f"{i:02}_{voice}.mp3")
        print(f"  [{i}/{len(voices)}] {voice}")
        if not synth(voice, rate, text, mp3):
            print(f"  ! {voice}: synthesis failed, skipping")
            continue
        results.append((voice, mp3))
        if player:
            player(mp3)
    return results
```

- [ ] **Step 4: Implement in `src/muthur/cli.py`**

Add `import sys`. In `build_parser`, before `return ap`:

```python
    v = sub.add_parser("voices", help="read a sample sentence with several voices and play them in turn")
    v.add_argument("--voice", action="append",
                   help=f"repeatable; default: {', '.join(narration.DEFAULT_VOICES)}")
    v.add_argument("--text", default=narration.SAMPLE)
    v.add_argument("--rate", default="-10%", help="speech rate, e.g. --rate=-15%%")
    v.add_argument("--keep", metavar="DIR", help="save the samples in DIR")
    v.add_argument("--no-play", action="store_true", help="only save the samples")
```

Add the command and register it in `main`:

```python
def voices_command(a):
    voices = a.voice or narration.DEFAULT_VOICES
    player = None if a.no_play else narration.find_player()
    keep = a.keep or (None if player else "audition")
    if keep:
        os.makedirs(keep, exist_ok=True)
        results = narration.audition(voices, a.text, a.rate, keep, player=player)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            results = narration.audition(voices, a.text, a.rate, tmp, player=player)
    if not results:
        sys.exit("no voice could be synthesised (check the voice names and your network)")
    if keep:
        print(f"  samples saved in {keep}/")


def main(argv=None):
    a = build_parser().parse_args(argv)
    {"render": render_command, "voices": voices_command}[a.command](a)
```

- [ ] **Step 5: Run tests, then try it for real**

Run: `uv run pytest -v` → all PASS.

```fish
uv run muthur voices --voice pl-PL-MarekNeural --voice de-DE-SeraphinaMultilingualNeural
```

Expected: two numbered voice names are printed and each sample plays through `afplay` (needs network). Then `uv run muthur voices --voice xx-XX-NopeNeural` → edge-tts error, then `no voice could be synthesised …`, exit code 1.

- [ ] **Step 6: Commit**

```fish
git add src/muthur/narration.py src/muthur/cli.py tests/test_narration.py tests/test_cli.py
git commit -m "feat: add muthur voices command to audition edge-tts voices" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Unicode and hand-edited SRT robustness (deliberate behaviour change)

**Files:**
- Modify: `src/muthur/text.py` (add `read_text`; NFC in `norm_word`)
- Modify: `src/muthur/timing.py` (`parse_srt` via `read_text`; `srt_time` pads short fractions)
- Modify: `src/muthur/narration.py` (`run_tts` takes the script text)
- Modify: `src/muthur/cli.py` (`render_command` reads via `read_text`, passes text to `run_tts`)
- Test: `tests/test_text.py`, `tests/test_timing.py`, `tests/test_narration.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `muthur.text.read_text(path: str) -> str` — UTF-8 with any BOM dropped, NFC-normalised
  - `muthur.narration.run_tts(text: str, voice: str, rate: str, workdir: str) -> tuple[str, list[list]]` — **signature change**: first argument is now the script text, written to `<workdir>/script.txt` for edge-tts

This task fixes Review Focus items 1–3. The golden fixtures are NFC without a BOM, so the golden hashes must not change.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_text.py`:

```python
import unicodedata

from muthur.text import read_text

NFD = unicodedata.normalize("NFD", "Żółć gęślą jaźń.")


def test_read_text_drops_bom_and_composes_diacritics(tmp_path):
    path = tmp_path / "intro.txt"
    path.write_bytes(b"\xef\xbb\xbf" + NFD.encode("utf-8"))
    assert read_text(str(path)) == "Żółć gęślą jaźń."


def test_norm_word_matches_decomposed_input():
    assert norm_word(unicodedata.normalize("NFD", "Żółć,")) == "żółć"
```

Append to `tests/test_timing.py`:

```python
import unicodedata


def test_srt_time_pads_shortened_fraction():
    assert srt_time("00:00:12,5") == pytest.approx(12.5)
    assert srt_time("00:00:12.25") == pytest.approx(12.25)


def test_parse_srt_with_bom_and_decomposed_text(tmp_path):
    srt = tmp_path / "napisy.srt"
    srt.write_bytes(b"\xef\xbb\xbf" + unicodedata.normalize(
        "NFD", "1\n00:00:00,000 --> 00:00:01,000\nŻółć gęślą jaźń.\n").encode("utf-8"))
    assert parse_srt(str(srt)) == [[0.0, 1.0, "Żółć gęślą jaźń."]]
```

In `tests/test_narration.py`, replace `test_run_tts_returns_sentence_cues` with:

```python
def test_run_tts_reads_the_given_text(tmp_path, monkeypatch):
    seen = []

    def fake_run(cmd, check):
        seen.append(cmd)
        seen.append(Path(cmd[cmd.index("--file") + 1]).read_text(encoding="utf-8"))
        Path(cmd[cmd.index("--write-subtitles") + 1]).write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nKurs został\n\n"
            "2\n00:00:01,000 --> 00:00:02,000\nskorygowany.\n", encoding="utf-8")

    monkeypatch.setattr(narration.subprocess, "run", fake_run)
    mp3, cues = narration.run_tts("Kurs został skorygowany.", "pl-PL-ZofiaNeural", "-10%", str(tmp_path))
    assert seen == [["edge-tts", "--voice", "pl-PL-ZofiaNeural", "--rate=-10%",
                     "--file", str(tmp_path / "script.txt"),
                     "--write-media", str(tmp_path / "narration.mp3"),
                     "--write-subtitles", str(tmp_path / "narration.srt")],
                    "Kurs został skorygowany."]
    assert mp3 == str(tmp_path / "narration.mp3")
    assert cues == [[0.0, 2.0, "Kurs został skorygowany."]]
```

Append to `tests/test_cli.py`:

```python
def test_decomposed_bom_script_reaches_tts_and_screen_composed(tmp_path, monkeypatch, rendered):
    import unicodedata
    path = tmp_path / "intro.txt"
    path.write_bytes(b"\xef\xbb\xbf" + unicodedata.normalize("NFD", "Matka was obudziła.\n").encode("utf-8"))
    spoken = []

    def fake_tts(text, voice, rate, workdir):
        spoken.append(text)
        mp3 = os.path.join(workdir, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, text]]

    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(path)])
    assert spoken == ["Matka was obudziła."]
    assert rendered[0][0] == [[0.0, 1.0, "Matka was obudziła."]]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_text.py tests/test_timing.py tests/test_narration.py tests/test_cli.py -v`
Expected: the new tests FAIL (`ImportError: cannot import name 'read_text'`, `12.005 != 12.5`, `KeyError`/assert mismatch on `script.txt`).

- [ ] **Step 3: Implement**

`src/muthur/text.py`:

```python
import re
import unicodedata


def read_text(path):
    with open(path, encoding="utf-8-sig") as f:
        return unicodedata.normalize("NFC", f.read())


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def norm_word(w):
    return re.sub(r"[^0-9a-ząćęłńóśźż]", "", unicodedata.normalize("NFC", w).lower())
```

`src/muthur/timing.py`: change the import to `from muthur.text import read_text, split_sentences`, and:

```python
def srt_time(s):
    h, m, rest = s.strip().split(":")
    sec, frac = re.split(r"[,.]", rest)
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(frac.ljust(3, "0")[:3]) / 1000


def parse_srt(path):
    cues = []
    blocks = re.split(r"\n\s*\n", read_text(path).strip())
    ...  # rest unchanged
```

`src/muthur/narration.py`, `run_tts`:

```python
def run_tts(text, voice, rate, workdir):
    require_edge_tts()
    script = os.path.join(workdir, "script.txt")
    with open(script, "w", encoding="utf-8") as f:
        f.write(text)
    mp3 = os.path.join(workdir, "narration.mp3")
    srt = os.path.join(workdir, "narration.srt")
    subprocess.run(edge_tts_cmd(voice, rate, mp3, file=script, srt=srt), check=True)
    return mp3, parse_srt(srt)
```

`src/muthur/cli.py`, in `render_command`: import `from muthur.text import read_text`, replace the `with open(...)` block with `raw = read_text(a.text).strip()`, and change the TTS call to `narration.run_tts(raw, a.voice, a.rate, tmp)`.

- [ ] **Step 4: Run the full suite, golden included**

Run: `uv run pytest -v`
Expected: all PASS. The golden tests must still match. If they don't, the change leaked into rendering, so fix the code, never the JSON.

- [ ] **Step 5: Commit**

```fish
git add src/muthur tests
git commit -m "fix: accept BOM, decomposed Polish diacritics and short SRT fractions" -m "Text from macOS copy-paste can arrive in NFD, which made norm_word turn żółć into zołc and broke Whisper alignment. A hand-edited 00:00:12,5 parsed as 12.005 s." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: README and CLAUDE.md

**Files:**
- Create: `README.md`
- Modify: `CLAUDE.md` (replace the prototype-era Commands/Pipeline sections)

**Interfaces:** none (documentation). Every command shown must have been run once while writing it.

- [ ] **Step 1: Write `README.md`**

````markdown
# muthur-voice

Turns a text file into a short video for a TV screen: a voice narration plus on-screen text styled
as the MU/TH/UR ship computer from the Alien films: green monospace terminal, typewriter text synced
to the voice, CRT scanlines, phosphor glow, blinking cursor, low ship hum. Built for Alien RPG
(OBCY) sessions, for example an intro where Mother wakes the crew from hypersleep. Polish first.

## Setup (macOS, fish)

```fish
brew install ffmpeg uv
uv sync                    # add --extra align to align your own recordings with Whisper
```

The output is a 1080p H.264 MP4 that plays from a USB stick on any TV.

## Usage

```fish
uv run muthur render intro.txt                          # Polish edge-tts narration -> intro.mp4
uv run muthur render intro.txt --no-tts                 # silent preview, estimated timing
uv run muthur render intro.txt --image montero.jpg      # darkened, green-tinted image behind the text
uv run muthur render intro.txt --voice pl-PL-MarekNeural --rate=-15%
uv run muthur render intro.txt --audio lektor.mp3       # own recording (e.g. ElevenLabs), Whisper aligns subtitles
uv run muthur render intro.txt --audio lektor.mp3 --srt intro_napisy.srt   # after fixing timing by hand
```

Options whose value starts with `-` need the `=` form: `--rate=-15%`, not `--rate -15%`.

Files written next to the video (`-o` changes the base name):

| Mode | Files |
|---|---|
| edge-tts (default) | `intro.mp4`, `intro_lektor.mp3` (the narration) |
| `--audio` with Whisper | `intro.mp4`, `intro_napisy.srt` (edit it, then pass it back with `--srt`) |
| `--no-tts`, `--audio --srt` | `intro.mp4` |

### Choosing a voice

edge-tts has two native Polish voices (`pl-PL-ZofiaNeural`, `pl-PL-MarekNeural`). The
`*MultilingualNeural` voices can read Polish too, sometimes more naturally. To hear a sample
sentence in each default candidate:

```fish
uv run muthur voices
uv run muthur voices --voice pl-PL-MarekNeural --voice de-DE-SeraphinaMultilingualNeural --rate=-15%
uv run muthur voices --text "Dlaczego Matka was obudziła?" --keep audition
edge-tts --list-voices | grep -E 'pl-PL|Multilingual'    # all candidates (run inside `uv run` or the venv)
```

Without `afplay` (Linux), samples are saved in `audition/` instead of played.

## Development

```fish
uv run pytest                          # everything (golden tests take ~20 s)
uv run pytest -m "not golden"          # fast loop
uv run pytest tests/test_align.py::test_missing_middle_sentence_fills_the_gap -v
```

The golden tests compare the SHA-256 of every rendered frame with hashes recorded from the
original prototype. They need Menlo (macOS). After an intended visual change, check the new
video by eye, then re-record with `uv run python tests/golden/record.py`.

## License

Apache License 2.0, see `LICENSE`.
````

- [ ] **Step 2: Rewrite `CLAUDE.md`**

Keep the header and the "What this is" / "Constraints" sections. Remove the sentence "Currently a single-file prototype … There is no build, lint, or test suite yet; verification means rendering a video and checking it." and replace it with:

```markdown
The original prototype (`mother_intro.py`, removed; see git history) defines the visual style.
Refactor the look, don't redesign it: `tests/test_golden.py` compares every frame's SHA-256 with
hashes recorded from that prototype.
```

Replace `## Commands` and `## Pipeline` with:

````markdown
## Commands

```fish
uv sync --extra align                  # venv in .venv; the extra adds faster-whisper
uv run pytest                          # all tests (golden ~20 s, needs Menlo)
uv run pytest -m "not golden"          # fast loop
uv run pytest tests/test_timing.py::test_merges_cues_split_mid_sentence -v
uv run muthur render intro.txt --no-tts -o /tmp/x.mp4   # quickest real render
uv run python tests/golden/record.py   # re-record golden hashes, only after an intended look change
```

Value options starting with `-` need `=` (`--rate=-15%`). `lektor.mp3` in the root is the user's own
recording; never overwrite it. Media files are gitignored.

## Architecture

Everything converges on **cues**: mutable `[start_sec, end_sec, sentence]` lists relative to the
start of the audio. `cli.render_command` picks the source:

- edge-tts → `narration.run_tts` → SRT → `timing.parse_srt` (merges mid-sentence cues)
- `--audio` → `align.align_cues` = `transcribe` (faster-whisper, Polish, script as prompt) +
  `match_cues` (pure difflib match; missing sentences interpolated by length, then forced monotonic)
- `--srt` → `timing.parse_srt`; `--no-tts` or no Whisper → `timing.estimate_cues`

`text.split_sentences` and `text.norm_word` define sentence and word identity for both the screen
and alignment. All file text goes through `text.read_text` (BOM dropped, NFC).

`render.iter_frames` shifts cues by `LEAD_IN` and lazily yields raw RGB frames.
`mux.ffmpeg_command` delays the voice by the same `LEAD_IN` (`adelay`), so the two must change
together. `mux.encode` pipes the frames into ffmpeg's stdin. Rendering runs at about 2.5× real time.

`narration.audition` (behind `muthur voices`) synthesises one sentence per voice and plays it with
`afplay`.
````

- [ ] **Step 3: Verify every documented command**

Run each command from the README Development section and the CLAUDE.md Commands section once (the `render` ones with `--no-tts` and `-o /tmp/...`). Run `uv run muthur voices --voice pl-PL-MarekNeural` once (needs network). Fix any command that doesn't work as written.

- [ ] **Step 4: Commit**

```fish
git add README.md CLAUDE.md
git commit -m "docs: add README and update CLAUDE.md for the package layout" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Verify Whisper alignment on the real recording

**Files:** none changed unless a defect is found. The deliverable is a short report to the user.

The brief says alignment has only been tested against a simulated transcript. `lektor.mp3` in the project root is the user's own narration of `intro.txt`. **Before starting, confirm with the user that it is a reading of the current `intro.txt`.**

- [ ] **Step 1: Run the alignment end to end**

```fish
uv run muthur render intro.txt --audio lektor.mp3 -o /tmp/muthur-real.mp4
```

Expected: `matched N/16 sentences` (`intro.txt` splits into 16 sentences) and `/tmp/muthur-real_napisy.srt` is written. The first run downloads the `small` model.

- [ ] **Step 2: Check the timing by ear and eye**

Play `/tmp/muthur-real.mp4`. For each sentence, write down whether its typing starts within roughly half a second of when it is spoken. Compare with `/tmp/muthur-real_napisy.srt`.

- [ ] **Step 3: Repeat with `--whisper-model base` and `--whisper-model medium`**

Record `matched N/16` for each and any visible drift.

- [ ] **Step 4: Report**

Tell the user: matched counts per model, which sentences (if any) drift or got interpolated, and a recommendation for the default model. If alignment is wrong, **do not fix it inside this plan**. Open it as a separate debugging task (superpowers:systematic-debugging) with the SRT and the observations attached. Delete the `/tmp/muthur-real*` files afterwards.
