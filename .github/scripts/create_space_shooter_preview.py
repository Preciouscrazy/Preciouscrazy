#!/usr/bin/env python3
"""Build an animated Space Shooter heatmap from GitHub's contribution calendar."""
import argparse
import json
import math
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT, FRAME_COUNT = 900, 220, 32
WEEK_COUNT = 53
CELL, GAP = 11, 4
BACKGROUND = (16, 13, 32)
CYAN = (98, 234, 242)
VIOLET = (185, 128, 255)
LEVEL_COLORS = {
    "NONE": (34, 28, 54),
    "FIRST_QUARTILE": (63, 43, 94),
    "SECOND_QUARTILE": (106, 71, 150),
    "THIRD_QUARTILE": (57, 160, 179),
    "FOURTH_QUARTILE": (98, 234, 242),
}


def font(paths, size):
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLE = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
], 22)
LABEL = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
], 10)
SMALL = font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
], 8)
STARS = [
    ((i * 167 + 43) % (WIDTH - 36) + 18,
     (i * 83 + 13) % 82 + 8,
     2 if i % 7 == 0 else 1,
     0.45 + (i % 4) * 0.2,
     i % 2)
    for i in range(46)
]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""


def fetch_calendar(login, token):
    now = datetime.now(timezone.utc)
    variables = {
        "login": login,
        "from": (now - timedelta(days=365)).isoformat().replace("+00:00", "Z"),
        "to": now.isoformat().replace("+00:00", "Z"),
    }
    payload = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "space-shooter-contribution-heatmap",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + "; ".join(e.get("message", "query failed") for e in result["errors"]))
    user = (result.get("data") or {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {login!r} was not returned by GraphQL.")
    calendar = user["contributionsCollection"]["contributionCalendar"]
    if not calendar.get("weeks"):
        raise RuntimeError("GitHub returned an empty contribution calendar.")
    return calendar, now


def calendar_grid(calendar):
    weeks = calendar["weeks"][-WEEK_COUNT:]
    padding = WEEK_COUNT - len(weeks)
    grid = [["NONE" for _ in range(7)] for _ in range(WEEK_COUNT)]
    for index, week in enumerate(weeks, start=padding):
        for day in week["contributionDays"]:
            # GitHub's graph starts on Sunday; Python's weekday starts on Monday.
            row = (datetime.strptime(day["date"], "%Y-%m-%d").weekday() + 1) % 7
            level = day.get("contributionLevel", "NONE")
            grid[index][row] = level if level in LEVEL_COLORS else "NONE"
    return grid


def render_frame(frame, grid, total, updated):
    image = Image.new("RGBA", (WIDTH, HEIGHT), (*BACKGROUND, 255))
    haze = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze)
    haze_draw.ellipse((245, -105, 690, 170), fill=(74, 42, 112, 70))
    haze_draw.ellipse((515, -35, 875, 150), fill=(25, 92, 116, 34))
    image = Image.alpha_composite(image, haze.filter(ImageFilter.GaussianBlur(58)))
    draw = ImageDraw.Draw(image)

    for x, y, radius, speed, tint in STARS:
        sy = (y + frame * speed) % 94
        color = CYAN if tint else (199, 165, 255)
        alpha = 90 + (frame % 5) * 18
        draw.ellipse((x, sy, x + radius, sy + radius), fill=(*color, alpha))

    draw.text((34, 20), "SPACE SHOOTER // HEATMAP", font=TITLE, fill=(226, 211, 255, 255))
    draw.text((36, 53), "LIVE GITHUB CONTRIBUTIONS · LAST 12 MONTHS", font=LABEL, fill=(127, 238, 244, 255))
    draw.text((865, 27), f"{total:,} CONTRIBUTIONS", font=LABEL, fill=(127, 238, 244, 255), anchor="ra")

    x0 = (WIDTH - (WEEK_COUNT * (CELL + GAP) - GAP)) // 2
    y0 = 96
    step = CELL + GAP
    for week in range(WEEK_COUNT):
        for day in range(7):
            x = x0 + week * step
            y = y0 + day * step
            color = LEVEL_COLORS[grid[week][day]]
            draw.rounded_rectangle((x, y, x + CELL, y + CELL), radius=2, fill=(*color, 255))

    # The small ship travels across the calendar while the contribution levels stay data-accurate.
    progress = frame / (FRAME_COUNT - 1)
    position = 0.5 - 0.5 * math.cos(2 * math.pi * progress)
    ship_x = x0 + CELL / 2 + position * (WEEK_COUNT - 1) * step
    ship_y = y0 + 3 * step + CELL / 2 + math.sin(progress * 2 * math.pi) * 1.4
    ship_glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(ship_glow).ellipse(
        (ship_x - 20, ship_y - 20, ship_x + 20, ship_y + 20),
        fill=(73, 232, 246, 115),
    )
    image = Image.alpha_composite(image, ship_glow.filter(ImageFilter.GaussianBlur(11)))
    draw = ImageDraw.Draw(image)
    flame = 5 + (frame % 3) * 2
    draw.polygon(
        [(ship_x, ship_y + 9 + flame), (ship_x - 3, ship_y + 5), (ship_x + 3, ship_y + 5)],
        fill=(78, 234, 245, 255),
    )
    draw.polygon(
        [(ship_x, ship_y - 9), (ship_x + 5, ship_y + 6), (ship_x, ship_y + 4), (ship_x - 5, ship_y + 6)],
        fill=(224, 204, 255, 255), outline=(124, 244, 248, 255),
    )
    draw.polygon(
        [(ship_x, ship_y - 5), (ship_x + 2, ship_y + 2), (ship_x, ship_y + 1), (ship_x - 2, ship_y + 2)],
        fill=(128, 86, 190, 255),
    )

    draw.text((35, 207), "PUBLIC CONTRIBUTIONS · REFRESHED HOURLY", font=SMALL, fill=(157, 145, 183, 255))
    draw.text((865, 207), updated, font=SMALL, fill=(157, 145, 183, 255), anchor="ra")
    draw.rounded_rectangle((8, 8, WIDTH - 9, HEIGHT - 9), radius=18, outline=(89, 67, 124, 235), width=1)
    return image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="space-shooter/space-shooter-heatmap.gif")
    parser.add_argument("--login", default=os.environ.get("GITHUB_LOGIN", "Preciouscrazy"))
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to fetch the live contribution calendar.")
    calendar, updated_at = fetch_calendar(args.login, token)
    grid = calendar_grid(calendar)
    updated = updated_at.strftime("%b %d · %H:%M UTC")
    frames = [render_frame(i, grid, calendar["totalContributions"], updated) for i in range(FRAME_COUNT)]
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {args.output} from {args.login}'s public contribution calendar ({calendar['totalContributions']} contributions).")


if __name__ == "__main__":
    main()
