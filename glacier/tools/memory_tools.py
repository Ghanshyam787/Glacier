"""
Glacier Tools: Memory & knowledge base
remember / recall / forget  - user ke baare mein permanent facts (SQLite)
index_folder / search_knowledge - apne documents mein local search (BM25), koi API nahi
"""

import os

import memory
import safety
import winpaths
from registry import tool


@tool(category="memory", label="Remember")
def remember(fact: str, tags: str = "") -> str:
    """
    Save a durable fact about the user for future chats (name, preferences, routines, people, projects).
    Short, self-contained sentence in third person, e.g. 'Ghanshyam ko subah 6 baje uthna pasand hai'.
    Never save passwords, card numbers or one-off temporary things.
    """
    res = memory.add_fact(fact, tags)
    if res == "empty":
        return "Fact bahut chhota hai."
    return "Pehle se yaad hai." if res == "exists" else f"Yaad rakh liya: {fact.strip()}"


@tool(category="memory", quiet=True, label="Recall")
def recall(query: str = "") -> str:
    """Look up what is remembered about the user (empty query lists the latest facts)."""
    facts = memory.search_facts(query, limit=10)
    if not facts:
        return "Is baare mein mujhe kuchh yaad nahi."
    return "\n".join(f"#{f['id']} {f['text']}" for f in facts)


@tool(category="memory", label="Forget")
def forget(fact_or_id: str) -> str:
    """Delete a remembered fact by its number (#id) or by words from it."""
    n = memory.delete_facts(fact_or_id.strip().lstrip("#"))
    return "Bhula diya." if n else "Aisa kuchh yaad nahi tha."


@tool(category="memory", label="Index folder")
def index_folder(path: str) -> str:
    """
    Teach Glacier your documents: index a folder (PDF, Word, Excel, text, code ...) so search_knowledge can answer
    questions from them. Re-running only picks up new/changed files. Use 'documents' or 'desktop' as shortcuts.
    """
    p = winpaths.resolve_folder_alias((path or "").strip().strip('"'))
    p = os.path.abspath(os.path.expanduser(p))
    if not safety.is_allowed_path(p):
        return safety.PATH_DENIED_MSG
    if not os.path.isdir(p):
        return f"Folder nahi mila: {p}"
    st = memory.index_folder(p, is_allowed=safety.is_allowed_path)
    if st.get("error"):
        return st["error"]
    tot = memory.knowledge_stats()
    extra = " (limit lag gayi - dobara chalao to baaki bhi aa jayengi)" if st.get("truncated") else ""
    return (f"Index ho gaya: {st['indexed']} nayi files, {st['unchanged']} pehle se updated, {st['skipped']} skip."
            f"{extra} Total knowledge: {tot['files']} files.")


@tool(category="memory", untrusted="your documents", label="Search documents")
def search_knowledge(query: str, limit: int = 5) -> str:
    """Search inside the documents the user indexed (index_folder). Returns best-matching passages with file paths."""
    rows = memory.search_knowledge(query, max(1, min(int(limit or 5), 10)))
    if not rows:
        st = memory.knowledge_stats()
        return "Kuchh nahi mila." if st["files"] else "Abhi koi document index nahi hai. Pehle index_folder se folder batao."
    return "\n\n".join(f"[{os.path.basename(r['path'])}] {r['path']}\n{r['snip']}" for r in rows)


@tool(category="memory", quiet=True, label="Knowledge status")
def knowledge_status() -> str:
    """How many documents are indexed for search_knowledge."""
    st = memory.knowledge_stats()
    return f"{st['files']} files indexed ({st['chunks']} passages)."
