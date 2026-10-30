"""
Glacier tools package.
Har module apne @tool functions registry mein register karta hai. Agar koi module import fail ho
(jaise optional library missing), baaki sab chalte rehte hain - LOAD_ERRORS mein reason milta hai
(python doctor.py ye dikhata hai).
"""

import importlib

MODULES = [
    "apps", "files", "terminal", "system", "web", "info", "reminders", "productivity", "comms",
    "vision", "control", "browser", "memory_tools", "research", "digest", "monitors", "code",
    "mcp_client", "skills_tools",
]

LOAD_ERRORS = {}

for _name in MODULES:
    try:
        importlib.import_module(f"tools.{_name}")
    except Exception as _e:  # pragma: no cover
        LOAD_ERRORS[_name] = f"{type(_e).__name__}: {_e}"

try:
    import skillsys
    skillsys.load_skills()
except Exception as _e:  # pragma: no cover
    LOAD_ERRORS["skills"] = f"{type(_e).__name__}: {_e}"
