"""Star icon drawing + .ico asset generation."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent / "assets"


def star_points(
    cx: float,
    cy: float,
    outer: float,
    inner: float,
    points: int = 5,
    rotation: float = -math.pi / 2,
) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for i in range(points * 2):
        angle = rotation + i * math.pi / points
        radius = outer if i % 2 == 0 else inner
        coords.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return coords


def draw_star(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    outer: float,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
) -> None:
    pts = star_points(cx, cy, outer, outer * 0.42)
    draw.polygon(pts, fill=fill, outline=outline)


def make_stars_icon(size: int = 64, active: bool = True) -> Image.Image:
    """Cluster of small stars — readable at tray (16px) and shortcut sizes."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        main = (255, 220, 70, 255)        # gold
        soft = (255, 170, 40, 255)        # amber
        outline = (90, 50, 0, 220)
        spark = (255, 245, 180, 255)
    else:
        main = (200, 205, 210, 255)
        soft = (150, 156, 164, 255)
        outline = (70, 75, 80, 200)
        spark = (220, 224, 228, 255)

    s = float(size)

    # Big center star
    draw_star(draw, s * 0.48, s * 0.48, s * 0.30, main, outline)
    # Smaller companions
    draw_star(draw, s * 0.78, s * 0.26, s * 0.145, soft, outline)
    draw_star(draw, s * 0.20, s * 0.74, s * 0.125, soft, outline)
    draw_star(draw, s * 0.74, s * 0.76, s * 0.095, main, outline)

    # Tiny sparkle dots
    for x, y, r in (
        (0.16, 0.20, 0.028),
        (0.90, 0.52, 0.022),
        (0.38, 0.88, 0.020),
        (0.58, 0.14, 0.016),
    ):
        draw.ellipse(
            (s * x - s * r, s * y - s * r, s * x + s * r, s * y + s * r),
            fill=spark,
        )

    return img


def write_ico(path: Path, active: bool) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    path.parent.mkdir(parents=True, exist_ok=True)
    # Pillow embeds resized variants from the master image
    master = make_stars_icon(256, active=active)
    master.save(path, format="ICO", sizes=[(s, s) for s in sizes])


def write_png(path: Path, size: int, active: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    make_stars_icon(size, active=active).save(path, format="PNG")


def generate_all() -> dict[str, Path]:
    ASSETS.mkdir(parents=True, exist_ok=True)
    paths = {
        "ico": ASSETS / "stars.ico",
        "ico_paused": ASSETS / "stars_paused.ico",
        "png": ASSETS / "stars.png",
        "png_paused": ASSETS / "stars_paused.png",
        "tray": ASSETS / "tray_on.png",
        "tray_paused": ASSETS / "tray_off.png",
    }
    write_ico(paths["ico"], active=True)
    write_ico(paths["ico_paused"], active=False)
    write_png(paths["png"], 256, active=True)
    write_png(paths["png_paused"], 256, active=False)
    write_png(paths["tray"], 64, active=True)
    write_png(paths["tray_paused"], 64, active=False)
    return paths


if __name__ == "__main__":
    out = generate_all()
    for name, path in out.items():
        print(f"{name}: {path}")
