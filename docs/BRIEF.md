# muthur-voice — project brief

## What this is

A small CLI tool that turns a text file into a short video for a TV screen:
a voice narration plus on-screen text styled as the MU/TH/UR ship computer
terminal from the Alien films (green monospace text, typewriter reveal synced
to the voice, CRT scanlines, phosphor glow, blinking cursor, low ship hum).

It's a game-master tool for tabletop RPG sessions (OBCY / Alien RPG, Polish
edition). Typical use: play a ~1 minute intro to a scenario before the session
starts, e.g. the ship computer waking the crew from hypersleep.

**Main language of narration and on-screen text is Polish.** Everything must
handle Polish diacritics (ą ć ę ł ń ó ś ź ż) in text, fonts, upper-casing and
word matching. English should work too, but Polish is the priority.

## Current state

There is a working single-file prototype: `mother_intro.py` (Python 3, Pillow,
ffmpeg, edge-tts, optional faster-whisper) and a sample `intro.txt`.
Treat it as the reference implementation and the source of truth for the
visual style; refactor it, don't rewrite the look from scratch.

Pipeline:

1. **Narration**, one of:
   - `edge-tts` (free Microsoft neural voices) → MP3 + SRT with timings.
     Default voice `pl-PL-ZofiaNeural`, rate `-10%`.
   - The user's own recording (`--audio`, e.g. made in ElevenLabs).
     Subtitle timing is then aligned automatically: faster-whisper transcribes
     with word timestamps, `difflib.SequenceMatcher` matches recognised words to
     the script words, sentences with no match are interpolated from their
     neighbours. Result is also saved as `<out>_napisy.srt` for manual fixes,
     and can be fed back with `--srt`.
   - `--no-tts`: silent preview with timing estimated from text length.
2. **Frames**: Pillow renders 1920x1080 @ 25 fps. Text is split into sentences,
   each sentence is a "cue" typed out over ~90% of its spoken duration.
   Older sentences stay on screen dimmed, the list scrolls when full.
   Optional `--image` is darkened and green-tinted behind the text.
3. **Mux**: raw frames are piped into ffmpeg → H.264 + AAC MP4
   (`yuv420p`, `+faststart`) so it plays on any TV from a USB stick.
   Audio: voice delayed by a 2 s "boot" lead-in, light `aecho` on the voice,
   brown-noise hum (lowpass 180 Hz) underneath, 3 s tail at the end.

CLI options today: `--out --image --voice --rate --audio --srt
--whisper-model --no-align --no-tts --no-hum --no-upper --wrap --font --title`.

## Environment and lessons learned

- macOS, Homebrew Python 3.14. System pip is blocked (PEP 668), so the project
  needs its own virtual environment. The user's shell is **fish**
  (`source .venv/bin/activate.fish`), so any docs/scripts must not assume bash.
- `ffmpeg` from Homebrew (regular formula is enough; libass is not needed
  because Pillow draws the text).
- Fonts: Menlo (`/System/Library/Fonts/Menlo.ttc`) on macOS, DejaVu Sans Mono
  as Linux fallback.
- edge-tts has only two native Polish voices (Zofia, Marek). The
  `*MultilingualNeural` voices can also read Polish, sometimes more naturally.
  The user was not happy with Zofia, so easy voice auditioning matters.
- TTS mispronounces "MU/TH/UR" and similar tokens. We need a way to have
  **different spoken text and displayed text** (pronunciation overrides).
- Whisper alignment is tested only with a simulated transcript, never on a real
  recording. Verify it on real audio.
- Rendering takes roughly 2.5x real time (pure Pillow per frame). Fine for now,
  but it could be faster (numpy, render only when text changes, reuse frames).
- The intro text must not spoil the scenario for players.

## What I want from the initial setup

1. Proper project structure with `pyproject.toml`, a package and a CLI entry
   point (e.g. `muthur render intro.txt`). Pick a sensible venv/tooling setup
   that works well with fish (`uv` is fine).
2. Split the prototype into modules (narration, timing/alignment, rendering,
   muxing) without changing its behaviour or look.
3. Tests for the parts that are easy to get wrong: sentence splitting,
   SRT parsing and writing, merging edge-tts cues into sentences, Whisper
   alignment logic (with a fake transcript, incl. recognition errors and
   missing sentences), Polish upper-casing and wrapping.
4. A voice audition command: read one sample sentence with several voices
   and play them one by one (`afplay` on macOS).
5. `README.md` (setup on macOS with fish, usage examples) and `CLAUDE.md`
   with project conventions.

## Ideas for later (not part of initial setup)

- Pronunciation overrides: displayed text vs spoken text in one source file.
- Scene file (YAML/TOML): several screens, pauses, per-scene image, sound
  effects (alarm, door, hiss of hypersleep pods).
- Visual presets beyond MU/TH/UR: ship log, Colonial Marines briefing,
  corporate (Weyland-Yutani) message.
- Faster rendering, preview of a single frame or a 10 s fragment.
- Optional ElevenLabs API integration instead of manual export.
