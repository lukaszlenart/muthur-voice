import re
import unicodedata


def read_text(path):
    with open(path, encoding="utf-8-sig") as f:
        return unicodedata.normalize("NFC", f.read())


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def norm_word(w):
    return re.sub(r"[^0-9a-ząćęłńóśźż]", "", unicodedata.normalize("NFC", w).lower())


def respell(text, pronounce):
    """Swap written words for how the narrator should say them; Polish endings after a word are kept."""
    if not pronounce:
        return text
    words = "|".join(re.escape(w) for w in sorted(pronounce, key=len, reverse=True))
    return re.sub(rf"(?<!\w)({words})", lambda m: pronounce[m[1]], text)


def restore(text, pronounce):
    if not pronounce:
        return text
    written = {" ".join(spoken.split()): w for w, spoken in pronounce.items()}
    spoken = "|".join(r"\s+".join(map(re.escape, s.split())) for s in sorted(written, key=len, reverse=True))
    return re.sub(rf"(?<!\w)({spoken})", lambda m: written[" ".join(m[1].split())], text)
