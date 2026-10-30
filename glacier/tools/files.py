"""
Glacier Tools: Files
Poore C:/D: par kaam, SIVAY system folders (Windows, Program Files, ProgramData, AppData ...) aur secrets
(.env, .ssh, browser profiles) - wo kabhi touch nahi hote, confirmation ke saath bhi nahi.

Naya vs. purana:
  * instant search (SQLite index) + naye files ke liye live scan; folders bhi milte hain
  * path check ab sahi hai (pehle 'C:\\Windows' prefix 'C:\\WindowsOld' ko bhi block kar deta tha)
  * delete = Recycle Bin (wapas aa sakta hai); organize_downloads confirmation + undo ke saath
  * Desktop/Documents/Downloads jaise top-level folders move/delete nahi ho sakte
"""

import json
import os
import shutil
import time
import zipfile
from datetime import datetime

import config
import docreader
import fileindex
import safety
import winpaths
from registry import tool

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

EXEC_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".msi", ".scr", ".com",
             ".jar", ".lnk", ".reg", ".hta", ".dll"}
UNDO_FILE = os.path.join(config.DATA_DIR, "undo_organize.json")


def _clean(path: str) -> str:
    p = (path or "").strip().strip('"').strip("'")
    p = winpaths.resolve_folder_alias(p)
    return os.path.abspath(os.path.expanduser(p)) if p else p


def _protected_roots() -> set:
    roots = {os.path.normcase(os.path.abspath(d)) for d in config.SEARCH_DRIVES}
    for v in winpaths.known_folders().values():
        roots.add(os.path.normcase(os.path.abspath(v)))
    roots.add(os.path.normcase(os.path.abspath(os.path.expanduser("~"))))
    roots.add(os.path.normcase(os.path.abspath(os.path.join(os.path.expanduser("~"), ".."))))
    return roots


def _is_top_level(path: str) -> bool:
    return os.path.normcase(os.path.abspath(path)) in _protected_roots()


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _line(path: str, is_dir: bool, size: int, mtime: float) -> str:
    when = datetime.fromtimestamp(mtime).strftime("%d %b %Y") if mtime else "?"
    kind = "[folder]" if is_dir else f"[{_fmt_size(size)}]"
    return f"{path}  {kind}  {when}"


# ---------------------------------------------------------------------------
# Search / browse
# ---------------------------------------------------------------------------
@tool(category="files", label="Find files")
def find_files(keyword: str, folder: str = "", kind: str = "any", ext: str = "") -> str:
    """
    Find files/folders by (part of) name anywhere on C: and D: (instant, uses an index; also catches
    brand-new files). keyword can have several words (all must match). kind = any | file | folder.
    ext narrows by extension e.g. 'pdf'. folder narrows to one folder (name like 'downloads' works).
    """
    kw = (keyword or "").strip()
    if not kw and not ext:
        return "Kya dhundhna hai? Naam ka koi hissa batao."
    tokens = [t for t in kw.replace("_", " ").split() if t]
    root = _clean(folder) if folder else ""
    if root and not safety.is_allowed_path(root):
        return safety.PATH_DENIED_MSG
    kind = kind if kind in ("any", "file", "folder") else "any"

    results = {}
    t0 = time.time()

    # 1) index
    for r in fileindex.search(tokens, kind=kind, ext=ext, limit=120, root=root):
        if os.path.exists(r["path"]):
            results[r["path"]] = (bool(r["is_dir"]), r["size"], r["mtime"])

    # 2) live scan of the user's own folders (new files not yet in index) or everything if no index yet
    live_roots = [root] if root else ([winpaths.get_desktop(), winpaths.get_downloads(), winpaths.get_documents(),
                                       winpaths.get_pictures()] if fileindex.is_ready() else list(config.SEARCH_DRIVES))
    budget = 4 if fileindex.is_ready() else 25
    scanned = 0
    for base in live_roots:
        if not os.path.isdir(base) or time.time() - t0 > budget or len(results) >= 60:
            continue
        for cur, dirs, files in os.walk(base, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in fileindex.SKIP_DIR_NAMES
                       and not safety.is_blocked_path(os.path.join(cur, d))]
            entries = []
            if kind in ("any", "folder"):
                entries += [(d, True) for d in dirs]
            if kind in ("any", "file"):
                entries += [(f, False) for f in files]
            for name, is_dir in entries:
                scanned += 1
                low = name.lower()
                if all(t.lower() in low for t in tokens) and (not ext or low.endswith("." + ext.lower().lstrip("."))):
                    full = os.path.join(cur, name)
                    if full not in results:
                        try:
                            st = os.stat(full)
                            results[full] = (is_dir, 0 if is_dir else st.st_size, st.st_mtime)
                        except OSError:
                            pass
            if scanned > 200_000 or time.time() - t0 > budget or len(results) >= 60:
                break

    results = {p: v for p, v in results.items() if safety.is_allowed_path(p)}
    if not results:
        note = "" if fileindex.is_ready() else " (index abhi ban raha hai, thodi der baad dobara try karo)"
        return f"'{kw}' naam ki koi file/folder nahi mili.{note}"
    ordered = sorted(results.items(), key=lambda kv: -kv[1][2])[:25]
    return f"{len(results)} match mile (naye pehle):\n" + "\n".join(_line(p, *v) for p, v in ordered)


