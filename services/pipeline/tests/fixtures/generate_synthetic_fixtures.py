"""Generates the synthetic seed fixtures the round-trip harness runs against.

These are NOT the 30 real device screenshots the brief (section 8) calls
for — sourcing real iOS/Android/Windows/macOS/web screenshots requires
actual devices/apps, which isn't something a generator can substitute for.
This gives the harness something real to run against today, using the same
registry fonts the matcher searches, composed into UI-like layouts (label +
value, button-on-pill, multi-line paragraph) at 1x/2x/3x scale and PNG/JPEG,
so the pass/fail gate in test_round_trip.py is exercised for real rather
than skipped.

Run inside the pipeline container/image, where fonts/registry.py's paths
resolve (see docs/fonts.md) — e.g.:
    docker exec screenshottexteditor-pipeline-1 python tests/fixtures/generate_synthetic_fixtures.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

from fonts.registry import FONT_REGISTRY

FIXTURES_DIR = os.path.dirname(__file__)


def _font_path(family: str, weight: int) -> str:
    return next(c.file_path for c in FONT_REGISTRY if c.family == family and c.weight == weight)


def _draw_text(draw: ImageDraw.ImageDraw, xy, text, family, weight, size, fill):
    font = ImageFont.truetype(_font_path(family, weight), size)
    draw.text(xy, text, font=font, fill=fill)


def _save(image: Image.Image, name: str, jpeg: bool = False):
    path = os.path.join(FIXTURES_DIR, name)
    if jpeg:
        image.convert("RGB").save(path, format="JPEG", quality=90)
    else:
        image.save(path, format="PNG")
    print(f"wrote {path} ({image.size[0]}x{image.size[1]})")


def ios_1x_settings():
    image = Image.new("RGB", (390, 260), color=(242, 242, 247))
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (20, 24), "Account Settings", "Inter", 600, 20, (20, 20, 24))
    _draw_text(draw, (20, 60), "Manage your profile and preferences", "Inter", 400, 14, (110, 110, 118))
    draw.rounded_rectangle((20, 100, 370, 140), radius=10, fill=(255, 255, 255))
    _draw_text(draw, (36, 112), "Notifications", "Inter", 400, 15, (20, 20, 24))
    draw.rounded_rectangle((20, 150, 370, 190), radius=10, fill=(255, 255, 255))
    _draw_text(draw, (36, 162), "Privacy", "Inter", 400, 15, (20, 20, 24))
    draw.rounded_rectangle((130, 210, 260, 244), radius=17, fill=(0, 122, 255))
    _draw_text(draw, (155, 218), "Sign Out", "Inter", 600, 15, (255, 255, 255))
    _save(image, "ios_1x_settings.png")


def ios_3x_login():
    image = Image.new("RGB", (1170, 700), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (60, 90), "Welcome back", "Inter", 700, 66, (20, 20, 24))
    _draw_text(draw, (60, 180), "Sign in to continue", "Inter", 400, 36, (110, 110, 118))
    draw.rounded_rectangle((60, 280, 1110, 380), radius=24, fill=(242, 242, 247))
    _draw_text(draw, (96, 312), "Email address", "Inter", 400, 39, (60, 60, 67))
    draw.rounded_rectangle((60, 410, 1110, 510), radius=24, fill=(242, 242, 247))
    _draw_text(draw, (96, 442), "Password", "Inter", 400, 39, (60, 60, 67))
    draw.rounded_rectangle((60, 560, 1110, 650), radius=27, fill=(0, 122, 255))
    _draw_text(draw, (480, 585), "Log In", "Inter", 600, 42, (255, 255, 255))
    _save(image, "ios_3x_login.png")


def android_2x_profile():
    image = Image.new("RGB", (720, 480), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 720, 112), fill=(98, 0, 238))
    _draw_text(draw, (32, 36), "Your Profile", "Roboto", 500, 40, (255, 255, 255))
    _draw_text(draw, (32, 148), "Jordan Rivera", "Roboto", 700, 36, (20, 20, 20))
    _draw_text(draw, (32, 200), "jordan.rivera@example.com", "Roboto", 400, 28, (100, 100, 100))
    draw.rounded_rectangle((32, 260, 320, 330), radius=8, fill=(98, 0, 238))
    _draw_text(draw, (70, 280), "Edit Profile", "Roboto", 500, 28, (255, 255, 255))
    _save(image, "android_2x_profile.jpg", jpeg=True)


def windows_1x_dialog():
    image = Image.new("RGB", (420, 220), color=(243, 243, 243))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 420, 40), fill=(0, 120, 212))
    _draw_text(draw, (12, 10), "System Settings", "Noto Sans", 700, 16, (255, 255, 255))
    _draw_text(draw, (20, 60), "Choose how updates are installed", "Noto Sans", 400, 15, (30, 30, 30))
    draw.rectangle((20, 100, 400, 130), outline=(180, 180, 180), width=1)
    _draw_text(draw, (30, 106), "Automatic (recommended)", "Noto Sans", 400, 14, (30, 30, 30))
    draw.rectangle((280, 170, 400, 200), fill=(0, 120, 212))
    _draw_text(draw, (315, 176), "Apply", "Noto Sans", 700, 14, (255, 255, 255))
    _save(image, "windows_1x_dialog.png")


def web_1x_pricing():
    image = Image.new("RGB", (360, 280), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 16, 344, 264), radius=12, outline=(229, 229, 229), width=1)
    _draw_text(draw, (36, 40), "Pro Plan", "Inter", 700, 22, (17, 17, 17))
    _draw_text(draw, (36, 76), "$29 / month", "Inter", 500, 18, (60, 60, 60))
    _draw_text(draw, (36, 116), "Unlimited screenshots", "Inter", 400, 14, (100, 100, 100))
    _draw_text(draw, (36, 142), "Priority support", "Inter", 400, 14, (100, 100, 100))
    draw.rounded_rectangle((36, 200, 324, 240), radius=8, fill=(24, 24, 27))
    _draw_text(draw, (150, 212), "Subscribe", "Inter", 600, 15, (255, 255, 255))
    _save(image, "web_1x_pricing.jpg", jpeg=True)


def macos_2x_menu():
    image = Image.new("RGB", (600, 360), color=(255, 255, 255))
    for y in range(360):
        t = y / 360
        r = int(246 + (230 - 246) * t)
        g = int(246 + (230 - 246) * t)
        b = int(248 + (235 - 248) * t)
        ImageDraw.Draw(image).line((0, y, 600, y), fill=(r, g, b))
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (40, 30), "General", "Inter", 600, 30, (20, 20, 22))
    _draw_text(draw, (40, 90), "Appearance", "Inter", 400, 22, (40, 40, 44))
    _draw_text(draw, (40, 140), "Accent color", "Inter", 400, 22, (40, 40, 44))
    _draw_text(draw, (40, 190), "Sidebar icon size", "Inter", 400, 22, (40, 40, 44))
    _save(image, "macos_2x_menu.png")


def android_1x_button():
    image = Image.new("RGB", (300, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 30, 240, 74), radius=22, fill=(3, 218, 197))
    _draw_text(draw, (108, 42), "Continue", "Roboto", 500, 17, (0, 0, 0))
    _save(image, "android_1x_button.png")


def web_3x_dashboard():
    image = Image.new("RGB", (900, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (40, 30), "Revenue", "Inter", 500, 24, (100, 100, 110))
    _draw_text(draw, (40, 64), "$482,910", "Inter", 700, 48, (17, 17, 17))
    _draw_text(draw, (40, 130), "Active Users", "Inter", 500, 24, (100, 100, 110))
    _draw_text(draw, (40, 164), "12,384", "Inter", 700, 48, (17, 17, 17))
    _draw_text(draw, (40, 230), "Churn Rate", "Inter", 500, 24, (100, 100, 110))
    _draw_text(draw, (40, 264), "2.1%", "Inter", 700, 48, (17, 17, 17))
    _save(image, "web_3x_dashboard.jpg", jpeg=True)


if __name__ == "__main__":
    ios_1x_settings()
    ios_3x_login()
    android_2x_profile()
    windows_1x_dialog()
    web_1x_pricing()
    macos_2x_menu()
    android_1x_button()
    web_3x_dashboard()
