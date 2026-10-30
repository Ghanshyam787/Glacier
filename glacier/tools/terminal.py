"""
Glacier Tools: Terminal & Python
DANGEROUS - isliye: (1) confirmation gate (code-enforced), (2) hamesha-blocked khatarnaak patterns,
(3) timeouts, (4) output limit, (5) UTF-8 output, koi console window nahi.
"""

import os
import subprocess
import tempfile

import config
import safety
from registry import tool
from winutil import CREATE_NO_WINDOW, python_console_exe, run_ps

MAX_TIMEOUT = 120


@tool(category="terminal", dangerous=True, label="PowerShell command")
def run_command(command: str, confirmed: bool = False, timeout_seconds: int = 30) -> str:
    """
    Run a Windows PowerShell command and return its output. DANGEROUS (can change/delete things).
    Needs confirmation: call with confirmed=False first (shows the command to the user), then call again with
    confirmed=True and the EXACT same command after the user says yes. Some destructive patterns
    (format, diskpart, registry/system-folder deletes, download-and-execute ...) are always blocked.
    """
    command = (command or "").strip()
    if not command:
        return "Command khaali hai."
    blocked = safety.check_command(command)
    if blocked:
        return blocked
    gate = safety.confirm_gate("run_command", {"command": command}, confirmed,
                               f"Ye PowerShell command chalau?\n{command}")
    if gate:
        return gate
    timeout = max(5, min(int(timeout_seconds or 30), MAX_TIMEOUT))
    try:
        rc, out, err = run_ps(command, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Command {timeout} second mein khatam nahi hua, rok diya."
    except OSError as e:
        return f"Command chalane mein error: {e}"
    text = (out + ("\n" + err if err else "")).strip()
    if not text:
        text = "(command chal gaya, koi output nahi)"
    return text + (f"\n[exit code {rc}]" if rc else "")


@tool(category="terminal", dangerous=True, label="Python code")
def run_python(code: str, confirmed: bool = False, timeout_seconds: int = 30) -> str:
    """
    Run a Python snippet (use print() for output) and return what it printed. DANGEROUS (full permissions).
    Needs confirmation: call with confirmed=False first, then confirmed=True with the EXACT same code after
    the user says yes.
    """
    code = code or ""
    if not code.strip():
        return "Code khaali hai."
    blocked = safety.check_python(code)
    if blocked:
        return blocked
    gate = safety.confirm_gate("run_python", {"code": code}, confirmed, f"Ye Python code chalau?\n{code[:1500]}")
    if gate:
        return gate
    timeout = max(5, min(int(timeout_seconds or 30), MAX_TIMEOUT))
    sandbox = os.path.join(config.DATA_DIR, "sandbox")
    os.makedirs(sandbox, exist_ok=True)
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=sandbox, delete=False, encoding="utf-8") as f:
            f.write(code)
            path = f.name
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        p = subprocess.run([python_console_exe(), path], capture_output=True, timeout=timeout, cwd=sandbox,
                           env=env, creationflags=CREATE_NO_WINDOW)
        text = (p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")).strip()
        return text or "(code chal gaya, koi output nahi)"
    except subprocess.TimeoutExpired:
        return f"Code {timeout} second mein khatam nahi hua, rok diya."
    except Exception as e:
        return f"Code chalane mein error: {e}"
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass
