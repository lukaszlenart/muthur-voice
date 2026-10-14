#!/usr/bin/env python3
"""
MU/TH/UR intro generator: text -> Polish narration + terminal-style video for TV.

Pipeline:
  1. edge-tts reads intro.txt (Polish neural voice) -> narration.mp3 + narration.srt
  2. Pillow renders frames: green monospace "terminal", typewriter text synced
     to the voice, scanlines, glow, blinking cursor, optional background image
  3. ffmpeg muxes frames + voice + low ship hum -> MP4 (1080p, H.264, plays on any TV)

Setup (macOS, inside a venv):
  brew install ffmpeg
  pip install edge-tts pillow
  pip install faster-whisper        # only for --audio (your own recording)

Usage:
  python3 mother_intro.py intro.txt                       # -> intro.mp4
  python3 mother_intro.py intro.txt --image montero.jpg   # image behind the text
  python3 mother_intro.py intro.txt --voice pl-PL-MarekNeural --rate=-15%
  python3 mother_intro.py intro.txt --audio lektor.mp3    # own narration (e.g. ElevenLabs),
                                                          # subtitles auto-aligned by Whisper
  python3 mother_intro.py intro.txt --no-tts              # silent preview, estimated timing
"""
import argparse
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 25
LEAD_IN = 2.0      # seconds of "boot" before the voice starts
TAIL = 3.0         # seconds after the voice ends
GREEN = (120, 255, 140)
DIM_GREEN = (60, 150, 75)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def load_font(size, path=None):
    for p in ([path] if path else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("No monospace font found, pass one with --font")


# ---------------------------------------------------------------- timing ---

def srt_time(s):
    h, m, rest = s.strip().split(":")
    sec, ms = re.split(r"[,.]", rest)
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(path):
    cues = []
    with open(path, encoding="utf-8") as f:
        blocks = re.split(r"\n\s*\n", f.read().strip())
    for b in blocks:
        lines = [l for l in b.strip().splitlines() if l.strip()]
        ts = next((l for l in lines if "-->" in l), None)
        if not ts:
            continue
        a, z = ts.split("-->")
        text = " ".join(lines[lines.index(ts) + 1:]).strip()
        if text:
            cues.append([srt_time(a), srt_time(z), text])
    return merge_into_sentences(cues)


def merge_into_sentences(cues):
    """edge-tts may split cues mid-sentence; glue them so the screen shows whole sentences."""
    out = []
    for c in cues:
        if out and not re.search(r"[.!?:]$", out[-1][2]):
            out[-1][1] = c[1]
            out[-1][2] += " " + c[2]
        else:
            out.append(c)
    return out


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def norm_word(w):
    return re.sub(r"[^0-9a-ząćęłńóśźż]", "", w.lower())


def align_cues(text, audio, model_size="small"):
    """Find when each sentence of `text` is spoken in `audio`.

    Whisper transcribes the recording with per-word timestamps; the recognised
    words are then matched against the script words (difflib), so small
    recognition mistakes don't matter. Sentences with no matched word get a
    time slot interpolated from their neighbours.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  ! faster-whisper not installed (pip install faster-whisper), estimating timing")
        return None
    import difflib

    print(f"  aligning subtitles with Whisper ({model_size}), first run downloads the model...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="pl", word_timestamps=True,
                                   initial_prompt=text[:800])
    rec = [(norm_word(w.word), w.start, w.end) for s in segments for w in (s.words or [])]
    rec = [r for r in rec if r[0]]
    if not rec:
        print("  ! Whisper recognised no words, estimating timing")
        return None

    sentences = split_sentences(text)
    script, owner = [], []
    for i, s in enumerate(sentences):
        for w in s.split():
            n = norm_word(w)
            if n:
                script.append(n)
                owner.append(i)

    times = [[] for _ in sentences]
    sm = difflib.SequenceMatcher(None, script, [r[0] for r in rec], autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            _, st, en = rec[b + k]
            times[owner[a + k]].append((st, en))

    cues = [[min(t[0] for t in ts), max(t[1] for t in ts), s] if ts else [None, None, s]
            for ts, s in zip(times, sentences)]
    matched = sum(1 for c in cues if c[0] is not None)
    print(f"  matched {matched}/{len(cues)} sentences")

    # fill sentences Whisper missed, proportionally to their length
    end_of_audio = rec[-1][2]
    i = 0
    while i < len(cues):
        if cues[i][0] is not None:
            i += 1
            continue
        j = i
        while j < len(cues) and cues[j][0] is None:
            j += 1
        lo = cues[i - 1][1] if i > 0 else 0.0
        hi = cues[j][0] if j < len(cues) else end_of_audio
        total = sum(len(c[2]) for c in cues[i:j]) or 1
        t = lo
        for c in cues[i:j]:
            d = (hi - lo) * len(c[2]) / total
            c[0], c[1] = t, t + d
            t += d
        i = j
    for k in range(1, len(cues)):  # keep order monotonic
        cues[k][0] = max(cues[k][0], cues[k - 1][0])
        cues[k][1] = max(cues[k][1], cues[k][0] + 0.3)
    return cues


def write_srt(cues, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, z, s) in enumerate(cues, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(z)}\n{s}\n\n")


def estimate_cues(text, cps=13.0):
    sentences = split_sentences(text)
    t, cues = 0.0, []
    for s in sentences:
        d = max(1.5, len(s) / cps)
        cues.append([t, t + d, s])
        t += d + 0.35
    return cues


def run_tts(text_file, voice, rate, workdir):
    if not shutil.which("edge-tts"):
        sys.exit("edge-tts not found: pip3 install edge-tts")
    mp3 = os.path.join(workdir, "narration.mp3")
    srt = os.path.join(workdir, "narration.srt")
    subprocess.run(["edge-tts", "--voice", voice, f"--rate={rate}",
                    "--file", text_file, "--write-media", mp3,
                    "--write-subtitles", srt], check=True)
    return mp3, parse_srt(srt)


# ---------------------------------------------------------------- render ---

def make_background(image_path, title, font_small):
    if image_path:
        img = Image.open(image_path).convert("RGB")
        s = max(W / img.width, H / img.height)
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        l, t = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((l, t, l + W, t + H))
        # darken + green tint so the text stays readable
        gray = img.convert("L").point(lambda p: int(p * 0.28))
        img = Image.merge("RGB", (gray.point(lambda p: int(p * 0.5)), gray, gray.point(lambda p: int(p * 0.6))))
    else:
        img = Image.new("RGB", (W, H), (4, 10, 6))
        # soft radial glow in the middle
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse((W * 0.1, H * 0.05, W * 0.9, H * 0.95), fill=28)
        glow = glow.filter(ImageFilter.GaussianBlur(220))
        img = Image.merge("RGB", (glow.point(lambda p: p // 3), glow, glow.point(lambda p: p // 2)))

    d = ImageDraw.Draw(img)
    d.rectangle((80, 60, W - 80, 64), fill=DIM_GREEN)
    d.text((80, 18), title, font=font_small, fill=GREEN)
    d.text((W - 80, 18), "INTERFEJS 2.1", font=font_small, fill=DIM_GREEN, anchor="ra")
    d.rectangle((80, H - 70, W - 80, H - 66), fill=DIM_GREEN)
    d.text((80, H - 55), "PRIORYTET: ZAŁOGA // KANAŁ: OGÓLNY", font=font_small, fill=DIM_GREEN)
    return img


def make_scanlines():
    sl = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(sl)
    for y in range(0, H, 4):
        d.line((0, y, W, y), fill=170)
    return sl


def build_blocks(cues, wrap, upper):
    blocks = []
    for start, end, text in cues:
        t = text.upper() if upper else text
        blocks.append((start, end, textwrap.wrap(t, wrap) or [""]))
    return blocks


def render_text_layer(t, blocks, font, line_h, max_lines, cursor_on):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = []  # (text, colour)
    for i, (start, end, wrapped) in enumerate(blocks):
        if t < start:
            break
        full = "\n".join(wrapped)
        dur = max(0.6, (end - start) * 0.9)
        n = min(len(full), int(len(full) * (t - start) / dur) + 1)
        shown = full[:n]
        is_current = i == len(blocks) - 1 or t < blocks[i + 1][0]
        colour = GREEN if is_current else DIM_GREEN
        if lines:
            lines.append(("", colour))
        prefix = "> "
        for j, l in enumerate(shown.split("\n")):
            lines.append(((prefix if j == 0 else "  ") + l, colour))
    if not lines:
        lines = [("> ", GREEN)]
    lines = lines[-max_lines:]
    x0 = 140
    y0 = 140
    for k, (txt, col) in enumerate(lines):
        d.text((x0, y0 + k * line_h), txt, font=font, fill=col)
    if cursor_on:
        last = lines[-1][0]
        cx = x0 + d.textlength(last, font=font) + 6
        cy = y0 + (len(lines) - 1) * line_h
        d.rectangle((cx, cy + 6, cx + font.size * 0.55, cy + font.size + 4), fill=GREEN)
    return layer


def render_video(cues, audio, out, image, font_path, wrap, upper, hum, title):
    font = load_font(46, font_path)
    font_small = load_font(28, font_path)
    line_h = 66
    max_lines = (H - 140 - 120) // line_h

    shifted = [[a + LEAD_IN, z + LEAD_IN, s] for a, z, s in cues]
    blocks = build_blocks(shifted, wrap, upper)
    total = (shifted[-1][1] if shifted else 5) + TAIL
    nframes = int(total * FPS)

    bg = make_background(image, title, font_small)
    scan = make_scanlines()
    black = Image.new("RGB", (W, H))

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    filters, maps = [], ["-map", "0:v"]
    inputs = 1
    mix = []
    if audio:
        cmd += ["-i", audio]
        ms = int(LEAD_IN * 1000)
        filters.append(f"[{inputs}:a]adelay={ms}|{ms},aecho=0.8:0.5:40:0.12[v]")
        mix.append("[v]")
        inputs += 1
    if hum:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anoisesrc=color=brown:amplitude=0.6:seed=7"]
        filters.append(f"[{inputs}:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,"
                       f"afade=t=out:st={max(0, total - 2):.2f}:d=2[h]")
        mix.append("[h]")
        inputs += 1
    if mix:
        if len(mix) > 1:
            filters.append("".join(mix) + f"amix=inputs={len(mix)}:duration=longest:normalize=0[a]")
        else:
            filters.append(f"{mix[0]}anull[a]")
        cmd += ["-filter_complex", ";".join(filters)]
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-t", f"{total:.2f}", "-movflags", "+faststart", out]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rnd = random.Random(42)
    for f in range(nframes):
        t = f / FPS
        cursor_on = (int(t * 2.5) % 2) == 0
        text = render_text_layer(t, blocks, font, line_h, max_lines, cursor_on)
        glow = text.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(6)).resize((W, H))
        mask = text.convert("L").point(lambda p: 255 if p > 20 else 0)
        frame = Image.composite(text, bg, mask)
        frame = ImageChops.add(frame, glow)            # phosphor glow
        frame = Image.composite(frame, black, scan)    # CRT scanlines
        flicker = 0.94 + 0.06 * rnd.random()
        if t < 0.6:  # power-on fade
            flicker *= t / 0.6
        lut = [min(255, int(i * flicker)) for i in range(256)] * 3
        frame = frame.point(lut)
        proc.stdin.write(frame.tobytes())
        if f % (FPS * 5) == 0:
            print(f"\r  rendering {t:5.1f}s / {total:.1f}s", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\r  done: {out} ({total:.1f}s)            ")
    if proc.returncode:
        sys.exit("ffmpeg failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text")
    ap.add_argument("-o", "--out")
    ap.add_argument("--image", help="background image (darkened behind the text)")
    ap.add_argument("--voice", default="pl-PL-ZofiaNeural", help="or pl-PL-MarekNeural")
    ap.add_argument("--rate", default="-10%", help="speech rate, e.g. -15%%")
    ap.add_argument("--audio", help="use your own narration (e.g. from ElevenLabs) instead of edge-tts")
    ap.add_argument("--srt", help="subtitles matching --audio (skips auto-alignment)")
    ap.add_argument("--whisper-model", default="small",
                    help="model for aligning --audio: base (fast), small (default), medium (most accurate)")
    ap.add_argument("--no-align", action="store_true", help="with --audio: estimate timing instead of Whisper")
    ap.add_argument("--no-tts", action="store_true", help="no voice, estimated timing (preview)")
    ap.add_argument("--no-hum", action="store_true", help="no ship-hum background")
    ap.add_argument("--no-upper", action="store_true", help="keep original letter case")
    ap.add_argument("--wrap", type=int, default=54, help="characters per line")
    ap.add_argument("--font")
    ap.add_argument("--title", default="MU/TH/UR 6000 :: USCSS MONTERO")
    a = ap.parse_args()

    out = a.out or os.path.splitext(a.text)[0] + ".mp4"
    with open(a.text, encoding="utf-8") as f:
        raw = f.read().strip()

    with tempfile.TemporaryDirectory() as tmp:
        if a.audio:
            audio = a.audio
            if a.srt:
                cues = parse_srt(a.srt)
            else:
                cues = None if a.no_align else align_cues(raw, audio, a.whisper_model)
                if cues is None:
                    cues = estimate_cues(raw)
                else:
                    srt_out = os.path.splitext(out)[0] + "_napisy.srt"
                    write_srt(cues, srt_out)
                    print(f"  subtitles saved: {srt_out} (fix by hand and pass with --srt if needed)")
        elif a.no_tts:
            audio, cues = None, estimate_cues(raw)
        else:
            print(f"  narration: {a.voice} ({a.rate})")
            audio, cues = run_tts(a.text, a.voice, a.rate, tmp)
            shutil.copy(audio, os.path.splitext(out)[0] + "_lektor.mp3")
        render_video(cues, audio, out, a.image, a.font, a.wrap, not a.no_upper, not a.no_hum, a.title)


if __name__ == "__main__":
    main()