@tool(category="files", label="List folder")
def list_folder(path: str, limit: int = 60) -> str:
    """List the contents of a folder (use 'desktop', 'downloads', 'documents' as shortcuts)."""
    p = _clean(path)
    if not safety.is_allowed_path(p) and not _is_top_level(p):
        return safety.PATH_DENIED_MSG
    if not os.path.isdir(p):
        return f"Folder nahi mila: {p}"
    rows = []
    try:
        with os.scandir(p) as it:
            for e in it:
                try:
                    st = e.stat()
                    rows.append((e.is_dir(), e.name, st.st_size, st.st_mtime))
                except OSError:
                    continue
    except PermissionError:
        return "Is folder ko kholne ki permission nahi hai."
    rows.sort(key=lambda r: (not r[0], r[1].lower()))
    lines = [_line(os.path.join(p, n), d, s, m) for d, n, s, m in rows[:limit]]
    extra = f"\n…aur {len(rows) - limit} items" if len(rows) > limit else ""
    return f"{p} ({len(rows)} items):\n" + "\n".join(lines) + extra if rows else f"{p} khaali hai."


@tool(category="files", label="File info")
def file_info(path: str) -> str:
    """Size, dates and type of a file or folder."""
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(p):
        return f"Nahi mila: {p}"
    st = os.stat(p)
    if os.path.isdir(p):
        total = count = 0
        for cur, _d, files in os.walk(p):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(cur, f))
                    count += 1
                except OSError:
                    pass
            if count > 50000:
                break
        return f"Folder: {p}\nFiles: {count}{'+' if count > 50000 else ''}, size: {_fmt_size(total)}\n" \
               f"Modified: {datetime.fromtimestamp(st.st_mtime):%d %b %Y %H:%M}"
    return (f"File: {p}\nSize: {_fmt_size(st.st_size)}\nType: {os.path.splitext(p)[1] or '-'}\n"
            f"Modified: {datetime.fromtimestamp(st.st_mtime):%d %b %Y %H:%M}\n"
            f"Created: {datetime.fromtimestamp(st.st_ctime):%d %b %Y %H:%M}")


@tool(category="files", untrusted="file content", label="Read file")
def read_file(path: str, max_chars: int = 6000) -> str:
    """Read a file's text (txt, md, code, csv, json, PDF, Word .docx, Excel .xlsx ...)."""
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    text, err = docreader.read_text(p, max_chars=max(500, min(int(max_chars or 6000), 20000)))
    return err if err else text


@tool(category="files", label="Open in Windows")
def open_path(path: str) -> str:
    """Open a file with its default app, or open a folder in File Explorer. Programs/scripts are refused."""
    p = _clean(path)
    if not (safety.is_allowed_path(p) or _is_top_level(p)):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(p):
        return f"Nahi mila: {p}"
    if os.path.splitext(p)[1].lower() in EXEC_EXTS:
        return "Programs/scripts open_path se nahi chalte (safety). Inke liye open_application ya run_command use karo."
    try:
        os.startfile(p)  # type: ignore[attr-defined]
        return f"Khol diya: {p}"
    except Exception as e:
        return f"Khol nahi paya: {e}"


