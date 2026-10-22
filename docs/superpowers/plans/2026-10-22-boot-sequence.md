# Boot Sequence Block Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An optional `[BOOT start]` … `[BOOT end]` block at the top of the intro file plays a typed MU/TH/UR boot screen (plain lines, progress bars, dot-leader statuses, counting values) with typing clicks before the narrated intro.

**Architecture:** A new `muthur/boot.py` parses the block into steps and lays them out on a timeline (`Boot`: duration, click times, screen lines at time t). `cli.render_command` splits the file, sends only the narrated text to TTS/alignment, and passes the `Boot` to rendering; `render.iter_frames` draws boot frames first and shifts the narrated cues by `boot.duration`; `mux.ffmpeg_command` delays the voice by the same amount and mixes a click WAV synthesised with the standard library.

**Tech Stack:** Python 3.14 stdlib (`re`, `difflib`, `wave`, `array`, `random`, `dataclasses`), Pillow, ffmpeg, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-22-boot-sequence-design.md`

## Global Constraints

- A file with no boot block renders byte-identically to today: `tests/test_golden.py` (frames **and** ffmpeg command) passes unchanged. Every new parameter defaults to today's behaviour.
- Boot text never reaches `narration.run_tts`, `align.align_cues`, `timing.estimate_cues`, `_napisy.srt` or `_lektor.mp3`.
- Voice delay and narrated-cue shift are both `boot.duration + LEAD_IN` (just `LEAD_IN` with no block). Cues stay relative to the audio.
- Polish letters (ą ć ę ł ń ó ś ź ż) survive parsing, upper-casing and drawing. `label` is never upper-cased; `text`, Status values and plain lines follow `--upper`.
- No bundled audio file and no new runtime dependency.
- Timing defaults: `--boot-type-speed 22` (letters/s), `--boot-status-pause 0.7`, `--boot-bar-time 1.5`, `--boot-count-time 2.0`, `--boot-hold 2.0` (seconds), `--boot-clicks/--no-boot-clicks` on. Gap between steps 0.25 s (constant, not a flag).
- Bar: 15 segments, `█` filled, `░` empty. Dot-leader column = longest `text` among Status/ProgressValue lines + 1 space + at least 3 dots + 1 space.
- Errors exit via `sys.exit` with a message naming the line number in the intro file, like `timing.parse_srt` does.
- Docs and commands assume fish; run everything with `uv run`.

## Review Focus

1. **Boot text leaking into narration** — a file with a block sent whole to edge-tts would read the tags aloud. Pinned in Task 6 (`test_tts_gets_only_the_narrated_text`).
2. **Voice and screen drifting apart** — a block with `--audio` must delay the voice by exactly the shift applied to the cues. Pinned in Task 6 (`test_boot_shifts_voice_and_cues_by_the_same_amount`).
3. **Commas inside `text`** (`text: SYSTEM, PODSYSTEM`) — the user expects the whole text, not a parse error. Pinned in Task 2 (`test_text_may_contain_commas`).
4. **Blank lines or whitespace before `[BOOT start]`** — the user expects the block to still count as "at the top". Pinned in Task 2 (`test_leading_blank_lines_before_the_block_are_ignored`).
5. **Zero or negative timing in `muthur.toml`** (`boot_type_speed = 0`) — expected: a clear error, not a ZeroDivisionError mid-render. Pinned in Task 6 (`test_non_positive_type_speed_is_rejected`).

---

### Task 1: Decimal numbers in `muthur.toml`

**Files:**
- Modify: `src/muthur/config.py` (the type checks in `defaults`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: any `render`/`voices` flag declared with `type=float` accepts a TOML int or float (stored as `float`) and rejects booleans and strings with `"{where} must be a number"`.

- [ ] **Step 1: Write the failing tests** — this task can't add the real `--boot-hold` flag yet, so the tests add a throwaway `type=float` option to the render subparser via a fixture that wraps `cli.build_parser` (monkeypatch `cli.build_parser` to call the original and then `subcommands(p)["render"].add_argument("--pace", type=float, default=1.0)`).

```python
@pytest.mark.parametrize("content, expected", [("pace = 2.5", 2.5), ("pace = 2", 2.0)])
def test_number_setting_accepts_decimals_and_whole_numbers(toml, float_flag, content, expected):
    toml(f"[render]\n{content}\n")
    assert cli.parse_args(["render", "intro.txt"]).pace == expected

