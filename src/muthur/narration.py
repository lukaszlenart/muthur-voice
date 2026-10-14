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