# ---------------------------------------------------------------------------
# Create / write
# ---------------------------------------------------------------------------
@tool(category="files", label="Create folder")
def create_folder(path: str) -> str:
    """Create a new folder (parents too)."""
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    os.makedirs(p, exist_ok=True)
    return f"Folder ban gaya: {p}"


@tool(category="files", dangerous=True, label="Write file")
def write_file(path: str, content: str, confirmed: bool = False) -> str:
    """
    Create a text file with the given content. If the file already exists it will be OVERWRITTEN, which needs
    confirmation: call with confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    New files need no confirmation.
    """
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    if os.path.splitext(p)[1].lower() in EXEC_EXTS:
        return "Executable/script files write_file se nahi banti (safety). Code chahiye to .py/.txt mein save karo."
    if os.path.exists(p):
        gate = safety.confirm_gate("write_file", {"path": p, "content": content}, confirmed,
                                   f"'{p}' pehle se hai - overwrite kar dun? ({len(content)} chars likhunga)")
        if gate:
            return gate
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return f"File likh di: {p} ({len(content)} chars)"


@tool(category="files", dangerous=True, label="Edit file")
def edit_file(path: str, old_text: str, new_text: str, confirmed: bool = False) -> str:
    """
    Replace exact text inside an existing text file (old_text must appear exactly once). Needs confirmation:
    call with confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    """
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    if not os.path.isfile(p):
        return f"File nahi mili: {p}"
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    n = data.count(old_text)
    if n != 1:
        return f"old_text file mein {n} baar mila (ek hi baar hona chahiye). Aur context ke saath dobara try karo."
    gate = safety.confirm_gate("edit_file", {"path": p, "old": old_text, "new": new_text}, confirmed,
                               f"'{p}' mein ye badlav karun?\n--- purana:\n{old_text[:300]}\n+++ naya:\n{new_text[:300]}")
    if gate:
        return gate
    shutil.copy2(p, p + ".glacier.bak")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(data.replace(old_text, new_text, 1))
    return f"Edit ho gaya: {p} (purani copy: {p}.glacier.bak)"


# ---------------------------------------------------------------------------
# Move / copy / rename / delete
# ---------------------------------------------------------------------------
def _dest_for(source: str, destination: str) -> str:
    return os.path.join(destination, os.path.basename(source.rstrip("\\/"))) if os.path.isdir(destination) else destination


@tool(category="files", dangerous=True, label="Move file")
def move_file(source: str, destination: str, confirmed: bool = False) -> str:
    """
    Move (cut-paste) a file or folder. If destination is an existing folder the item goes inside it.
    Needs confirmation: call with confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    """
    src, dst = _clean(source), _clean(destination)
    if not (safety.is_allowed_path(src) and safety.is_allowed_path(dst)):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(src):
        return f"Source nahi mila: {src}"
    if _is_top_level(src):
        return "Ye top-level folder hai (Desktop/Documents/Drive jaisa), ise move nahi karunga."
    final = _dest_for(src, dst)
    if os.path.exists(final):
        return f"Destination par already kuchh hai: {final}. Naya naam ya doosra folder batao."
    gate = safety.confirm_gate("move_file", {"source": src, "destination": dst}, confirmed,
                               f"'{src}' ko '{final}' par move karu?")
    if gate:
        return gate
    os.makedirs(os.path.dirname(final) or ".", exist_ok=True)
    shutil.move(src, final)
    return f"Move ho gaya: {src} -> {final}"


@tool(category="files", dangerous=True, label="Copy file")
def copy_file(source: str, destination: str, confirmed: bool = False) -> str:
    """
    Copy a file or folder (original stays). Needs confirmation: confirmed=False first, then confirmed=True
    (same arguments) after the user says yes.
    """
    src, dst = _clean(source), _clean(destination)
    if not (safety.is_allowed_path(src) and safety.is_allowed_path(dst)):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(src):
        return f"Source nahi mila: {src}"
    final = _dest_for(src, dst)
    if os.path.exists(final):
        return f"Destination par already kuchh hai: {final}."
    gate = safety.confirm_gate("copy_file", {"source": src, "destination": dst}, confirmed,
                               f"'{src}' ki copy '{final}' par banau?")
    if gate:
        return gate
    os.makedirs(os.path.dirname(final) or ".", exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, final)
    else:
        shutil.copy2(src, final)
    return f"Copy ho gaya: {src} -> {final}"


