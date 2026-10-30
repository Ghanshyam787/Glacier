"""
Glacier - image helpers (screenshots -> Gemini parts)
"""

import io
import os
import time

import config
import winpaths

try:
    from google.genai import types
except ImportError:
    types = None


def screenshot_dir() -> str:
    d = os.path.join(winpaths.get_pictures(), "Glacier Screenshots")
    os.makedirs(d, exist_ok=True)
    return d


def grab_screen():
    """PIL Image of the full virtual screen. Raises RuntimeError with a clear message."""
    try:
        from PIL import ImageGrab
    except ImportError:
        raise RuntimeError("Pillow install nahi hai (pip install pillow).")
    try:
        img = ImageGrab.grab(all_screens=True)
    except TypeError:
        img = ImageGrab.grab()
    except Exception as e:
        raise RuntimeError(f"Screenshot nahi le paya: {e}")
    return img.convert("RGB")


def save_screenshot(img=None) -> str:
    img = img or grab_screen()
    path = os.path.join(screenshot_dir(), time.strftime("screen_%Y%m%d_%H%M%S.png"))
    img.save(path)
    return path


def to_part(img, max_dim: int = 1568, quality: int = 85):
    """PIL image -> Gemini Part (JPEG, resized)."""
    if types is None:
        raise RuntimeError("google-genai install nahi hai.")
    im = img.convert("RGB")
    im.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def file_to_part(path: str, max_dim: int = 1568):
    from PIL import Image
    with Image.open(path) as im:
        return to_part(im, max_dim=max_dim)
