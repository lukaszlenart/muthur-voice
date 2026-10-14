# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A game-master tool for tabletop Alien RPG sessions (OBCY, Polish edition): it turns a text file into
a ~1 minute MU/TH/UR terminal video played on a TV before a session — green typewriter text synced
to narration, CRT scanlines/glow/flicker, and a low ship hum, as a 1080p H.264 MP4 that plays from a
USB stick.

Currently a single-file prototype, `mother_intro.py`. It is the reference implementation and the
source of truth for the visual style: refactor it, don't redesign the look. There is no build, lint,
or test suite yet; verification means rendering a video and checking it.

## Constraints

- **Polish first.** Narration and on-screen text are Polish; every text path (fonts, upper-casing,
  wrapping, Whisper word matching) must handle ą ć ę ł ń ó ś ź ż. English should also work.
- **fish shell.** Docs and scripts must not assume bash. System pip is blocked (PEP 668, Homebrew
  Python 3.14), so everything runs from the project venv.
- **No spoilers.** Intro texts are shown to players; don't add scenario details to them.
- Whisper alignment (`--audio`) has only been tested against a simulated transcript, never a real
  recording — treat it as unverified.
- TTS mispronounces tokens like "MU/TH/UR"; there is no spoken-vs-displayed text override yet.
- edge-tts has only two native Polish voices (Zofia, Marek); `*MultilingualNeural` voices can also
  read Polish. The user dislikes Zofia (the current default).
- Rendering runs at roughly 2.5× real time (pure Pillow per frame).

## Commands

Environment: Python 3.14 venv in `.venv` (the user's shell is fish → `source .venv/bin/activate.fish`).
Requires `ffmpeg` on PATH (plain Homebrew formula; libass isn't needed since Pillow draws the text). Packages: `edge-tts`, `pillow`, optionally `faster-whisper`.

```fish
.venv/bin/python mother_intro.py intro.txt --no-tts          # fastest check: silent, estimated timing
.venv/bin/python mother_intro.py intro.txt                   # edge-tts narration (needs network)
.venv/bin/python mother_intro.py intro.txt --audio lektor.mp3   # own recording, Whisper-aligned
.venv/bin/python mother_intro.py intro.txt --audio lektor.mp3 --srt intro_napisy.srt  # hand-fixed timing
```

Outputs derive from `-o` (default `<text basename>.mp4`): `<out>.mp4`, plus `<out>_lektor.mp3`
(edge-tts mode) or `<out>_napisy.srt` (Whisper alignment mode). Running on `intro.txt` overwrites
`intro.mp4` / `intro_lektor.mp3` in the project root. `lektor.mp3` is a user-supplied recording, not
generated — don't overwrite it.

## Pipeline

Everything converges on one data shape: **cues**, a list of `[start_sec, end_sec, sentence]` relative
to the start of the audio. Four sources produce them, chosen in `main()`:

- edge-tts → its SRT → `parse_srt` → `merge_into_sentences` (glues cues split mid-sentence)
- `--audio` → `align_cues`: Whisper word timestamps matched to script words via `difflib`; unmatched
  sentences are interpolated by character length, then forced monotonic
- `--srt` → `parse_srt` directly
- `--no-tts` / fallback → `estimate_cues` (fixed chars-per-second)

Sentence boundaries come from `split_sentences` (regex on `.!?`) and `norm_word` keeps Polish
diacritics — changes to either affect alignment matching.

`render_video` shifts all cues by `LEAD_IN` and delays the audio by the same amount with ffmpeg
`adelay`; these must stay in sync. Frames are drawn with Pillow (`render_text_layer`: typewriter
reveal over 90% of each cue's duration, current sentence bright, previous ones dimmed, scrolled to
`max_lines`) and piped as raw RGB to an ffmpeg subprocess on stdin, which mixes narration (with echo)
and a brown-noise hum and encodes the MP4. Rendering is CPU-bound, per-frame, at 25 fps.
