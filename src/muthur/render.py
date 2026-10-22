import os
import random
import sys
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
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def load_font(size, path=None):
    for p in ([path] if path else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    sys.exit("No monospace font found, pass one with --font")


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


def render_boot_layer(lines, font, line_h, max_lines, cursor_on):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = (lines or [""])[-max_lines:]
    x0 = 140
    y0 = 140
    for k, txt in enumerate(lines):
        d.text((x0, y0 + k * line_h), txt, font=font, fill=GREEN)
    if cursor_on:
        cx = x0 + d.textlength(lines[-1], font=font) + 6
        cy = y0 + (len(lines) - 1) * line_h
        d.rectangle((cx, cy + 6, cx + font.size * 0.55, cy + font.size + 4), fill=GREEN)
    return layer


def timeline(cues, offset=0.0):
    shifted = [[a + offset + LEAD_IN, z + offset + LEAD_IN, s] for a, z, s in cues]
    total = (shifted[-1][1] if shifted else 5) + TAIL
    return shifted, total


def iter_frames(cues, image, font_path, wrap, upper, title, boot=None):
    font = load_font(46, font_path)
    font_small = load_font(28, font_path)
    line_h = 66
    max_lines = (H - 140 - 120) // line_h
    shifted, total = timeline(cues, boot.duration if boot else 0.0)
    blocks = build_blocks(shifted, wrap, upper)
    bg = make_background(image, title, font_small)
    return total, _frames(total, blocks, bg, font, line_h, max_lines, boot)


def _frames(total, blocks, bg, font, line_h, max_lines, boot=None):
    scan = make_scanlines()
    black = Image.new("RGB", (W, H))
    rnd = random.Random(42)
    for f in range(int(total * FPS)):
        t = f / FPS
        cursor_on = (int(t * 2.5) % 2) == 0
        if boot and t < boot.duration:
            text = render_boot_layer(boot.lines_at(t), font, line_h, max_lines, cursor_on)
        else:
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
        yield t, frame.point(lut).tobytes()
