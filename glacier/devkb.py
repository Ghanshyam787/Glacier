"""
Glacier - Developer knowledge base
==================================
devkb/ref/*.md        : C, C++, HTML, CSS, JavaScript reference notes (searched by section)
devkb/examples/<lang> : tested, complete example programs (header comment has NAME / DESC / KEYWORDS)

Sab kuchh offline hai. Brain ke tools (dev_reference, list_examples, use_example) isi module ko use karte hain.
"""

import os
import re
import shutil

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devkb")
REF_DIR = os.path.join(BASE, "ref")
EX_DIR = os.path.join(BASE, "examples")

LANG_DIRS = {"c": "c", "cpp": "cpp", "html": "html"}
LANG_REFS = {
    "c": ("c_core", "c_pitfalls"),
    "cpp": ("cpp_core", "cpp_stl", "cpp_idioms_errors"),
    "html": ("html_core", "css_core", "js_dom", "web_projects"),
}
_EXT = {"c": ".c", "cpp": ".cpp", "html": ".html"}
_STOP = {"the", "a", "an", "of", "in", "to", "for", "and", "or", "is", "how", "do", "i", "me", "kaise", "kya", "hai", "ka", "ki", "ke",
         "mein", "se", "ko", "banao", "bana", "de", "do", "with", "using", "use", "program", "code", "project", "example"}

_cache = {}


def norm_lang(language: str) -> str:
    k = (language or "").strip().lower().replace("c++", "cpp").replace("c#", "csharp").replace("c+", "csharp")
    if k in ("js", "javascript", "css", "web", "website", "html5"):
        return "html"
    return k if k in LANG_DIRS else ""


def _words(text: str) -> list:
    return [w for w in re.findall(r"[a-z0-9_+#]+", (text or "").lower()) if w not in _STOP and len(w) > 1]


# ------------------------------------------------------------------ reference docs
def _sections() -> list:
    """[(doc, title, body, lang_set)] - har '## ' heading ek section."""
    if "sections" in _cache:
        return _cache["sections"]
    out = []
    if os.path.isdir(REF_DIR):
        for fn in sorted(os.listdir(REF_DIR)):
            if not fn.endswith(".md"):
                continue
            doc = fn[:-3]
            try:
                with open(os.path.join(REF_DIR, fn), encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            langs = {l for l, docs in LANG_REFS.items() if doc in docs}
            parts = re.split(r"(?m)^## ", text)
            head = parts[0].strip()
            for p in parts[1:]:
                title, _, body = p.partition("\n")
                out.append((doc, title.strip(), body.strip(), langs, head.splitlines()[0] if head else doc))
    _cache["sections"] = out
    return out


def search_ref(query: str, language: str = "", limit: int = 3, max_chars: int = 3500) -> str:
    qw = _words(query)
    lang = norm_lang(language)
    if not qw:
        return ""
    scored = []
    for doc, title, body, langs, _h in _sections():
        if lang and langs and lang not in langs:
            continue
        tl, bl = title.lower(), body.lower()
        score = 0.0
        for w in qw:
            if w in tl:
                score += 5
            n = bl.count(w)
            if n:
                score += min(n, 6) * 1.0
        if score:
            scored.append((score, doc, title, body))
    scored.sort(key=lambda x: -x[0])
    out, used = [], 0
    for score, doc, title, body in scored[:max(1, limit)]:
        chunk = f"### [{doc}] {title}\n{body}"
        room = max_chars - used
        if room < 400:
            break
        chunk = chunk[:room]
        out.append(chunk)
        used += len(chunk)
    return "\n\n".join(out)


# ------------------------------------------------------------------ examples
_META = {
    "name": re.compile(r"NAME:\s*(.+)"),
    "desc": re.compile(r"DESC:\s*(.+)"),
    "keywords": re.compile(r"KEYWORDS:\s*(.+?)(?:\s*\*/|\s*-->|$)", re.M),
}


def _parse_example(path: str, lang: str):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(1500)
    except OSError:
        return None
    meta = {k: (rx.search(head).group(1).strip() if rx.search(head) else "") for k, rx in _META.items()}
    for k in ("desc", "keywords"):
        meta[k] = re.sub(r"\s*(\*/|-->)\s*$", "", meta[k]).strip()
    if not meta["name"]:
        meta["name"] = os.path.splitext(os.path.basename(path))[0]
    meta.update(lang=lang, path=path, file=os.path.basename(path))
    return meta


def examples(language: str = "") -> list:
    if "examples" not in _cache:
        allx = []
        for lang, d in LANG_DIRS.items():
            folder = os.path.join(EX_DIR, d)
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                if fn.endswith(_EXT[lang]):
                    m = _parse_example(os.path.join(folder, fn), lang)
                    if m:
                        allx.append(m)
        _cache["examples"] = allx
    lang = norm_lang(language)
    return [e for e in _cache["examples"] if not lang or e["lang"] == lang]


def find_examples(query: str, language: str = "", limit: int = 4) -> list:
    qw = _words(query)
    scored = []
    for e in examples(language):
        hay = f"{e['name']} {e['desc']} {e['keywords']}".lower()
        s = sum((4 if w in e["name"].lower() else 0) + (2 if w in e["keywords"].lower() else 0) + (1 if w in hay else 0) for w in qw)
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _s, e in scored[:limit]]


def get_example(name: str, language: str = ""):
    n = (name or "").strip().lower().replace(".c", "").replace(".cpp", "").replace(".html", "")
    lang = norm_lang(language)
    for e in examples(lang):
        if e["name"].lower() == n or e["file"].lower().rsplit(".", 1)[0] == n:
            return e
    return None


def example_source(e: dict) -> str:
    with open(e["path"], encoding="utf-8") as f:
        return f.read()


def copy_example(e: dict, dest_folder: str) -> list:
    """Example ko dest_folder mein copy karo. HTML ke liye index.html naam; C/C++ ke liye original naam."""
    os.makedirs(dest_folder, exist_ok=True)
    target = os.path.join(dest_folder, "index.html" if e["lang"] == "html" else e["file"])
    shutil.copyfile(e["path"], target)
    return [target]


def build_hint(e: dict) -> str:
    n = e["file"].rsplit(".", 1)[0]
    if e["lang"] == "c":
        return f"Compile: compile_code(path) ya `gcc -std=c11 -Wall -Wextra {e['file']} -o {n} -lm`"
    if e["lang"] == "cpp":
        extra = " -pthread" if "thread" in e["keywords"].lower() else ""
        return f"Compile: compile_code(path) ya `g++ -std=c++17 -Wall -Wextra {e['file']} -o {n}{extra}`"
    return "Browser mein index.html double-click karke kholo (ya preview_html)."


def stats() -> dict:
    ex = examples()
    return {
        "examples": len(ex),
        "c": sum(1 for e in ex if e["lang"] == "c"),
        "cpp": sum(1 for e in ex if e["lang"] == "cpp"),
        "html": sum(1 for e in ex if e["lang"] == "html"),
        "ref_sections": len(_sections()),
    }
