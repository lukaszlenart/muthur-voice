# Boot sequence block — design

Date: 2026-10-22
Status: approved in conversation, pending builder check

## Intent

The OBCY teaser (youtube.com/watch?v=9oef5crU2fI, ~9–22 s) opens with MU/TH/UR booting the ship:
typed status lines, a reactor progress bar, dot-leader status values, a deck temperature counting
up. The game master wants the same opening before their narrated intro, written in the same text
file with a few tags, so it plays on the TV before the session like the rest of the video.

## What the user decided

- A `[BOOT start]` … `[BOOT end]` block (alias `[CRT start]` … `[CRT end]`) at the **top** of the
  intro text file. It is optional: without it, the video is exactly what it is today.
- The boot block has **no narration**. Its only sound is printing (a click per typed letter), with
  the ship hum underneath.
- After the boot block finishes, the existing narrated intro plays as it does now.
- The boot screen **reuses the narrated part's header, footer and background** (`--title`,
  `--image`, the existing CRT scanlines, glow and flicker). No ticking clock, no separate mode label.
- Line types inside the block, as played back in the mockup and accepted:
  - **plain line** — typed letter by letter.
  - `[ProgressBar: 1..100, label: %, text: ROZRUCH REAKTORA]` — the text is typed, then a
    segmented bar fills while the number counts from the start to the end value, followed by the label.
  - `[Status: AKTYWNE, text: System podtrzymywania życia]` — the text and a dot leader are typed,
    a pause, then the value appears.
  - `[ProgressValue: -10..21, label: °C, text: TEMPERATURA POKŁADU]` — like Status, but the value
    counts from the start to the end number, followed by the label.
- Everything is upper-cased like the narrated part (and follows `--no-upper`). Dot leaders run to
  one shared column so values line up.
- After the last line: a hold, then the screen clears and the narrated intro starts.
- **Timing is configurable.**

Example the user wrote (tag name corrected to `ProgressBar`):

```
[BOOT start]
WZNAWIANIE SYSTEMÓW POKŁADOWYCH
[ProgressBar: 1..100, label: %, text: ROZRUCH REAKTORA]
[Status: AKTYWNE, text: System podtrzymywania życia]
[Status: włączone, text: OŚWIETLENIE]
[ProgressValue: -10..21, label: °C, text: TEMPERATURA POKŁADU]
[Status: ZDATNA DO ODDYCHANIA, text: ATMOSFERA]
INICJACJA SEKWENCJI WYBUDZANIA ZAŁOGI
[BOOT end]
Raport systemowy.
...narrated intro as today...
```

## Goals

- Recreate the feel of the teaser's boot screen from a plain text file, in Polish and English.
- Keep the narrated part untouched: same look, same cues, same alignment.

## Non-goals

- The teaser's crew vital-signs monitor (portraits, ECG traces), the starfield cold open, the
  ticking ship clock and mode footer.
- Boot blocks anywhere other than the top of the file, or more than one per file.
- Narration inside the boot block.

## Anti-goals (fails even if it works)

- Any change to frames of a file with **no** boot block. `tests/test_golden.py` must pass unchanged.
- Boot text leaking into TTS, Whisper alignment or the saved `_napisy.srt` / `_lektor.mp3`.
- Mangled Polish letters in tags, labels or values (ą ć ę ł ń ó ś ź ż, including in upper-casing).
- A bundled audio file or a new runtime dependency for the click sound.

## Constraints

- Voice delay and cue shift must change together: `render.timeline` shifts cues by `LEAD_IN`, and
  `mux.ffmpeg_command` delays the voice by the same amount via `adelay`. With a boot block, both
  must use `boot_duration + LEAD_IN`.
- Cues stay relative to the start of the audio (the SRT written for `--audio` must not move).
- Config: a new flag on the `render` subparser is automatically a `muthur.toml` key
  (`config.apply`). But `config.defaults` only accepts booleans, string lists, whole numbers
  (`type=int`) and strings, so the seconds-valued timing flags need a `type=float` branch there
  (accepting TOML ints and floats, rejecting booleans), mirroring the existing `int` branch.
