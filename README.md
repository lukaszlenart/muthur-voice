# muthur-voice

Turns a text file into a short video for a TV screen: a voice narration plus on-screen text styled
as the MU/TH/UR ship computer from the Alien films: green monospace terminal, typewriter text synced
to the voice, CRT scanlines, phosphor glow, blinking cursor, low ship hum. Built for Alien RPG
(OBCY) sessions, for example an intro where Mother wakes the crew from hypersleep. Polish first.

## Setup (macOS, fish)

```fish
brew install ffmpeg fribidi uv   # fribidi: Pillow's Raqm text layout, which the look depends on
uv sync                    # add --extra align to align your own recordings with Whisper
```

The output is a 1080p H.264 MP4 that plays from a USB stick on any TV.

## Usage

```fish
uv run muthur render intro.txt                          # Polish edge-tts narration -> intro.mp4
uv run muthur render intro.txt --pitch=+0Hz --voice-fx echo   # natural pitch, lighter echo
uv run muthur render intro.txt --no-tts                 # silent preview, estimated timing
uv run muthur render intro.txt --image examples/orbit/background.jpg   # darkened, green-tinted image behind the text
uv run muthur render intro.txt --voice pl-PL-MarekNeural --rate=-15%
uv run muthur render intro.txt --audio lektor.mp3       # own recording (e.g. ElevenLabs), Whisper aligns subtitles
uv run muthur render intro.txt --audio lektor.mp3 --srt intro_napisy.srt   # after fixing timing by hand
```

The default narration is `pl-PL-ZofiaNeural` at `--rate=-20% --pitch=-24Hz`, played through
`--voice-fx intercom` (a ship's speaker). The effect also applies to `--audio`; pass
`--voice-fx none` to keep your recording dry.

Files written next to the video (`-o` changes the base name):

| Mode | Files |
|---|---|
| edge-tts (default) | `intro.mp4`, `intro_lektor.mp3` (the narration) |
| `--audio` with Whisper | `intro.mp4`, `intro_napisy.srt` (edit it, then pass it back with `--srt`) |
| `--no-tts`, `--audio --srt` | `intro.mp4` |

### Examples

[`examples/`](examples/README.md) holds four ready intros, each with its own text, settings and
background image:

```fish
uv run muthur render examples/wake-up/intro.txt --config examples/wake-up/muthur.toml
```

### Settings file

Instead of repeating flags each session, put them in `muthur.toml` in the current directory (or
pass `--config FILE`). A flag beats the file, and the file beats the built-in default. Keys are the
long flag names with `_` for `-`; `--no-*` flags become booleans (`hum`, `upper`, `tts`, `align`,
`play`), each also available as a positive flag (`--hum`) to undo a `false` from the file. Paths
(`image`, `audio`, `srt`, `font`, `out`, `keep`) are relative to the file. An unknown key is an error.

```toml
[render]
voice = "pl-PL-ZofiaNeural"
rate = "-20%"
pitch = "-24Hz"
voice_fx = "intercom"
title = "MU/TH/UR 6000 :: USCSS MONTERO"
image = "examples/orbit/background.jpg"
whisper_model = "medium"
wrap = 54
hum = true
upper = true

[voices]
voice = ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]
rate = "-20%"
text = "Procedura wybudzania zakończona. Witamy z powrotem, załogo."
```

### Choosing a voice

edge-tts has two native Polish voices (`pl-PL-ZofiaNeural`, `pl-PL-MarekNeural`). The
`*MultilingualNeural` voices can read Polish too, sometimes more naturally. To hear a sample
sentence in each default candidate, with the default rate, pitch and effect:

```fish
uv run muthur voices
uv run muthur voices --voice pl-PL-MarekNeural --voice de-DE-SeraphinaMultilingualNeural --rate=-15%
uv run muthur voices --voice pl-PL-ZofiaNeural --pitch=-15Hz --voice-fx none
uv run muthur voices --text "Dlaczego Matka was obudziła?" --keep audition
uv run edge-tts --list-voices | grep -E 'pl-PL|Multilingual'    # all candidates
```

Without `afplay` (Linux), samples are saved in `audition/` instead of played.

## Development

```fish
uv run pytest                          # everything (golden tests take ~20 s)
uv run pytest -m "not golden"          # fast loop
uv run pytest tests/test_align.py::test_missing_middle_sentence_fills_the_gap -v
```

The golden tests compare the SHA-256 of every rendered frame with hashes recorded from the
original prototype. They need Menlo (macOS) and Raqm text layout (`brew install fribidi`). After an intended visual change, check the new
video by eye, then re-record with `uv run python tests/golden/record.py`.

CI (`.github/workflows/test.yml`) runs the full suite, golden tests included, on macOS for every
pull request and push to `main`.

## License

Apache License 2.0, see `LICENSE`.
