"""
Glacier - Windows Known Folder Resolver
Desktop/Downloads/Documents/Pictures ka SAHI (actual) path nikalta hai - chahe OneDrive ne
unhe redirect kiya ho ya nahi. Non-Windows pe (testing) simple home-folder fallback.
"""

import os

try:
    import winreg  # type: ignore
except ImportError:  # not Windows
    winreg = None

_SHELL_FOLDERS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"


def _get_shell_folder(value_name: str, fallback: str) -> str:
    if winreg is None:
        return fallback
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS_KEY) as key:
            raw_value, _ = winreg.QueryValueEx(key, value_name)
            path = os.path.expandvars(raw_value)
            return path if path else fallback
    except Exception:
        return fallback


def get_desktop() -> str:
    return _get_shell_folder("Desktop", os.path.expanduser("~/Desktop"))


def get_downloads() -> str:
    # Downloads ka registry value ek GUID hota hai.
    return _get_shell_folder("{374DE290-123F-4565-9164-39C4925E467B}", os.path.expanduser("~/Downloads"))


def get_documents() -> str:
    return _get_shell_folder("Personal", os.path.expanduser("~/Documents"))


def get_pictures() -> str:
    return _get_shell_folder("My Pictures", os.path.expanduser("~/Pictures"))


def get_videos() -> str:
    return _get_shell_folder("My Video", os.path.expanduser("~/Videos"))


def get_music() -> str:
    return _get_shell_folder("My Music", os.path.expanduser("~/Music"))


def known_folders() -> dict:
    return {
        "desktop": get_desktop(),
        "downloads": get_downloads(),
        "documents": get_documents(),
        "pictures": get_pictures(),
        "videos": get_videos(),
        "music": get_music(),
        "home": os.path.expanduser("~"),
    }


def resolve_folder_alias(text: str) -> str:
    """'desktop' / 'downloads' jaisa naam ho to uska asli path, warna text wapas."""
    if not text:
        return text
    key = text.strip().lower().rstrip("\\/")
    return known_folders().get(key, text)