- fish shell, macOS first, Linux/Windows supported; Polish-first text handling via `text.read_text`.

## How it fits the code

1. **Parse** (`text.py` or a new `boot.py`): after `read_text`, split the file into
   `(boot_steps, narrated_text)`. `render_command` passes only `narrated_text` to TTS, alignment
   and `estimate_cues` — everything that uses `raw` today.
2. **Timeline**: from the steps and timing settings, compute each step's start/end, every typed
   character's time (for clicks) and the total boot duration, ending with the hold.
3. **Render**: `render.iter_frames` draws boot frames first (same background, scanlines, glow,
   flicker and power-on fade), then the narrated frames with the extra shift. Boot lines use the
   narrated font, size, line height and left margin, all bright `GREEN`, with the block cursor.
4. **Audio**: `mux.ffmpeg_command` delays the voice by `boot_duration + LEAD_IN`, and mixes in a
   click track when there are clicks. The ship hum runs from 0 over the whole video as today.

## Tag grammar

- One tag or plain line per line. `[Name: first, key: value, key: value]`.
- Tag names and keys are case-insensitive. `[BOOT start]`/`[CRT start]` and `end` likewise.
- `ProgressBar` / `ProgressValue`: first item is `A..B` (integers, may be negative); keys `text`
  (required) and `label` (optional, appended as written right after the number).
- `Status`: first item is the value; key `text` (required).
- Malformed input exits with a clear message naming the line number: unknown tag (suggest the
  closest name, e.g. `ProgresBar` → `ProgressBar`), missing `text`, bad range, `[BOOT start]`
  without `[BOOT end]`, or a boot block that is not at the top of the file.

## Timing settings (configurable)

Flags on `muthur render`, so also `muthur.toml` keys. Defaults are my call, matching the mockup:

| Flag | Default | Meaning |
|---|---|---|
| `--boot-type-speed` | 22 | letters per second when typing |
| `--boot-status-pause` | 0.7 s | pause between the dots and a Status value |
| `--boot-bar-time` | 1.5 s | time for a ProgressBar to fill |
| `--boot-count-time` | 2.0 s | time for a ProgressValue to count |
| `--boot-hold` | 2.0 s | hold after the last line before the screen clears |

Plus `--boot-clicks/--no-boot-clicks` (default on) for the typing sound.

## My calls (the user did not decide these)

- Blank lines inside the block are kept as empty lines.
- No `> ` prompt prefix on boot lines (the teaser has none; the narrated part keeps its prefix).
- Values appear all at once after the pause; they are not typed.
- Dot-leader column = longest `text` among the block's Status and ProgressValue lines + a minimum
  of 3 dots. ProgressBar lines take no part in it: as in the approved mockup, the bar follows the
  text after one space, then two spaces and the number with its label. A line that would exceed
  `--wrap` exits with an error naming the line, rather than wrapping a status line.
- `label` is shown exactly as typed and is never upper-cased (`kPa`, `m/s` stay as they are);
  `text`, Status values and plain lines follow `--upper`.
- Timing flags take seconds as decimals (`type=float`), which needs the `config.py` branch above.
- A short pause (~0.25 s) between steps.
- Bars and counting values make no sound apart from the hum.
- ProgressValue counts in whole numbers.
- The click is synthesised with the standard library or ffmpeg's `lavfi`, never shipped as a file.
- If the block has more lines than fit on screen, it scrolls like the narrated part.

## Left to the builder

- Module layout (extend `text.py` vs. a new `boot.py`), exact click synthesis, and how the click
  track reaches ffmpeg.
- Bar width and glyphs (the mockup used 15 segments of `█`/`░`; Menlo must have them).
- Tests: parser (Polish letters, errors, aliases), timeline arithmetic, the voice/cue shift staying
  in sync, ffmpeg command with clicks, and a no-boot-block regression via the golden tests.
- README: document the tags with the example above, in a section about the boot block.