@pytest.mark.parametrize("content", ['pace = "2.5"', "pace = true"])
def test_number_setting_rejects_strings_and_booleans(toml, float_flag, content):
    toml(f"[render]\n{content}\n")
    with pytest.raises(SystemExit, match=r"\]\.pace must be a number"):
        cli.parse_args(["render", "intro.txt"])
```

- [ ] **Step 2: Run** `uv run pytest tests/test_config.py -k number_setting -v` — Expected: FAIL (`must be a string`).
- [ ] **Step 3: Add an `elif action.type is float:` branch** next to the `int` branch in `config.defaults`; check `isinstance(value, (int, float)) and not isinstance(value, bool)`, store `float(value)`.
- [ ] **Step 4: Run** `uv run pytest tests/test_config.py -v` — Expected: all PASS.
- [ ] **Step 5: Commit** `feat: accept decimal numbers in muthur.toml`

---

### Task 2: Parse the boot block

**Files:**
- Create: `src/muthur/boot.py`
- Test: `tests/test_boot.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Step: kind: str; text: str; line: int; value: str = ""; start: int = 0; end: int = 0; label: str = ""` — `kind` is one of `"line"`, `"blank"`, `"bar"` (ProgressBar), `"status"`, `"count"` (ProgressValue). `line` is the 1-based line number in the file.
  - `split_boot(text: str) -> tuple[list[Step], str]` — returns `([], text)` unchanged when there is no block; otherwise the steps and the narrated text after `[BOOT end]` (stripped).

Grammar: markers `[BOOT start]`, `[BOOT end]`, `[CRT start]`, `[CRT end]`, case-insensitive, inner spaces optional. A tag line is `[Name: first, key: value, ...]`; split the inside on the first `:` into name and rest; `first` is everything up to the first `, key:` where key is `text` or `label` (case-insensitive); each key's value runs to the next `, text:`/`, label:` or the end, so commas inside values survive. Ranges match `^-?\d+\s*\.\.\s*-?\d+$`. Upper-casing is **not** done here.

Errors (each `sys.exit`, message contains `line N`):
- unknown tag → `line 3: unknown tag ProgresBar (did you mean ProgressBar?)` (use `difflib.get_close_matches` over `ProgressBar`, `ProgressValue`, `Status`);
- missing `text:`; bad range; `[BOOT start]` without `[BOOT end]`; a block that does not start on the first non-blank line; a second block; a tag outside the block;
- empty narrated text after the block → `nothing to narrate after [BOOT end]`.

- [ ] **Step 1: Write the failing tests**

```python
EXAMPLE = """[BOOT start]
WZNAWIANIE SYSTEMÓW POKŁADOWYCH
[ProgressBar: 1..100, label: %, text: ROZRUCH REAKTORA]
[Status: AKTYWNE, text: System podtrzymywania życia]

[ProgressValue: -10..21, label: °C, text: TEMPERATURA POKŁADU]
[BOOT end]
Raport systemowy."""

def test_splits_steps_from_the_narrated_text():
    steps, narrated = split_boot(EXAMPLE)
    assert narrated == "Raport systemowy."
    assert steps == [
        Step("line", "WZNAWIANIE SYSTEMÓW POKŁADOWYCH", 2),
        Step("bar", "ROZRUCH REAKTORA", 3, start=1, end=100, label="%"),
        Step("status", "System podtrzymywania życia", 4, value="AKTYWNE"),
        Step("blank", "", 5),
        Step("count", "TEMPERATURA POKŁADU", 6, start=-10, end=21, label="°C"),
    ]

def test_file_without_a_block_is_returned_unchanged():
    assert split_boot("Raport systemowy.\nKoniec.") == ([], "Raport systemowy.\nKoniec.")

@pytest.mark.parametrize("start, end", [("[crt start]", "[CRT END]"), ("[Boot Start]", "[boot end]")])
def test_markers_ignore_case_and_crt_is_an_alias(start, end):
    assert split_boot(f"{start}\nA\n{end}\nB.")[0] == [Step("line", "A", 2)]

def test_tag_names_and_keys_ignore_case():
    steps, _ = split_boot("[BOOT start]\n[status: OK, TEXT: zasilanie]\n[BOOT end]\nB.")
    assert steps == [Step("status", "zasilanie", 2, value="OK")]

