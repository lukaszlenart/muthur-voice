# muthur-voice

Turns a text file into a short video for a TV screen: a voice narration plus on-screen text styled
as the MU/TH/UR ship computer from the Alien films: green monospace terminal, typewriter text synced
to the voice, CRT scanlines, phosphor glow, blinking cursor, low ship hum. Built for Alien RPG
(OBCY) sessions, for example an intro where Mother wakes the crew from hypersleep. Polish first.

## Install

macOS ([Homebrew](https://brew.sh)):

```fish
brew install ffmpeg fribidi uv   # fribidi: Pillow's Raqm text layout, which the look depends on
uv tool install "muthur-voice @ https://github.com/lukaszlenart/muthur-voice/archive/refs/heads/main.zip"
```

Linux (Debian/Ubuntu):

```sh
sudo apt install ffmpeg libfribidi0 fonts-dejavu-core
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install "muthur-voice @ https://github.com/lukaszlenart/muthur-voice/archive/refs/heads/main.zip"
```

Windows (PowerShell; open a new terminal after `winget` so the new commands are on PATH):

```powershell
winget install astral-sh.uv
winget install Gyan.FFmpeg
uv tool install "muthur-voice @ https://github.com/lukaszlenart/muthur-voice/archive/refs/heads/main.zip"
```

`uv` fetches a matching Python if needed. To align your own recordings with Whisper (`--audio`),
install `"muthur-voice[align] @ ..."` instead; it downloads a few hundred MB more. Remove with
`uv tool uninstall muthur-voice`.

### Updates

`muthur` checks the [latest release](https://github.com/lukaszlenart/muthur-voice/releases) at most
once a day and, when there is a newer one, prints after the render:

```
  MU/TH/UR 0.2.0 is available (you have 0.1.0): uv tool upgrade muthur-voice
```

`muthur --version` shows what you have. Set `MUTHUR_NO_UPDATE_CHECK=1` to turn the check off. To
hear about releases by email instead, use *Watch → Custom → Releases* on GitHub.

The look was tuned on macOS with Menlo. Linux uses DejaVu Sans Mono and Windows uses Consolas
(pass `--font` for another), and without FriBiDi (usual on Windows) Pillow lays text out more simply.

The output is a 1080p H.264 MP4 that plays from a USB stick on any TV.

## Usage

```fish
muthur render intro.txt                          # Polish edge-tts narration -> intro.mp4
muthur render intro.txt --pitch=+0Hz --voice-fx echo   # natural pitch, lighter echo
muthur render intro.txt --no-tts                 # silent preview, estimated timing
muthur render intro.txt --image examples/orbit/background.jpg   # darkened, green-tinted image behind the text
muthur render intro.txt --voice pl-PL-MarekNeural --rate=-15%
muthur render intro.txt --audio lektor.mp3       # own recording (e.g. ElevenLabs), Whisper aligns subtitles
muthur render intro.txt --audio lektor.mp3 --srt intro_napisy.srt   # after fixing timing by hand
```

The default narration is `pl-PL-ZofiaNeural` at `--rate=-20% --pitch=-24Hz`, played through
`--voice-fx intercom` (a ship's speaker); `--voice-fx old-intercom` is a narrower, slightly
distorted 1979-style PA. The effect also applies to `--audio`; pass
`--voice-fx none` to keep your recording dry.

Files written next to the video (`-o` changes the base name):

| Mode | Files |
|---|---|
| edge-tts (default) | `intro.mp4`, `intro_lektor.mp3` (the narration) |
| `--audio` with Whisper | `intro.mp4`, `intro_napisy.srt` (edit it, then pass it back with `--srt`) |
| `--no-tts`, `--audio --srt` | `intro.mp4` |

### Boot sequence

An optional block at the top of the text file plays a MU/TH/UR boot screen before the narration:
no voice, just typing clicks over the ship hum, with the same header and background as the rest.

```text
[BOOT start]
WZNAWIANIE SYSTEMÓW POKŁADOWYCH
[ProgressBar: 1..100, label: %, text: ROZRUCH REAKTORA]
[Status: AKTYWNE, text: Podtrzymywanie życia]
[Status: włączone, text: OŚWIETLENIE]
[ProgressValue: -10..21, label: °C, text: TEMPERATURA POKŁADU]
[Status: ZDATNA DO ODDYCHANIA, text: ATMOSFERA]
INICJACJA SEKWENCJI WYBUDZANIA ZAŁOGI
[BOOT end]
Raport systemowy. ...the narrated intro...
```

| Line | On screen |
|---|---|
| plain text | typed letter by letter |
| `[ProgressBar: A..B, label: %, text: ...]` | the text, then a bar filling while the number counts from A to B |
| `[Status: VALUE, text: ...]` | the text and dots, a pause, then the value |
| `[ProgressValue: A..B, label: °C, text: ...]` | the text and dots, then a number counting from A to B |

`[CRT start]` / `[CRT end]` work too, and tag names ignore case. Status and ProgressValue values
line up in one column. Text follows `--upper`; the `label` is shown exactly as typed. A line wider
than `--wrap` is an error. The pace is set with `--boot-type-speed` (letters per second, default
22), `--boot-status-pause` (0.7 s), `--boot-bar-time` (1.5 s), `--boot-count-time` (2 s) and
`--boot-hold` (2 s after the last line); `--no-boot-clicks` silences the typing.

```fish
muthur render intro.txt --no-tts --boot-hold 3
```

### Examples

[`examples/`](examples/README.md) holds four ready intros, each with its own text, settings and
background image (in a clone, or the [zip](https://github.com/lukaszlenart/muthur-voice/archive/refs/heads/main.zip) the install uses):

```fish
muthur render examples/wake-up/intro.txt --config examples/wake-up/muthur.toml
```

### Settings file

Instead of repeating flags each session, put them in `muthur.toml` in the current directory (or
pass `--config FILE`). A flag beats the file, and the file beats the built-in default. Keys are the
long flag names with `_` for `-`; `--no-*` flags become booleans (`hum`, `upper`, `tts`, `align`,
`play`, `boot_clicks`), each also available as a positive flag (`--hum`) to undo a `false` from the file. Paths
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
boot_type_speed = 22
boot_hold = 2.5

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
muthur voices
muthur voices --voice pl-PL-MarekNeural --voice de-DE-SeraphinaMultilingualNeural --rate=-15%
muthur voices --voice pl-PL-ZofiaNeural --pitch=-15Hz --voice-fx none
muthur voices --text "Dlaczego Matka was obudziła?" --keep audition
uvx edge-tts --list-voices | grep -E 'pl-PL|Multilingual'    # all candidates
```

Samples play with `afplay` (macOS) or `ffplay` (bundled with ffmpeg); without either they are saved
in `audition/`.

## Development

```fish
git clone https://github.com/lukaszlenart/muthur-voice; and cd muthur-voice
uv sync --extra align                  # then prefix commands with `uv run`, e.g. `uv run muthur render intro.txt`
uv run pytest                          # everything (golden tests take ~20 s)
uv run pytest -m "not golden"          # fast loop
uv run pytest tests/test_align.py::test_missing_middle_sentence_fills_the_gap -v
```

The golden tests compare the SHA-256 of every rendered frame with hashes recorded from the
original prototype. They need Menlo (macOS) and Raqm text layout (`brew install fribidi`). After an intended visual change, check the new
video by eye, then re-record with `uv run python tests/golden/record.py`.

To release, bump `version` in `pyproject.toml`, merge, then tag `main`:

```fish
git switch main; and git pull
git tag v0.2.0; and git push origin v0.2.0
```

The tag starts `.github/workflows/release.yml`: it checks the tag matches `version` and points at
`main`, runs the full test suite, then publishes a GitHub release with notes generated from the
merged PRs. Installed copies start showing the update notice within a day.

The check is off in a clone (editable install), in CI, and with `MUTHUR_NO_UPDATE_CHECK=1`.

CI (`.github/workflows/test.yml`) runs the full suite, golden tests included, on macOS for every
pull request and push to `main`, and the suite without golden tests plus a silent render on Linux
and Windows.

## License

Apache License 2.0, see `LICENSE`.
