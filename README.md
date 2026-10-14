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
uv run muthur render intro.txt --voice pl-PL-ZofiaNeural --rate=-15% --pitch=-8Hz   # lower, flatter voice
uv run muthur render intro.txt --audio lektor.mp3       # own recording (e.g. ElevenLabs), Whisper aligns subtitles
uv run muthur render intro.txt --audio lektor.mp3 --srt intro_napisy.srt   # after fixing timing by hand
```

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
uv run muthur voices --voice pl-PL-ZofiaNeural --rate=-15% --pitch=-8Hz
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
original prototype. They need Menlo (macOS). After an intended visual change, check the new
video by eye, then re-record with `uv run python tests/golden/record.py`.

## License

Apache License 2.0, see `LICENSE`.