@tool(category="files", dangerous=True, label="Rename")
def rename_file(path: str, new_name: str, confirmed: bool = False) -> str:
    """
    Rename a file/folder (new_name is just the new name, not a path). Needs confirmation: confirmed=False
    first, then confirmed=True (same arguments) after the user says yes.
    """
    src = _clean(path)
    if not safety.is_allowed_path(src):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(src):
        return f"Nahi mila: {src}"
    if _is_top_level(src):
        return "Top-level folder rename nahi karunga."
    if os.sep in new_name or "/" in new_name or any(c in new_name for c in '<>:"|?*'):
        return "Naya naam sirf naam hona chahiye (path ya special characters nahi)."
    final = os.path.join(os.path.dirname(src), new_name)
    if os.path.exists(final):
        return f"'{new_name}' naam se already kuchh hai."
    gate = safety.confirm_gate("rename_file", {"path": src, "new_name": new_name}, confirmed,
                               f"'{os.path.basename(src)}' ka naam badal ke '{new_name}' kar dun?")
    if gate:
        return gate
    os.rename(src, final)
    return f"Rename ho gaya: {final}"


@tool(category="files", dangerous=True, label="Delete")
def delete_file(path: str, confirmed: bool = False) -> str:
    """
    Delete a file or folder. By default goes to the Recycle Bin (recoverable). Needs confirmation:
    confirmed=False first, then confirmed=True (same path) after the user says yes to THIS item.
    """
    p = _clean(path)
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(p):
        return f"Nahi mila: {p}"
    if _is_top_level(p):
        return "Ye top-level folder hai (Desktop/Documents/Drive jaisa), ise delete nahi karunga."
    what = "folder (andar ki sab files ke saath)" if os.path.isdir(p) else "file"
    where = "Recycle Bin mein bhejunga (wapas aa sakti hai)" if (config.USE_RECYCLE_BIN and send2trash) else "PERMANENT delete hoga"
    gate = safety.confirm_gate("delete_file", {"path": p}, confirmed, f"Pakka ye {what} delete karun?\n{p}\n({where})")
    if gate:
        return gate
    if config.USE_RECYCLE_BIN and send2trash:
        send2trash(os.path.abspath(p))
        return f"Recycle Bin mein bhej diya: {p}"
    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    return f"Delete ho gaya (permanent): {p}"


# ---------------------------------------------------------------------------
# Zip
# ---------------------------------------------------------------------------
def _unique(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base} ({i}){ext}"):
        i += 1
    return f"{base} ({i}){ext}"


@tool(category="files", label="Zip")
def zip_folder(folder_path: str, output_path: str = "") -> str:
    """Compress a folder (or single file) into a .zip next to it (or at output_path). Original is untouched."""
    src = _clean(folder_path)
    if not safety.is_allowed_path(src):
        return safety.PATH_DENIED_MSG
    if not os.path.exists(src):
        return f"Nahi mila: {src}"
    out = _clean(output_path) if output_path else src.rstrip("\\/") + ".zip"
    if not out.lower().endswith(".zip"):
        out += ".zip"
    if not safety.is_allowed_path(out):
        return safety.PATH_DENIED_MSG
    out = _unique(out)
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.isfile(src):
            z.write(src, os.path.basename(src))
            count = 1
        else:
            for cur, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if not safety.is_blocked_path(os.path.join(cur, d))]
                for f in files:
                    full = os.path.join(cur, f)
                    if os.path.abspath(full) == os.path.abspath(out) or safety.is_secret_path(full):
                        continue
                    try:
                        z.write(full, os.path.relpath(full, os.path.dirname(src)))
                        count += 1
                    except OSError:
                        continue
    return f"Zip ban gaya ({count} files, {_fmt_size(os.path.getsize(out))}): {out}"


