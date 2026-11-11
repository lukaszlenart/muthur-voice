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
    """Swap written words for how the narrator should say them, ignoring case; Polish endings are kept.

    Returns the spoken text and the written words it replaced, in order, for `restore`.
    """
    if not pronounce:
        return text, []
    spoken = {w.lower(): s for w, s in pronounce.items()}
    replaced = []

    def swap(m):
        replaced.append(m[1])
        return spoken[m[1].lower()]

    return re.sub(rf"(?<!\w)({_alternation(pronounce)})", swap, text, flags=re.IGNORECASE), replaced


def restore(text, pronounce, replaced):
    """Put the written words back; `replaced` is an iterator over what `respell` replaced, consumed in order."""
    if not pronounce:
        return text
    written = {_key(s): w for w, s in pronounce.items()}
    return re.sub(rf"(?<!\w)({_alternation(pronounce.values())})",
                  lambda m: next(replaced, None) or written[_key(m[1])], text, flags=re.IGNORECASE)


def _key(spoken):
    return " ".join(spoken.split()).lower()


def _alternation(words):
    return "|".join(r"\s+".join(map(re.escape, w.split())) for w in sorted(words, key=len, reverse=True))
