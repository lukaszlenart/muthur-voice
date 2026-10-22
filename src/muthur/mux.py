import array
import random
import subprocess
import sys
import wave

from muthur.render import FPS, H, LEAD_IN, W

VOICE_FX = {
    "echo": "aecho=0.8:0.5:40:0.12",
    "intercom": "highpass=f=250,lowpass=f=4500,aecho=0.8:0.6:25:0.2,chorus=0.7:0.9:20:0.3:0.2:2",
    "old-intercom": "highpass=f=400,lowpass=f=3000,volume=3,asoftclip=type=tanh,volume=0.4,"
                    "aecho=0.8:0.7:60|110:0.3|0.2",
    "none": "",
}


def apply_fx(src, dst, fx):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", VOICE_FX[fx], dst]
    return subprocess.run(cmd).returncode == 0


RATE = 44100
CLICK = 0.006


def write_clicks(times, total, path):
    samples = array.array("h", bytes(2 * int(total * RATE)))
    rnd = random.Random(7)
    length = int(CLICK * RATE)
    for t in times:
        start, peak = int(t * RATE), rnd.uniform(0.6, 1.0) * 12000
        for i in range(min(length, len(samples) - start)):
            samples[start + i] = int(peak * (1 - i / length) ** 2 * rnd.uniform(-1, 1))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(samples.tobytes())


def ffmpeg_command(total, audio, hum, out, fx="echo", delay=LEAD_IN, clicks=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    filters, maps = [], ["-map", "0:v"]
    inputs = 1
    mix = []
    if audio:
        cmd += ["-i", audio]
        ms = int(delay * 1000)
        chain = f",{VOICE_FX[fx]}" if VOICE_FX[fx] else ""
        filters.append(f"[{inputs}:a]adelay={ms}|{ms}{chain}[v]")
        mix.append("[v]")
        inputs += 1
    if hum:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anoisesrc=color=brown:amplitude=0.6:seed=7"]
        filters.append(f"[{inputs}:a]lowpass=f=180,volume=0.25,afade=t=in:d=2,"
                       f"afade=t=out:st={max(0, total - 2):.2f}:d=2[h]")
        mix.append("[h]")
        inputs += 1
    if clicks:
        cmd += ["-i", clicks]
        filters.append(f"[{inputs}:a]anull[c]")
        mix.append("[c]")
        inputs += 1
    if mix:
        if len(mix) > 1:
            filters.append("".join(mix) + f"amix=inputs={len(mix)}:duration=longest:normalize=0[a]")
        else:
            filters.append(f"{mix[0]}anull[a]")
        cmd += ["-filter_complex", ";".join(filters)]
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    return cmd + maps + ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
                         "-pix_fmt", "yuv420p", "-t", f"{total:.2f}", "-movflags", "+faststart", out]


def encode(frames, total, cmd, out):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f, (t, data) in enumerate(frames):
        proc.stdin.write(data)
        if f % (FPS * 5) == 0:
            print(f"\r  rendering {t:5.1f}s / {total:.1f}s", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\r  done: {out} ({total:.1f}s)            ")
    if proc.returncode:
        sys.exit("ffmpeg failed")
