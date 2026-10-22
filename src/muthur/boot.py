"""The optional [BOOT start] ... [BOOT end] block at the top of the intro file."""
import difflib
import re
import sys
from dataclasses import dataclass

MARKER = re.compile(r"\[\s*(boot|crt)\s+(start|end)\s*\]", re.IGNORECASE)
TAG = re.compile(r"\[\s*([^\]:]+?)\s*:(.*)\]")
KEY = re.compile(r",\s*(text|label)\s*:", re.IGNORECASE)
RANGE = re.compile(r"(-?\d+)\s*\.\.\s*(-?\d+)")
TAGS = {"progressbar": ("ProgressBar", "bar"), "progressvalue": ("ProgressValue", "count"),
        "status": ("Status", "status")}


@dataclass(frozen=True)
class Step:
    kind: str
    text: str
    line: int
    value: str = ""
    start: int = 0
    end: int = 0
    label: str = ""


def fail(n, message):
    sys.exit(f"line {n}: {message}")


def parse_tag(n, name, rest):
    known = TAGS.get(name.lower())
    if known is None:
        close = difflib.get_close_matches(name.lower(), TAGS, n=1)
        hint = f" (did you mean {TAGS[close[0]][0]}?)" if close else ""
        fail(n, f"unknown tag {name}{hint}")
    tag, kind = known
    first, *pairs = KEY.split(rest)
    keys = {k.lower(): v.strip() for k, v in zip(pairs[::2], pairs[1::2])}
    text, first = keys.get("text", ""), first.strip()
    if not text:
        fail(n, f"{tag} needs text: ...")
    if kind == "status":
        if not first:
            fail(n, "Status needs a value before text:")
        return Step(kind, text, n, value=first)
    match = RANGE.fullmatch(first)
    if not match:
        fail(n, f"{tag} needs a range like 1..100, got {first!r}")
    return Step(kind, text, n, start=int(match[1]), end=int(match[2]), label=keys.get("label", ""))


def parse_line(n, line):
    if not line:
        return Step("blank", "", n)
    match = TAG.fullmatch(line)
    if match:
        return parse_tag(n, match[1], match[2])
    return Step("line", line, n)


def is_tag(line):
    match = TAG.fullmatch(line)
    return bool(MARKER.fullmatch(line) or (match and match[1].lower() in TAGS))


def split_boot(text):
    lines = text.split("\n")
    top = next((i for i, l in enumerate(lines) if l.strip()), len(lines))
    first = MARKER.fullmatch(lines[top].strip()) if top < len(lines) else None
    if not first or first[2].lower() != "start":
        check_outside(lines, 0)
        return [], text
    end = next((i for i in range(top + 1, len(lines))
                if (m := MARKER.fullmatch(lines[i].strip())) and m[2].lower() == "end"), None)
    if end is None:
        fail(top + 1, f"{lines[top].strip()} has no [BOOT end]")
    steps = []
    for i in range(top + 1, end):
        line = lines[i].strip()
        if MARKER.fullmatch(line):
            fail(i + 1, f"unexpected {line} inside the boot block")
        steps.append(parse_line(i + 1, line))
    check_outside(lines, end + 1)
    narrated = "\n".join(lines[end + 1:]).strip()
    if not narrated:
        fail(end + 1, "nothing to narrate after [BOOT end]")
    return steps, narrated


def check_outside(lines, start):
    for i in range(start, len(lines)):
        if is_tag(lines[i].strip()):
            fail(i + 1, f"{lines[i].strip()} is outside the boot block, which must be at the top of the file")
