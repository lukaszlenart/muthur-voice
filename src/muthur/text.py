import re
import unicodedata


def read_text(path):
    with open(path, encoding="utf-8-sig") as f:
        return unicodedata.normalize("NFC", f.read())


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def norm_word(w):
    return re.sub(r"[^0-9a-ząćęłńóśźż]", "", unicodedata.normalize("NFC", w).lower())