def test_text_may_contain_commas():
    steps, _ = split_boot("[BOOT start]\n[Status: OK, text: SYSTEM, PODSYSTEM]\n[BOOT end]\nB.")
    assert steps[0].text == "SYSTEM, PODSYSTEM"

def test_leading_blank_lines_before_the_block_are_ignored():
    steps, narrated = split_boot("\n  \n[BOOT start]\nA\n[BOOT end]\nB.")
    assert steps == [Step("line", "A", 4)] and narrated == "B."

@pytest.mark.parametrize("source, message", [
    ("[BOOT start]\n[ProgresBar: 1..100, text: R]\n[BOOT end]\nB.", r"line 2: unknown tag ProgresBar \(did you mean ProgressBar\?\)"),
    ("[BOOT start]\n[Status: OK]\n[BOOT end]\nB.", r"line 2: .*text"),
    ("[BOOT start]\n[ProgressValue: 1-5, text: T]\n[BOOT end]\nB.", r"line 2: .*range"),
    ("[BOOT start]\nA\nB.", r"line 1: .*\[BOOT end\]"),
    ("Wstęp.\n[BOOT start]\nA\n[BOOT end]\nB.", r"line 2: .*top"),
    ("[BOOT start]\nA\n[BOOT end]\nB.\n[Status: OK, text: T]", r"line 5: "),
    ("[BOOT start]\nA\n[BOOT end]\n", r"nothing to narrate"),
])
def test_malformed_blocks_name_the_line(source, message):
    with pytest.raises(SystemExit, match=message):
        split_boot(source)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_boot.py -v` — Expected: FAIL (`ModuleNotFoundError: muthur.boot`).
- [ ] **Step 3: Implement `Step` and `split_boot`** in `src/muthur/boot.py` per the grammar above.
- [ ] **Step 4: Run** `uv run pytest tests/test_boot.py -v` — Expected: all PASS.
- [ ] **Step 5: Commit** `feat: parse the [BOOT start] block in the intro file`

---

### Task 3: Lay the boot screen out on a timeline

**Files:**
- Modify: `src/muthur/boot.py`
- Test: `tests/test_boot.py`

**Interfaces:**
- Consumes: `Step`, `split_boot` (Task 2).
- Produces:
  - `@dataclass(frozen=True) class Timing: type_speed: float = 22.0; status_pause: float = 0.7; bar_time: float = 1.5; count_time: float = 2.0; hold: float = 2.0; gap: float = 0.25`
  - `BAR_WIDTH = 15`, `FILLED = "█"`, `EMPTY = "░"`
  - `class Boot` with attributes `duration: float`, `clicks: list[float]` (seconds from video start, one per typed non-space character) and method `lines_at(t: float) -> list[str]` (screen lines at time t, finished lines plus the one in progress; `[]` before anything is typed).
  - `plan(steps: list[Step], timing: Timing, wrap: int, upper: bool) -> Boot`

Per-step behaviour (each step starts after the previous one ends + `timing.gap`; the first starts at 0):
- `line`: typed at `type_speed`; finished line = text.
- `blank`: no time beyond the gap; finished line = `""`.
- `status`: types `lead(text)`, waits `status_pause`, then `lead(text) + value` appears at once.
- `bar`: types `text + " "`, then over `bar_time` shows `text + " " + FILLED*n + EMPTY*(15-n) + "  " + f"{v}{label}"` with `p` = progress 0→1, `n = round(15*p)`, `v = round(start + (end-start)*p)`; finished = fully filled at `end`.
- `count`: types `lead(text)`, then over `count_time` shows `lead(text) + f"{v}{label}"` stepping through whole numbers `start..end`; finished at `end`.
- `lead(text) = text + " " + "." * (col - len(text) - 2) + " "` where `col = max(len(text) for status/count steps) + 5`, so the shortest leader has 3 dots and every value starts at column `col`.
- `duration` = end of the last step + `hold`.
- `upper=True` upper-cases `text`, `value` and plain lines, never `label`.
- A finished line longer than `wrap` exits with `line N: ... is X characters, --wrap is W`.

- [ ] **Step 1: Write the failing tests**

```python
T = Timing(type_speed=10, status_pause=1, bar_time=1, count_time=1, hold=2, gap=0)

