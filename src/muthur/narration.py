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


def run_tts(text, voice, rate, workdir):
    require_edge_tts()
    script = os.path.join(workdir, "script.txt")
    with open(script, "w", encoding="utf-8") as f:
        f.write(text)
    mp3 = os.path.join(workdir, "narration.mp3")
    srt = os.path.join(workdir, "narration.srt")
    subprocess.run(edge_tts_cmd(voice, rate, mp3, file=script, srt=srt), check=True)
    return mp3, parse_srt(srt)


DEFAULT_VOICES = [
    "pl-PL-ZofiaNeural",
    "pl-PL-MarekNeural",
    "de-DE-SeraphinaMultilingualNeural",
    "de-DE-FlorianMultilingualNeural",
    "en-US-AvaMultilingualNeural",
    "en-US-AndrewMultilingualNeural",
]
SAMPLE = "Procedura wybudzania zakończona. Witamy z powrotem, załogo."


def synthesize(voice, rate, text, mp3):
    require_edge_tts()
    return subprocess.run(edge_tts_cmd(voice, rate, mp3, text=text)).returncode == 0


def find_player():
    afplay = shutil.which("afplay")
    if not afplay:
        return None
    return lambda mp3: subprocess.run([afplay, mp3])


def audition(voices, text, rate, outdir, synth=synthesize, player=None):
    results = []
    for i, voice in enumerate(voices, 1):
        mp3 = os.path.join(outdir, f"{i:02}_{voice}.mp3")
        print(f"  [{i}/{len(voices)}] {voice}")
        if not synth(voice, rate, text, mp3):
            print(f"  ! {voice}: synthesis failed, skipping")
            continue
        results.append((voice, mp3))
        if player:
            player(mp3)
    return results
