"""
Glacier Tools: Git (developer helpers)
Read-only git (status/diff/log) free; commit confirmation ke saath. Code likhne/chalane ke liye write_file, edit_file,
run_python, run_command already hain.
"""

import os
import shutil
import subprocess

import safety
from registry import tool
from winutil import CREATE_NO_WINDOW


def _git(repo: str, *args, timeout=30):
    if not shutil.which("git"):
        return None, "Git install nahi hai (https://git-scm.com/download/win)."
    p = os.path.abspath(os.path.expanduser(repo.strip().strip('"')))
    if not safety.is_allowed_path(p) or not os.path.isdir(p):
        return None, safety.PATH_DENIED_MSG if os.path.exists(p) else f"Folder nahi mila: {p}"
    try:
        r = subprocess.run(["git", "-C", p, *args], capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        return None, "Git command time out."
    out = (r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")).strip()
    return (out or "(koi output nahi)"), None


@tool(category="terminal", label="Git status")
def git_status(repo: str) -> str:
    """Show git status (changed/untracked files and branch) of a repository folder."""
    out, err = _git(repo, "status", "-sb")
    return err or out


@tool(category="terminal", label="Git diff")
def git_diff(repo: str, staged: bool = False) -> str:
    """Show the uncommitted changes (diff) of a repository."""
    out, err = _git(repo, "diff", *(["--staged"] if staged else []), "--stat", "--patch", "--no-color")
    return err or out


@tool(category="terminal", label="Git log")
def git_log(repo: str, count: int = 8) -> str:
    """Show the latest commits of a repository."""
    out, err = _git(repo, "log", f"-{max(1, min(int(count or 8), 30))}", "--oneline", "--decorate", "--no-color")
    return err or out


@tool(category="terminal", dangerous=True, label="Git commit")
def git_commit(repo: str, message: str, confirmed: bool = False) -> str:
    """
    Stage all changes and commit them with the message. Needs confirmation: confirmed=False first, then
    confirmed=True (same arguments) after the user says yes. (Never pushes.)
    """
    status, err = _git(repo, "status", "--porcelain")
    if err:
        return err
    if status.startswith("(koi output"):
        return "Commit karne layak koi badlav nahi hai."
    gate = safety.confirm_gate("git_commit", {"repo": repo, "message": message}, confirmed,
                               f"Ye badlav commit karun?\n{status[:400]}\nMessage: {message}")
    if gate:
        return gate
    _, err = _git(repo, "add", "-A")
    if err:
        return err
    out, err = _git(repo, "commit", "-m", message)
    return err or out