def test_line_is_typed_at_the_type_speed():
    boot = plan([Step("line", "abcd", 1)], T, 54, False)
    assert boot.lines_at(0.15) == ["ab"]  # letter i appears at i / type_speed
    assert boot.lines_at(0.45) == ["abcd"]
    assert boot.duration == pytest.approx(0.4 + 2)

def test_clicks_fall_on_typed_letters_but_not_spaces():
    assert plan([Step("line", "a b", 1)], T, 54, False).clicks == pytest.approx([0.0, 0.2])

def test_status_values_line_up_after_the_pause():
    steps = [Step("status", "ATMOSFERA", 1, value="OK"), Step("status", "OŚWIETLENIE", 2, value="WŁĄCZONE")]
    boot = plan(steps, T, 54, False)
    final = boot.lines_at(boot.duration)
    assert final == ["ATMOSFERA ..... OK", "OŚWIETLENIE ... WŁĄCZONE"]
    typed = len("ATMOSFERA ..... ") / 10
    assert boot.lines_at(typed + 0.5) == ["ATMOSFERA ..... "]

def test_bar_fills_and_counts_to_the_end_value():
    boot = plan([Step("bar", "R", 1, start=1, end=100, label="%")], T, 54, False)
    assert boot.lines_at(0.2 + 0.4) == ["R " + "█" * 6 + "░" * 9 + "  " + "41%"]
    assert boot.lines_at(boot.duration) == ["R " + "█" * 15 + "  100%"]

def test_value_counts_through_whole_numbers():
    boot = plan([Step("count", "T", 1, start=-10, end=21, label="°C")], T, 54, False)
    assert boot.lines_at(boot.duration)[0].endswith("21°C")
    assert boot.lines_at(len("T ... ") / 10)[0].endswith("-10°C")

def test_upper_casing_skips_the_label():
    boot = plan([Step("count", "ciśnienie", 1, start=1, end=2, label="kPa")], T, 54, True)
    assert boot.lines_at(boot.duration) == ["CIŚNIENIE ... 2kPa"]

def test_line_wider_than_wrap_names_the_line():
    with pytest.raises(SystemExit, match=r"line 7: .*--wrap is 10"):
        plan([Step("status", "TEMPERATURA", 7, value="OK")], T, 10, False)
```

- [ ] **Step 2: Run** `uv run pytest tests/test_boot.py -v` — Expected: new tests FAIL (`ImportError: plan`).
- [ ] **Step 3: Implement `Timing`, `Boot` and `plan`** in `src/muthur/boot.py` as specified; keep `Boot` a plain class holding per-step `(start, end, frames_fn)` so `lines_at` is a pure lookup.
- [ ] **Step 4: Run** `uv run pytest tests/test_boot.py -v` — Expected: all PASS.
- [ ] **Step 5: Commit** `feat: lay the boot screen out on a timeline`

---

### Task 4: Draw the boot frames before the narration

**Files:**
- Modify: `src/muthur/render.py` (`timeline`, `iter_frames`, `_frames`, new `render_boot_layer`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `Boot.lines_at`, `Boot.duration` (Task 3).
- Produces: `timeline(cues, offset=0.0)` shifts by `offset + LEAD_IN`; `iter_frames(cues, image, font_path, wrap, upper, title, boot=None) -> (total, frames)`; with a boot, `total` grows by exactly `boot.duration`.

Frames with `t < boot.duration` draw `render_boot_layer(boot.lines_at(t), font, line_h, max_lines, cursor_on)` instead of `render_text_layer`: same `x0=140, y0=140`, font, `line_h`, `max_lines` (keep the last `max_lines`), every line `GREEN`, no `> ` prefix, cursor after the last line (on an empty first line when there are none). Glow, scanlines, flicker and the power-on fade apply to all frames as today. Narrated frames are unchanged apart from the shift.

- [ ] **Step 1: Write the failing tests**

```python
def test_timeline_offset_adds_to_the_lead_in():
    shifted, total = timeline([[0.0, 1.0, "A."]], offset=5.0)
    assert shifted == [[7.0, 8.0, "A."]] and total == pytest.approx(8.0 + render.TAIL)

def test_boot_lengthens_the_video_by_its_duration():
    cues = estimate_cues("Raport systemowy.")
    boot = plan([Step("line", "WZNAWIANIE", 1)], Timing(), 54, True)
    plain, _ = iter_frames(cues, None, None, 54, True, "T")
    longer, _ = iter_frames(cues, None, None, 54, True, "T", boot=boot)
    assert longer == pytest.approx(plain + boot.duration)

@requires_menlo
@pytest.mark.parametrize("ch", ["█", "░"])
def test_default_font_draws_the_bar_glyphs(ch):
    font = load_font(46)
    assert _glyph(font, ch) != _glyph(font, "͸")
```

- [ ] **Step 2: Run** `uv run pytest tests/test_render.py -v` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** the `offset`/`boot` parameters and `render_boot_layer`.
- [ ] **Step 4: Run** `uv run pytest tests/test_render.py tests/test_golden.py -v` — Expected: all PASS, golden unchanged.
- [ ] **Step 5: Commit** `feat: draw the boot screen before the narration`

---

### Task 5: Typing clicks and the voice delay in the mix

**Files:**
- Modify: `src/muthur/mux.py`
- Test: `tests/test_mux.py`

**Interfaces:**
- Produces:
  - `write_clicks(times: list[float], total: float, path: str) -> None` — 44100 Hz mono 16-bit WAV of length `total`, a short decaying noise burst (~6 ms, fixed `random.Random` seed) starting at each time; stdlib `wave` + `array` only.
  - `ffmpeg_command(total, audio, hum, out, fx="echo", delay=LEAD_IN, clicks=None)` — `adelay` uses `int(delay * 1000)`; when `clicks` is a path, adds `-i clicks` as the next input with filter `[{n}:a]anull[c]` and includes `[c]` in the `amix`. Defaults reproduce today's command exactly.

- [ ] **Step 1: Write the failing tests**

```python
def test_voice_delay_follows_the_boot():
    cmd = ffmpeg_command(6.0, "voice.mp3", False, "o.mp4", fx="none", delay=9.5)
    assert "[1:a]adelay=9500|9500[v];[v]anull[a]" in cmd

def test_clicks_are_mixed_with_voice_and_hum():
    cmd = ffmpeg_command(10.43, "voice.mp3", True, "o.mp4", clicks="clicks.wav")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert cmd[cmd.index("clicks.wav") - 1] == "-i"
    assert graph.endswith("[3:a]anull[c];[v][h][c]amix=inputs=3:duration=longest:normalize=0[a]")

def test_clicks_alone_still_produce_an_audio_track():
    cmd = ffmpeg_command(5.0, None, False, "o.mp4", clicks="clicks.wav")
    assert "[1:a]anull[c];[c]anull[a]" in cmd

def test_click_track_has_the_video_length_and_sound_at_each_click(tmp_path):
    path = tmp_path / "c.wav"
    write_clicks([0.5], 2.0, str(path))
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (44100, 1, 2)
        assert w.getnframes() == 88200
        samples = array.array("h", w.readframes(w.getnframes()))
    assert max(map(abs, samples[:22050])) == 0
    assert max(map(abs, samples[22050:22050 + 441])) > 1000
```

- [ ] **Step 2: Run** `uv run pytest tests/test_mux.py -v` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** `write_clicks` and the `delay`/`clicks` parameters.
- [ ] **Step 4: Run** `uv run pytest tests/test_mux.py tests/test_golden.py -v` — Expected: all PASS.
- [ ] **Step 5: Commit** `feat: mix typing clicks and delay the voice past the boot screen`

---

### Task 6: Wire the block through the CLI, flags and README

**Files:**
- Modify: `src/muthur/cli.py` (`build_parser`, `parse_args`, `render_command`, `render_video`), `README.md` (new `### Boot sequence` section under Usage, plus the `boot_*` keys in the Settings file example)
- Test: `tests/test_cli.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `split_boot`, `plan`, `Timing` (Tasks 2–3); `iter_frames(..., boot=)` (Task 4); `ffmpeg_command(..., delay=, clicks=)`, `write_clicks` (Task 5).
- Produces: flags `--boot-type-speed`, `--boot-status-pause`, `--boot-bar-time`, `--boot-count-time`, `--boot-hold` (`type=float`, defaults from Global Constraints) and `--boot-clicks/--no-boot-clicks`; `render_video(cues, audio, out, image, font_path, wrap, upper, hum, title, fx, boot=None)`.

`render_command`: `steps, narrated = boot.split_boot(raw)`; use `narrated` everywhere `raw` is used today; when `steps`, `boot = plan(steps, Timing(...from flags), a.wrap, a.upper)`. `render_command` calls `render_video` positionally with `boot` as the last argument (the `rendered` fixture reads `args[-1]`); `render_video` passes `boot=boot` as a keyword to `iter_frames`, uses `delay = (boot.duration if boot else 0) + LEAD_IN`, and when `boot and a.boot_clicks` writes the click WAV into the temp dir and passes it as `clicks`. `parse_args` rejects `boot_type_speed <= 0` and any other boot timing `< 0` using the existing `fail(key, ...)` helper so file vs flag is named correctly.

- [ ] **Step 1: Write the failing tests**

```python
BOOTED = "[BOOT start]\n[Status: AKTYWNE, text: ŻYCIE]\n[BOOT end]\nRaport systemowy.\n"

