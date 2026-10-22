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


BAR_WIDTH = 15
FILLED, EMPTY = "█", "░"
EPS = 1e-9


@dataclass(frozen=True)
class Timing:
    type_speed: float = 22.0
    status_pause: float = 0.7
    bar_time: float = 1.5
    count_time: float = 2.0
    hold: float = 2.0
    gap: float = 0.25
    start: float = 0.0


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    show: object
    final: str


def value_text(step, p):
    return f"{round(step.start + (step.end - step.start) * p)}{step.label}"


def bar_text(step, p):
    n = round(BAR_WIDTH * p)
    return FILLED * n + EMPTY * (BAR_WIDTH - n) + "  " + value_text(step, p)


class Boot:
    def __init__(self, segments, clicks, duration):
        self.segments, self.clicks, self.duration = segments, clicks, duration

    def lines_at(self, t):
        return [s.final if t >= s.end else s.show(t) for s in self.segments if t >= s.start]


def plan(steps, timing, wrap, upper):
    case = str.upper if upper else str
    leaders = [len(case(s.text)) for s in steps if s.kind in ("status", "count")]
    col = max(leaders, default=0) + 5
    speed = timing.type_speed
    clicks, segments, t = [], [], timing.start

    def lead(text):
        return f"{text} {'.' * (col - len(text) - 2)} "

    def typing(start, typed, after=lambda now, done: ""):
        clicks.extend(start + i / speed for i, ch in enumerate(typed) if not ch.isspace())
        done = start + len(typed) / speed

        def show(t):
            if t < done:
                return typed[:int((t - start) * speed + EPS) + 1]
            return typed + after(t, done)
        return done, show

    def check(step, *lines):
        for line in lines:
            if len(line) > wrap:
                fail(step.line, f"{line!r} is {len(line)} characters, --wrap is {wrap}")

    for step in steps:
        text = case(step.text)
        if step.kind == "blank":
            segments.append(Segment(t, t, lambda t: "", ""))
            end = t
        elif step.kind == "line":
            end, show = typing(t, text)
            check(step, text)
            segments.append(Segment(t, end, show, text))
        elif step.kind == "status":
            typed = lead(text)
            done, show = typing(t, typed)
            end = done + timing.status_pause
            final = typed + case(step.value)
            check(step, final)
            segments.append(Segment(t, end, show, final))
        else:
            typed = lead(text) if step.kind == "count" else text + " "
            span = timing.count_time if step.kind == "count" else timing.bar_time
            fill = value_text if step.kind == "count" else bar_text

            def after(now, done, step=step, span=span, fill=fill):
                return fill(step, min(1.0, (now - done) / span) if span else 1.0)
            done, show = typing(t, typed, after)
            end = done + span
            check(step, typed + fill(step, 0.0), typed + fill(step, 1.0))
            segments.append(Segment(t, end, show, typed + fill(step, 1.0)))
        t = end + timing.gap
    duration = (t - timing.gap if steps else timing.start) + timing.hold
    return Boot(segments, clicks, duration)
