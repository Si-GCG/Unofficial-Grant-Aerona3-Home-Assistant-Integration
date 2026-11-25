"""Generate the integration's brand images (custom_components/grant_aerona3/brand/).

Home Assistant 2026.3+ serves these for custom integrations. Run from the repo root:

    python3 Docs/brand/generate_brand.py

Needs Pillow only. The wordmark uses Pillow's bundled font (Aileron, public domain).
Original artwork: an outdoor heat pump fan inside a warm ring. It deliberately does
not use the manufacturer's logo, since this is an unofficial integration.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("custom_components/grant_aerona3/brand")

SUPER = 1024  # draw large, then downscale for smooth edges
BLUE_TOP = (52, 179, 216)
BLUE_BOTTOM = (14, 63, 99)
WARM = (255, 154, 60)
WHITE = (255, 255, 255)
TEXT_LIGHT_BG = (14, 63, 99)  # wordmark on a white background
TEXT_DARK_BG = (234, 244, 248)  # wordmark on a dark background
SUB_LIGHT_BG = (206, 100, 10)  # deeper orange so the subtitle reads on white


def _rounded_gradient(size: int) -> Image.Image:
    gradient = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(gradient)
    for y in range(size):
        t = y / (size - 1)
        colour = tuple(round(a + (b - a) * t) for a, b in zip(BLUE_TOP, BLUE_BOTTOM))
        draw.line([(0, y), (size, y)], fill=colour + (255,))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255)
    gradient.putalpha(mask)
    return gradient


def _blade(cx: float, cy: float, base_angle: float, r_in: float, r_out: float, sweep: float, half_width: float):
    """One curved fan blade as a polygon."""
    steps = 40
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        r = r_in + (r_out - r_in) * t
        centre = base_angle + sweep * t
        width = half_width * math.sin(math.pi * t) ** 0.75 / r  # angular half-width
        left.append((cx + r * math.cos(centre + width), cy + r * math.sin(centre + width)))
        right.append((cx + r * math.cos(centre - width), cy + r * math.sin(centre - width)))
    return left + right[::-1]


def make_icon(size: int = SUPER) -> Image.Image:
    image = _rounded_gradient(size)
    cx = cy = size / 2

    # Fan well: a translucent layer composited over the gradient. Drawing the
    # translucent fill straight onto the image would overwrite its alpha channel.
    well = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(well).ellipse(
        [cx - 0.375 * size, cy - 0.375 * size, cx + 0.375 * size, cy + 0.375 * size], fill=(7, 30, 50, 110)
    )
    image = Image.alpha_composite(image, well)
    draw = ImageDraw.Draw(image)

    # warm ring
    ring = 0.038 * size
    draw.ellipse(
        [cx - 0.375 * size, cy - 0.375 * size, cx + 0.375 * size, cy + 0.375 * size],
        outline=WARM + (255,),
        width=round(ring),
    )

    for i in range(5):
        draw.polygon(
            _blade(cx, cy, math.radians(-90 + i * 72), 0.06 * size, 0.325 * size, math.radians(52), 0.085 * size),
            fill=WHITE + (255,),
        )
    hub = 0.07 * size
    draw.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=WARM + (255,))
    return image


def make_logo(text_colour: tuple[int, int, int], sub_colour: tuple[int, int, int], height: int = 512) -> Image.Image:
    """Icon plus wordmark, trimmed to its content."""
    scale = 4
    canvas_h = height * scale
    icon = make_icon().resize((canvas_h, canvas_h), Image.LANCZOS)
    title_font = ImageFont.load_default(size=int(canvas_h * 0.34))
    sub_font = ImageFont.load_default(size=int(canvas_h * 0.15))
    title, sub = "Aerona3", "HEAT PUMP"

    def measure(font, text, stroke):
        left, top, right, bottom = font.getbbox(text, stroke_width=stroke)
        return left, top, right - left, bottom - top

    stroke = max(1, int(canvas_h * 0.006))
    tl, tt, tw, th = measure(title_font, title, stroke)
    sl, st, sw, sh = measure(sub_font, sub, 0)
    spacing = int(canvas_h * 0.035)  # extra letter-spacing for the subtitle
    sub_width = sw + spacing * (len(sub) - 1)

    gap = int(canvas_h * 0.07)
    line_gap = int(canvas_h * 0.07)
    text_w = max(tw, sub_width)
    text_h = th + line_gap + sh
    canvas = Image.new("RGBA", (canvas_h + gap + text_w, canvas_h), (0, 0, 0, 0))
    canvas.alpha_composite(icon, (0, 0))
    draw = ImageDraw.Draw(canvas)

    top = (canvas_h - text_h) // 2
    x = canvas_h + gap
    draw.text((x - tl, top - tt), title, font=title_font, fill=text_colour + (255,), stroke_width=stroke, stroke_fill=text_colour + (255,))
    y = top + th + line_gap - st
    for ch in sub:  # manual letter-spacing
        draw.text((x, y), ch, font=sub_font, fill=sub_colour + (255,))
        x += sub_font.getlength(ch) + spacing
    canvas = canvas.crop(canvas.getbbox())
    return canvas.resize((round(canvas.width / scale), round(canvas.height / scale)), Image.LANCZOS)


def save(image: Image.Image, name: str) -> None:
    image.save(OUT / name, optimize=True)
    print(f"{name}: {image.width}x{image.height}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    save(icon.resize((512, 512), Image.LANCZOS), "icon@2x.png")
    save(icon.resize((256, 256), Image.LANCZOS), "icon.png")

    light = make_logo(TEXT_LIGHT_BG, SUB_LIGHT_BG, height=512)
    dark = make_logo(TEXT_DARK_BG, WARM, height=512)
    save(light, "logo@2x.png")
    save(light.resize((light.width // 2, light.height // 2), Image.LANCZOS), "logo.png")
    save(dark, "dark_logo@2x.png")
    save(dark.resize((dark.width // 2, dark.height // 2), Image.LANCZOS), "dark_logo.png")


if __name__ == "__main__":
    main()
