#!/usr/bin/env python3
"""Render a looping GIF preview for the GitHub profile README."""
import argparse
import math
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT, FRAME_COUNT = 900, 220, 24
BG = (16, 13, 32)
CYAN = (98, 234, 242)
VIOLET = (185, 128, 255)


def font(paths, size):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLE = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
], 24)
LABEL = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
], 11)
MICRO = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
], 9)
STARS = [
    ((i * 167 + 43) % (WIDTH - 40) + 20,
     (i * 83 + 19) % (HEIGHT - 30) + 12,
     2 if i % 7 == 0 else 1,
     0.7 + (i % 4) * 0.28,
     i % 2)
    for i in range(54)
]


def render(frame):
    image = Image.new("RGBA", (WIDTH, HEIGHT), (*BG, 255))
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((275, -120, 725, 300), fill=(74, 42, 112, 76))
    glow_draw.ellipse((520, 30, 860, 280), fill=(25, 92, 116, 30))
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(64)))
    draw = ImageDraw.Draw(image)

    for x, y, radius, speed, tint in STARS:
        sy = (y + frame * speed) % HEIGHT
        color = CYAN if tint else (199, 165, 255)
        alpha = 120 + (frame % 5) * 20
        draw.ellipse((x, sy, x + radius, sy + radius), fill=(*color, alpha))

    columns, rows = 38, 5
    cell, gap = 13, 6
    total_width = columns * (cell + gap) - gap
    x0, y0 = (WIDTH - total_width) // 2, 118
    for row in range(rows):
        for column in range(columns):
            phase = (column * 7 + row * 13 + frame * 2) % 31
            lit = ((column * 11 + row * 17) % 23) < (
                4 + int(2 * (1 + math.sin((frame + column * 2) * 0.38)))
            )
            if lit:
                color = CYAN if phase < 13 else VIOLET
                alpha = 180 + int(50 * (0.5 + 0.5 * math.sin((frame + column) * 0.48)))
            else:
                color, alpha = (35, 28, 56), 220
            x = x0 + column * (cell + gap)
            y = y0 + row * (cell + gap)
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=3, fill=(*color, alpha))

    draw.text((38, 34), "SPACE SHOOTER // HEATMAP", font=TITLE, fill=(226, 211, 255, 255))
    draw.text((40, 70), "ARCADE ACTIVITY FIELD", font=LABEL, fill=(127, 238, 244, 255))
    draw.text((40, 91), "SECTOR 01  ·  SIGNALS IN MOTION", font=MICRO, fill=(157, 145, 183, 255))
    draw.line((38, 103, WIDTH - 40, 103), fill=(64, 48, 87, 210), width=1)

    ship_x = WIDTH * 0.54 + math.sin(2 * math.pi * frame / FRAME_COUNT) * 170
    ship_y = 150 + math.sin(2 * math.pi * frame / FRAME_COUNT + 0.8) * 5
    halo = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse(
        (ship_x - 36, ship_y - 36, ship_x + 36, ship_y + 36),
        fill=(73, 232, 246, 115),
    )
    image = Image.alpha_composite(image, halo.filter(ImageFilter.GaussianBlur(18)))
    draw = ImageDraw.Draw(image)
    flame = 9 + (frame % 3) * 3
    draw.polygon(
        [(ship_x, ship_y + 23 + flame), (ship_x - 5, ship_y + 10), (ship_x + 5, ship_y + 10)],
        fill=(78, 234, 245, 240),
    )
    draw.polygon(
        [(ship_x, ship_y - 21), (ship_x + 11, ship_y + 13), (ship_x, ship_y + 8), (ship_x - 11, ship_y + 13)],
        fill=(224, 204, 255, 255), outline=(124, 244, 248, 255),
    )
    draw.polygon(
        [(ship_x, ship_y - 13), (ship_x + 4, ship_y + 5), (ship_x, ship_y + 2), (ship_x - 4, ship_y + 5)],
        fill=(128, 86, 190, 255),
    )

    for index in range(2):
        target_x = 590 + index * 145 + math.sin(frame * 0.35 + index) * 26
        target_y = ((frame * (2.2 + index * 0.35) + index * 68) % 118) + 24
        radius = 7
        draw.polygon(
            [(target_x, target_y - radius), (target_x + radius, target_y),
             (target_x, target_y + radius), (target_x - radius, target_y)],
            fill=(209, 157, 255, 255),
        )
        draw.ellipse((target_x - 2, target_y - 2, target_x + 2, target_y + 2), fill=(255, 238, 255, 255))

    draw.rounded_rectangle((8, 8, WIDTH - 9, HEIGHT - 9), radius=18, outline=(89, 67, 124, 235), width=1)
    return image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="space-shooter/space-shooter-heatmap.gif")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    frames = [render(index) for index in range(FRAME_COUNT)]
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=95,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {args.output} ({FRAME_COUNT} frames)")


if __name__ == "__main__":
    main()