def test_tts_gets_only_the_narrated_text(tmp_path, monkeypatch, rendered):
    path = tmp_path / "intro.txt"
    path.write_text(BOOTED, encoding="utf-8")
    texts = []
    def fake_tts(text, voice, rate, workdir, pitch=None):
        texts.append(text)
        mp3 = os.path.join(workdir, "narration.mp3")
        open(mp3, "wb").close()
        return mp3, [[0.0, 1.0, text]]
    monkeypatch.setattr(cli.narration, "run_tts", fake_tts)
    cli.main(["render", str(path)])
    assert texts == ["Raport systemowy."]
    assert rendered[0][-1].duration > 0

def test_boot_shifts_voice_and_cues_by_the_same_amount(tmp_path, monkeypatch, voice):
    path = tmp_path / "intro.txt"
    path.write_text(BOOTED, encoding="utf-8")
    (tmp_path / "s.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nRaport systemowy.\n", encoding="utf-8")
    seen = {}

    def fake_frames(cues, *args, boot=None):
        seen["shift"] = boot.duration
        return 10.0, iter(())

    monkeypatch.setattr(cli.render, "iter_frames", fake_frames)
    monkeypatch.setattr(cli.mux, "encode", lambda frames, total, cmd, out: seen.setdefault("cmd", cmd))
    cli.main(["render", str(path), "--audio", voice, "--srt", "s.srt", "--no-boot-clicks"])
    ms = int((seen["shift"] + cli.render.LEAD_IN) * 1000)
    assert f"adelay={ms}|{ms}" in seen["cmd"][seen["cmd"].index("-filter_complex") + 1]

def test_boot_flag_defaults():
    a = cli.build_parser().parse_args(["render", "intro.txt"])
    assert (a.boot_type_speed, a.boot_status_pause, a.boot_bar_time, a.boot_count_time, a.boot_hold, a.boot_clicks) == (
        22.0, 0.7, 1.5, 2.0, 2.0, True)

@pytest.mark.parametrize("args", [["--boot-type-speed", "0"], ["--boot-hold", "-1"]])
def test_non_positive_type_speed_is_rejected(args, capsys):
    with pytest.raises(SystemExit):
        cli.parse_args(["render", "intro.txt", *args])
    assert args[0][2:] in capsys.readouterr().err
```

And in `tests/test_config.py`: `boot_hold = 2.5` in `[render]` gives `a.boot_hold == 2.5`; `boot_type_speed = 0` exits naming `boot_type_speed in <file>`.

- [ ] **Step 2: Run** `uv run pytest tests/test_cli.py tests/test_config.py -v` — Expected: new tests FAIL.
- [ ] **Step 3: Implement** the flags, validation and wiring; write the README section (the example block from the spec, each tag in one line, the timing flags table, a fish example `uv run muthur render intro.txt --no-tts --boot-hold 3`).
- [ ] **Step 4: Run** `uv run pytest` — Expected: all PASS including golden.
- [ ] **Step 5: Smoke render** `uv run muthur render <scratch>/boot.txt --no-tts -o <scratch>/boot.mp4` with the spec's example; extract frames at 1, 4 and the first narrated second with `ffmpeg -ss`, and look at them: bar, aligned dots, Polish letters, then the narrated screen.
- [ ] **Step 6: Commit** `feat: play an optional boot sequence before the narrated intro`
