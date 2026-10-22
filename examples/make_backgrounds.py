"""Draw the example backgrounds: uv run python examples/make_backgrounds.py"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1920, 1080
HERE = Path(__file__).resolve().parent


def blank(color=(0, 0, 0)):
    return Image.new("RGB", (W, H), color)


def glow(img, shape_draw, radius, strength=1.0):
    layer = Image.new("L", img.size, 0)
    shape_draw(ImageDraw.Draw(layer))
    layer = layer.filter(ImageFilter.GaussianBlur(radius)).point(lambda p: min(255, int(p * strength)))
    return ImageChops.add(img, Image.merge("RGB", (layer, layer, layer)))


def stars(img, rng, count, max_size=3):
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.randrange(W), rng.randrange(H)
        b = int(255 * rng.random() ** 2.5)
        r = rng.choice([0, 0, 0, 1, 1, max_size - 1])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(b, b, b))
    return img


def planet(img, cx, cy, radius, light_angle):
    lx, ly = math.cos(light_angle), math.sin(light_angle)
    body = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(body)
    for i in range(radius, 0, -3):
        shift = (radius - i) * 0.55
        b = int(30 + 200 * (1 - i / radius) ** 0.6)
        d.ellipse((cx + lx * shift - i, cy + ly * shift - i, cx + lx * shift + i, cy + ly * shift + i), fill=b)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    rng = random.Random(7)
    bands = ImageDraw.Draw(body)
    for _ in range(10):
        y = cy + rng.uniform(-0.9, 0.9) * radius
        tilt = rng.uniform(-30, 30)
        bands.line([(cx + x, y + tilt * x / radius + 12 * math.sin(x / 90)) for x in range(-radius, radius + 1, 20)],
                   fill=rng.randint(40, 110), width=rng.randint(10, 40))
    body = body.filter(ImageFilter.GaussianBlur(14))
    img.paste(Image.merge("RGB", (body, body, body)), mask=mask)
    return glow(img, lambda g: g.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                                         outline=255, width=14), 30, 1.4)


def orbit():
    rng = random.Random(1)
    img = stars(blank(), rng, 1400)
    img = planet(img, int(W * 0.72), int(H * 1.05), 720, math.radians(-120))
    return glow(img, lambda g: g.ellipse((150, 120, 330, 300), fill=255), 60, 0.9)


def freighter(img, x0, y0, length):
    rng = random.Random(3)
    d = ImageDraw.Draw(img)
    d.polygon([(x0, y0), (x0 + length * 0.08, y0 - 34), (x0 + length, y0 - 40), (x0 + length, y0 + 46),
               (x0 + length * 0.08, y0 + 40)], fill=0)
    x = x0 + length * 0.1
    while x < x0 + length * 0.8:
        w = rng.randint(14, 60)
        d.rectangle((x, y0 - 34 - rng.randint(4, 30), x + w, y0), fill=0)
        d.rectangle((x, y0, x + w, y0 + 40 + rng.randint(2, 22)), fill=0)
        x += w + rng.randint(2, 10)
    d.rectangle((x0 + length * 0.18, y0 - 92, x0 + length * 0.3, y0 - 30), fill=0)
    d.rectangle((x0 + length * 0.21, y0 - 130, x0 + length * 0.26, y0 - 90), fill=0)
    d.line((x0 + length * 0.235, y0 - 130, x0 + length * 0.235, y0 - 200), fill=0, width=4)
    d.rectangle((x0 + length * 0.8, y0 - 80, x0 + length, y0 + 86), fill=0)
    engines = [(x0 + length + 6, y0 - 50 + i * 52) for i in range(3)]
    img = glow(img, lambda g: [g.ellipse((ex - 8, ey - 14, ex + 26, ey + 14), fill=255) for ex, ey in engines], 14, 2.2)
    bx, by = x0 + length * 0.235, y0 - 200
    return glow(img, lambda g: g.ellipse((bx - 6, by - 6, bx + 6, by + 6), fill=255), 8, 3.0)


def signal():
    rng = random.Random(2)
    img = stars(blank(), rng, 900)
    img = glow(img, lambda g: g.ellipse((W * 0.15, H * 0.2, W * 0.95, H * 1.3), fill=150), 160)
    img = glow(img, lambda g: g.ellipse((W * 0.35, H * 0.45, W * 0.75, H * 0.9), fill=255), 90)
    return freighter(img, int(W * 0.12), int(H * 0.56), int(W * 0.7))


def frame_at(z, cx=W / 2, cy=H / 2, half_w=1300, half_h=760):
    s = 1 / z
    return cx - half_w * s, cy - half_h * s, cx + half_w * s, cy + half_h * s


def corridor():
    img = blank((10, 10, 10))
    d = ImageDraw.Draw(img)
    depths = [1 + i * 0.55 for i in range(14)]
    for i, z in enumerate(depths):
        x1, y1, x2, y2 = frame_at(z)
        shade = int(150 / z ** 0.8)
        d.rectangle((x1, y1, x2, y2), outline=(shade,) * 3, width=max(2, int(28 / z)))
        if i < len(depths) - 1:
            nx1, ny1, nx2, ny2 = frame_at(depths[i + 1])
            for k in range(1, 4):
                t = k / 4
                d.line((x1, y1 + (y2 - y1) * t, nx1, ny1 + (ny2 - ny1) * t), fill=(shade // 2,) * 3, width=2)
                d.line((x2, y1 + (y2 - y1) * t, nx2, ny1 + (ny2 - ny1) * t), fill=(shade // 2,) * 3, width=2)
            for k in range(1, 8):
                t = k / 8
                d.line((x1 + (x2 - x1) * t, y2, nx1 + (nx2 - nx1) * t, ny2), fill=(shade // 2,) * 3, width=2)
    for z in depths[::2]:
        x1, y1, x2, y2 = frame_at(z)
        w = (x2 - x1) * 0.12
        img = glow(img, lambda g, x1=x1, y1=y1, x2=x2, w=w: g.rectangle(
            ((x1 + x2) / 2 - w, y1 + 6, (x1 + x2) / 2 + w, y1 + 6 + 40 / z), fill=255), 12 / z + 4, 1.6)
    x1, y1, x2, y2 = frame_at(depths[-1] + 1)
    return glow(img, lambda g: g.rectangle((x1, y1, x2, y2), fill=255), 25, 1.2)


def wake_up():
    img = blank((8, 8, 8))
    cx, cy = W / 2, H / 2
    img = glow(img, lambda g: g.ellipse((cx - 300, cy - 300, cx + 300, cy + 300), fill=200), 140)
    d = ImageDraw.Draw(img)
    d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), fill=(30, 30, 30), outline=(170, 170, 170), width=6)
    windows = []
    for i in range(7):
        a = math.radians(-90 + i * 360 / 7)
        pod = Image.new("L", (360, 140), 0)
        pd = ImageDraw.Draw(pod)
        pd.rounded_rectangle((4, 4, 355, 135), radius=65, fill=60, outline=190, width=6)
        pd.rounded_rectangle((50, 34, 310, 106), radius=36, fill=220 if i == 0 else 120)
        rotated = pod.rotate(-math.degrees(a), expand=True, resample=Image.BICUBIC)
        px, py = cx + math.cos(a) * 320, cy + math.sin(a) * 320
        img.paste(Image.merge("RGB", (rotated,) * 3),
                  (int(px - rotated.width / 2), int(py - rotated.height / 2)), rotated)
        windows.append((px, py))
    img = glow(img, lambda g: [g.ellipse((x - 120, y - 120, x + 120, y + 120), fill=90) for x, y in windows], 60)
    return glow(img, lambda g: g.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), fill=255), 40, 1.5)


def cold_start():
    rng = random.Random(5)
    img = blank((6, 6, 6))
    cx, top, bottom = W * 0.62, H * 0.08, H * 0.98
    img = glow(img, lambda g: g.rectangle((cx - 170, top, cx + 170, bottom), fill=150), 160)
    d = ImageDraw.Draw(img)
    d.rectangle((cx - 110, top, cx + 110, bottom), fill=(40, 40, 40), outline=(160, 160, 160), width=5)
    for y in range(int(top) + 60, int(bottom), 110):
        d.rectangle((cx - 135, y, cx + 135, y + 22), fill=(90, 90, 90))
    img = glow(img, lambda g: g.rectangle((cx - 40, top + 30, cx + 40, bottom), fill=255), 45, 1.6)
    grille = img.copy()
    d = ImageDraw.Draw(grille)
    for y in range(0, H, 72):
        d.rectangle((0, y, W, y + 14), fill=(4, 4, 4))
    img = Image.blend(img, grille, 0.75)
    d = ImageDraw.Draw(img)
    for _ in range(24):
        x, y = rng.randrange(80, int(cx) - 260), rng.choice(range(7, H, 72))
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(rng.randint(80, 200),) * 3)
    return img


SCENES = {"orbit": orbit, "signal": signal, "corridor": corridor, "wake-up": wake_up, "cold-start": cold_start}


def main():
    for name, draw in SCENES.items():
        out = HERE / name / "background.jpg"
        out.parent.mkdir(exist_ok=True)
        draw().save(out, quality=88)
        print(f"  {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