@tool(category="files", label="Unzip")
def unzip_file(zip_path: str, destination: str = "") -> str:
    """Extract a .zip into a new folder next to it (or into destination). Never overwrites existing files."""
    src = _clean(zip_path)
    if not safety.is_allowed_path(src) or not os.path.isfile(src):
        return safety.PATH_DENIED_MSG if os.path.exists(src) else f"Zip nahi mili: {src}"
    dest = _clean(destination) if destination else os.path.splitext(src)[0]
    if not safety.is_allowed_path(dest):
        return safety.PATH_DENIED_MSG
    dest = _unique(dest) if os.path.exists(dest) and not destination else dest
    try:
        with zipfile.ZipFile(src) as z:
            total = sum(i.file_size for i in z.infolist())
            if total > 3 * 1024 ** 3:
                return "Zip ka unzipped size 3GB se zyada hai - zip-bomb ho sakta hai, nahi khola."
            root = os.path.realpath(dest)
            for info in z.infolist():
                target = os.path.realpath(os.path.join(dest, info.filename))
                if not (target == root or target.startswith(root + os.sep)):
                    return "Zip ke andar unsafe paths hain (path traversal) - nahi khola."
                if safety.is_blocked_path(target):
                    return "Zip protected folder mein likhna chahta hai - nahi khola."
            os.makedirs(dest, exist_ok=True)
            for info in z.infolist():
                target = os.path.join(dest, info.filename)
                if info.is_dir():
                    os.makedirs(target, exist_ok=True)
                elif not os.path.exists(target):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with z.open(info) as s, open(target, "wb") as d:
                        shutil.copyfileobj(s, d)
    except zipfile.BadZipFile:
        return "Ye valid zip file nahi hai."
    return f"Unzip ho gaya: {dest}"


# ---------------------------------------------------------------------------
# Downloads organizer (with undo)
# ---------------------------------------------------------------------------
_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".heic"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".xls", ".ppt", ".pptx", ".csv", ".md"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
    "Music": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Installers": [".exe", ".msi"],
}


def _plan_downloads() -> list:
    d = winpaths.get_downloads()
    plan = []
    if not os.path.isdir(d):
        return plan
    for f in os.listdir(d):
        full = os.path.join(d, f)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(f)[1].lower()
        cat = next((c for c, exts in _CATEGORIES.items() if ext in exts), "Others")
        plan.append((full, os.path.join(d, cat, f), cat))
    return plan


@tool(category="files", dangerous=True, label="Organize Downloads")
def organize_downloads(confirmed: bool = False) -> str:
    """
    Sort files in the Downloads folder into subfolders by type (Images, Documents, Videos, Music, Archives,
    Installers, Others). Needs confirmation (confirmed=False first). Can be undone with undo_organize_downloads.
    """
    plan = _plan_downloads()
    if not plan:
        return "Downloads folder mein organize karne layak koi file nahi hai."
    summary = {}
    for _s, _d, cat in plan:
        summary[cat] = summary.get(cat, 0) + 1
    desc = ", ".join(f"{c}: {n}" for c, n in sorted(summary.items()))
    gate = safety.confirm_gate("organize_downloads", {"n": len(plan)}, confirmed,
                               f"Downloads ki {len(plan)} files type ke hisaab se sort karun? ({desc})")
    if gate:
        return gate
    moved = []
    for src, dst, _cat in plan:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                continue
            shutil.move(src, dst)
            moved.append({"from": src, "to": dst})
        except OSError:
            continue
    with open(UNDO_FILE, "w", encoding="utf-8") as f:
        json.dump(moved, f, ensure_ascii=False)
    return f"Downloads organize ho gaya: {len(moved)} files sort ki gayi. ('undo' bologe to wapas kar dunga)"


@tool(category="files", label="Undo organize")
def undo_organize_downloads() -> str:
    """Undo the last organize_downloads: move every file back to where it was."""
    if not os.path.exists(UNDO_FILE):
        return "Undo ke liye kuchh nahi hai."
    with open(UNDO_FILE, encoding="utf-8") as f:
        moved = json.load(f)
    back = 0
    for m in moved:
        try:
            if os.path.exists(m["to"]) and not os.path.exists(m["from"]):
                shutil.move(m["to"], m["from"])
                back += 1
        except OSError:
            continue
    for cat in list(_CATEGORIES) + ["Others"]:
        d = os.path.join(winpaths.get_downloads(), cat)
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        except OSError:
            pass
    os.remove(UNDO_FILE)
    return f"Undo ho gaya: {back} files wapas rakh di."
