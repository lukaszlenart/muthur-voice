# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A game-master tool for tabletop Alien RPG sessions (OBCY, Polish edition): it turns a text file into
a ~1 minute MU/TH/UR terminal video played on a TV before a session — green typewriter text synced
to narration, CRT scanlines/glow/flicker, and a low ship hum, as a 1080p H.264 MP4 that plays from a
USB stick.

The original prototype (`mother_intro.py`, removed; see git history) defines the visual style.
Refactor the look, don't redesign it: `tests/test_golden.py` compares every frame's SHA-256 with
hashes recorded from that prototype.

## Constraints

- **Polish first.** Narration and on-screen text are Polish; every text path (fonts, upper-casing,
  wrapping, Whisper word matching) must handle ą ć ę ł ń ó ś ź ż. English should also work.
- **fish shell.** Docs and scripts must not assume bash. System pip is blocked (PEP 668, Homebrew
  Python 3.14), so everything runs from the project venv.
- **No spoilers.** Intro texts are shown to players; don't add scenario details to them.
- Whisper alignment on the real `lektor.mp3` (2026-10-14): `medium` matched 15/16 sentences, all
  within ~0.3 s of the recording's pauses, so it is the default; `small` matched 8/16 and `base` 5/16, both
  badly misplaced (short common words match at the wrong place in the audio and pin sentences to the wrong times).
- TTS mispronounces tokens like "MU/TH/UR"; there is no spoken-vs-displayed text override yet.
- edge-tts has only two native Polish voices (Zofia, Marek); `*MultilingualNeural` voices can also
  read Polish. The user dislikes Zofia (the current default).
- Rendering runs at roughly 2.5× real time (pure Pillow per frame).

- Dependencies resolve with `[tool.uv] exclude-newer` because the user's safe-chain guard blocks
  very new releases; never bypass it with `--safe-chain-skip-minimum-package-age`.

## Commands

```fish
uv sync --extra align                  # venv in .venv; the extra adds faster-whisper
uv run pytest                          # all tests (golden ~20 s, needs Menlo)
uv run pytest -m "not golden"          # fast loop
uv run pytest tests/test_timing.py::test_merges_cues_split_mid_sentence -v
uv run muthur render intro.txt --no-tts -o /tmp/x.mp4   # quickest real render
uv run python tests/golden/record.py   # re-record golden hashes, only after an intended look change
```

`lektor.mp3` in the root is the user's own recording; never overwrite it. Media files are gitignored.

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
