"""
Glacier Tools: Skills & capabilities
Naye skills (instructions) internet se install karo, capabilities dekho.
"""

import os
import re

import config
import netsafe
import registry
import safety
import skillsys
from registry import tool


@tool(category="skill", quiet=True, label="What can Glacier do")
def list_capabilities() -> str:
    """List everything Glacier can do (tool categories and names). Use when the user asks 'tum kya kar sakte ho?'."""
    cats = registry.tools_by_category()
    total = sum(len(v) for v in cats.values())
    lines = [f"{total} tools hain:"]
    for c, names in sorted(cats.items()):
        lines.append(f"- {c}: {', '.join(sorted(names))}")
    return "\n".join(lines)


@tool(category="skill", label="List skills")
def list_skills() -> str:
    """List installed skills (skills/ folder: python plugins and instruction files)."""
    if not os.path.isdir(config.SKILLS_DIR):
        return "Koi skill installed nahi hai."
    items = [e for e in sorted(os.listdir(config.SKILLS_DIR)) if not e.startswith(("_", ".")) and e.lower() != "readme.md"]
    msg = "Installed skills: " + ", ".join(items) if items else "Koi skill installed nahi hai."
    if skillsys.LOAD_ERRORS:
        msg += "\nLoad errors: " + "; ".join(f"{k}: {v}" for k, v in skillsys.LOAD_ERRORS.items())
    return msg


@tool(category="skill", dangerous=True, label="Install skill")
def install_skill_from_url(url: str, name: str = "", confirmed: bool = False) -> str:
    """
    Install an instructions-only skill (a SKILL.md / .md file, agentskills.io style) from a URL (e.g. a raw GitHub
    link). Python skills are NOT installed from the internet (safety) - those must be copied manually. Needs
    confirmation: confirmed=False first, then confirmed=True (same arguments).
    """
    if not url.lower().split("?")[0].endswith(".md"):
        return "Sirf .md (instructions) skill URL se install hoti hai. Raw GitHub link do."
    text, err = netsafe.fetch_text(url, max_chars=20000, timeout=15)
    if err:
        return err
    flags = safety.scan_injection(text)
    fname = re.sub(r"[^\w\-]", "_", (name or os.path.basename(url.split("?")[0])[:-3] or "skill"))[:50] + ".md"
    warn = f"\nWARNING: isme suspicious phrases mile: {', '.join(flags)}" if flags else ""
    gate = safety.confirm_gate("install_skill_from_url", {"url": url, "name": fname}, confirmed,
                               f"Ye skill '{fname}' install karun? ({len(text)} chars){warn}\nShuruaat:\n{text[:400]}")
    if gate:
        return gate
    os.makedirs(config.SKILLS_DIR, exist_ok=True)
    with open(os.path.join(config.SKILLS_DIR, fname), "w", encoding="utf-8") as f:
        f.write(text)
    skillsys.load_skills()
    return f"Skill install ho gayi: {fname}. Agli nayi chat se Glacier use karega (reset_session ya restart)."
