import re

from muthur.text import read_text, split_sentences


def srt_time(s):
    h, m, rest = s.strip().split(":")
    sec, frac = re.split(r"[,.]", rest)
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(frac.ljust(3, "0")[:3]) / 1000


def parse_srt(path):
    cues = []
    blocks = re.split(r"\n\s*\n", read_text(path).strip())
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
