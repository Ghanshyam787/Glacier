"""
Glacier - Windows subprocess helpers
 - PowerShell hamesha UTF-8 output ke saath (Hindi app names / paths kharab nahi hote)
 - Koi console window flash nahi hoti (pythonw / background mein bhi)
 - Script -EncodedCommand se jaati hai, isliye quotes/special characters ka koi jhanjhat nahi
"""

import base64
import os
import re
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
DETACHED = (0x00000008 | 0x00000200) if os.name == "nt" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP

_PS_PREFIX = (
    "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
    "$OutputEncoding=[System.Text.Encoding]::UTF8; "
    "$ProgressPreference='SilentlyContinue'; "
)


def _clean_clixml(text: str) -> str:
    if not text.startswith("#< CLIXML"):
        return text
    msgs = re.findall(r'<S S="(?:Error|error)">(.*?)</S>', text, flags=re.S)
    if not msgs:
        return ""
    joined = "".join(msgs).replace("_x000D__x000A_", "\n").replace("_x000A_", "\n").replace("_x000D_", "")
    return re.sub(r"<[^>]+>", "", joined).strip()


def run_ps(script: str, timeout: int = 30):
    """PowerShell script chalao. Returns (returncode, stdout, stderr). Raises TimeoutExpired."""
    if os.name != "nt":
        raise OSError("PowerShell sirf Windows par available hai.")
    encoded = base64.b64encode((_PS_PREFIX + script).encode("utf-16-le")).decode("ascii")
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
           "-OutputFormat", "Text", "-EncodedCommand", encoded]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)
    out = p.stdout.decode("utf-8", "replace").strip()
    err = _clean_clixml(p.stderr.decode("utf-8", "replace").strip())
    return p.returncode, out, err


def ps_quote(s: str) -> str:
    """PowerShell single-quoted string literal."""
    return "'" + str(s).replace("'", "''") + "'"


def python_console_exe() -> str:
    """pythonw.exe nahi, python.exe - taaki child scripts ka stdout capture ho sake."""
    exe = sys.executable
    if os.name == "nt" and exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            return cand
    return exe


def python_windowless_exe() -> str:
    exe = sys.executable
    if os.name == "nt" and exe.lower().endswith("python.exe"):
        cand = exe[:-len("python.exe")] + "pythonw.exe"
        if os.path.exists(cand):
            return cand
    return exe
