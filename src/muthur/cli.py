"""MU/TH/UR intro generator: text -> Polish narration + terminal-style video for TV.

  muthur render intro.txt                        # edge-tts narration -> intro.mp4
  muthur render intro.txt --image montero.jpg    # image behind the text
  muthur render intro.txt --voice pl-PL-MarekNeural --rate=-15%
  muthur render intro.txt --pitch=+0Hz --voice-fx echo   # natural pitch, lighter echo
  muthur render intro.txt --audio lektor.mp3     # own narration, subtitles aligned by Whisper
  muthur render intro.txt --no-tts               # silent preview, estimated timing

Defaults come from ./muthur.toml (or --config FILE) when present; flags override it.
"""
import argparse
import os
import shutil
import sys
import tempfile

from muthur import align, config, mux, narration, render, timing
from muthur.text import read_text

VOICE = "pl-PL-ZofiaNeural"
RATE = "-20%"
PITCH = "-24Hz"
VOICE_FX = "intercom"


def build_parser():
    ap = argparse.ArgumentParser(prog="muthur", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="text file -> MU/TH/UR video")
    r.add_argument("text")
    r.add_argument("--config", help=f"settings file (default: ./{config.FILENAME} if present)")
    r.add_argument("-o", "--out")
    r.add_argument("--image", help="background image (darkened behind the text)")
    r.add_argument("--voice", default=VOICE, help="or pl-PL-MarekNeural")
    r.add_argument("--rate", default=RATE, help="speech rate (default %(default)s), e.g. --rate=-15%%")
    r.add_argument("--pitch", default=PITCH, help="voice pitch (default %(default)s), e.g. --pitch=+0Hz")
    r.add_argument("--voice-fx", choices=mux.VOICE_FX, default=VOICE_FX,
                   help="effect on the narration: intercom (ship's speaker, default), echo, none")
    r.add_argument("--audio", help="use your own narration (e.g. from ElevenLabs) instead of edge-tts")
    r.add_argument("--srt", help="subtitles matching --audio (skips auto-alignment)")
    r.add_argument("--whisper-model", default="medium",
                   help="model for aligning --audio: medium (default, most accurate), small, base (faster, less accurate)")
    r.add_argument("--align", action=argparse.BooleanOptionalAction, default=True,
                   help="with --audio: --no-align estimates timing instead of Whisper")
    r.add_argument("--tts", action=argparse.BooleanOptionalAction, default=True,
                   help="--no-tts: no voice, estimated timing (preview)")
    r.add_argument("--hum", action=argparse.BooleanOptionalAction, default=True,
                   help="ship-hum background")
    r.add_argument("--upper", action=argparse.BooleanOptionalAction, default=True,
                   help="upper-case the text; --no-upper keeps the original letter case")
    r.add_argument("--wrap", type=int, default=54, help="characters per line")
    r.add_argument("--font")
    r.add_argument("--title", default="MU/TH/UR 6000 :: USCSS MONTERO")

    v = sub.add_parser("voices", help="read a sample sentence with several voices and play them in turn")
    v.add_argument("--config", help=f"settings file (default: ./{config.FILENAME} if present)")
    v.add_argument("--voice", action="append",
                   help=f"repeatable; default: {', '.join(narration.DEFAULT_VOICES)}")
    v.add_argument("--text", default=narration.SAMPLE)
    v.add_argument("--rate", default=RATE, help="speech rate (default %(default)s), e.g. --rate=-15%%")
    v.add_argument("--pitch", default=PITCH, help="voice pitch (default %(default)s), e.g. --pitch=+0Hz")
    v.add_argument("--voice-fx", choices=mux.VOICE_FX, default=VOICE_FX,
                   help="play the samples through an effect: intercom (default), echo, none")
    v.add_argument("--keep", metavar="DIR", help="save the samples in DIR")
    v.add_argument("--play", action=argparse.BooleanOptionalAction, default=True,
                   help="--no-play only saves the samples")
    return ap


def render_video(cues, audio, out, image, font_path, wrap, upper, hum, title, fx):
    total, frames = render.iter_frames(cues, image, font_path, wrap, upper, title)
    mux.encode(frames, total, mux.ffmpeg_command(total, audio, hum, out, fx), out)


def render_command(a):
    out = a.out or os.path.splitext(a.text)[0] + ".mp4"
    raw = read_text(a.text).strip()

    with tempfile.TemporaryDirectory() as tmp:
        if a.audio:
            audio = a.audio
            if a.srt:
                cues = timing.parse_srt(a.srt)
            else:
                cues = align.align_cues(raw, audio, a.whisper_model) if a.align else None
                if cues is None:
                    cues = timing.estimate_cues(raw)
                else:
                    srt_out = os.path.splitext(out)[0] + "_napisy.srt"
                    timing.write_srt(cues, srt_out)
                    print(f"  subtitles saved: {srt_out} (fix by hand and pass with --srt if needed)")
        elif not a.tts:
            audio, cues = None, timing.estimate_cues(raw)
        else:
            print(f"  narration: {a.voice} ({', '.join(filter(None, [a.rate, a.pitch]))})")
            audio, cues = narration.run_tts(raw, a.voice, a.rate, tmp, pitch=a.pitch)
            shutil.copy(audio, os.path.splitext(out)[0] + "_lektor.mp3")
        render_video(cues, audio, out, a.image, a.font, a.wrap, a.upper, a.hum, a.title,
                     a.voice_fx)


def voices_command(a):
    voices = a.voice or getattr(a, "config_voice", None) or narration.DEFAULT_VOICES
    player = narration.find_player() if a.play else None
    keep = a.keep or (None if player else "audition")
    fx = None if a.voice_fx == "none" else lambda src, dst: mux.apply_fx(src, dst, a.voice_fx)
    if keep:
        os.makedirs(keep, exist_ok=True)
        results = narration.audition(voices, a.text, a.rate, keep, player=player, pitch=a.pitch, fx=fx)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            results = narration.audition(voices, a.text, a.rate, tmp, player=player, pitch=a.pitch, fx=fx)
    if not results:
        sys.exit("no voice could be synthesised (check the voice names and your network)")
    if keep:
        print(f"  samples saved in {keep}/")


def subcommands(parser):
    return next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices


def parse_args(argv=None):
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config")
    path = config.find(pre.parse_known_args(argv)[0].config)
    parser = build_parser()
    settings = config.load(path) if path else {}
    if path:
        config.apply(subcommands(parser), settings, path)
        print(f"  config: {os.path.abspath(path)}")
    a = parser.parse_args(argv)
    if a.command == "render" and not a.audio:
        render = subcommands(parser)["render"]
        for key, flag, used in [("srt", "--srt", a.srt), ("align", "--no-align", not a.align)]:
            if used:
                from_file = key in settings.get("render", {}) and getattr(a, key) == render.get_default(key)
                parser.error(f"{key} in {path} needs audio" if from_file else f"{flag} needs --audio")
    return a


def main(argv=None):
    a = parse_args(argv)
    {"render": render_command, "voices": voices_command}[a.command](a)
