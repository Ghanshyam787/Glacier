"""
Glacier - Skills (plugins)
==========================
skills/ folder mein file daalo, Glacier use khud seekh leta hai:
  * skills/mera_kaam.py  -> usme @tool wale functions (registry.tool) automatically tools ban jaate hain
  * skills/mera_style.md -> plain instructions (agentskills.io jaisa SKILL.md; frontmatter optional)
                            jo system prompt mein jud jaati hain

Python skills poora code chalate hain - sirf wahi file daalo jis par bharosa ho.
"""

import importlib.util
import os
import re

import config

LOAD_ERRORS = {}
_md_cache = []


def load_skills():
    """Python skills import karo (har ek apne try/except mein) aur md instructions padho."""
    global _md_cache
    LOAD_ERRORS.clear()
    _md_cache = []
    folder = config.SKILLS_DIR
    if not os.path.isdir(folder):
        return
    for entry in sorted(os.listdir(folder)):
        path = os.path.join(folder, entry)
        if entry.startswith(("_", ".")):
            continue
        try:
            if entry.endswith(".py") and os.path.isfile(path):
                spec = importlib.util.spec_from_file_location(f"glacier_skill_{entry[:-3]}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            elif entry.endswith(".md") and os.path.isfile(path) and entry.lower() != "readme.md":
                with open(path, encoding="utf-8") as f:
                    raw = f.read()
                name = entry[:-3]
                body = raw
                m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
                if m:
                    nm = re.search(r"^name:\s*(.+)$", m.group(1), re.M)
                    name = nm.group(1).strip() if nm else name
                    body = m.group(2)
                _md_cache.append((name, body.strip()[:3000]))
            elif os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md")):
                with open(os.path.join(path, "SKILL.md"), encoding="utf-8") as f:
                    raw = f.read()
                m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
                body = m.group(2) if m else raw
                _md_cache.append((entry, body.strip()[:3000]))
        except Exception as e:
            LOAD_ERRORS[entry] = f"{type(e).__name__}: {e}"


def instructions() -> str:
    return "\n\n".join(f"[{n}]\n{b}" for n, b in _md_cache)
