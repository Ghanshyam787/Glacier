"""
Glacier Tools: MCP client (Model Context Protocol)
==================================================
Duniya bhar ke MCP servers (GitHub, Notion, Slack, filesystem, databases ...) Glacier se jod sakte ho.
Setup: data/mcp_servers.json banao:

{
  "servers": {
    "fs":     {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "D:\\\\Projects"]},
    "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
               "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."}}
  }
}

Zaroorat: pip install mcp   (aur npx wale servers ke liye Node.js)
Tools: mcp_list_tools, mcp_call (confirmation ke saath - kyunki bahari server kuchh bhi kar sakta hai).
"""

import asyncio
import json
import os
import shutil
import threading
from contextlib import AsyncExitStack

import config
import safety
from registry import tool

CONFIG_PATH = os.path.join(config.DATA_DIR, "mcp_servers.json")

_loop = None
_thread = None
_sessions = {}   # name -> (session, [tools])
_errors = {}
_lock = threading.Lock()
_stack = None


def _ensure_loop():
    global _loop, _thread
    with _lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            _thread = threading.Thread(target=_loop.run_forever, daemon=True, name="glacier-mcp")
            _thread.start()
    return _loop


def _run(coro, timeout=60):
    return asyncio.run_coroutine_threadsafe(coro, _ensure_loop()).result(timeout)


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f).get("servers", {})
    except Exception as e:
        _errors["config"] = str(e)
        return {}


async def _connect_all(servers: dict):
    global _stack
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    if _stack is None:
        _stack = AsyncExitStack()
    for name, spec in servers.items():
        if name in _sessions:
            continue
        try:
            cmd = spec["command"]
            if os.name == "nt" and not os.path.splitext(cmd)[1]:
                cmd = shutil.which(cmd) or cmd
            params = StdioServerParameters(command=cmd, args=spec.get("args", []),
                                           env={**os.environ, **spec.get("env", {})})
            read, write = await _stack.enter_async_context(stdio_client(params))
            session = await _stack.enter_async_context(ClientSession(read, write))
            await asyncio.wait_for(session.initialize(), 40)
            tools = (await session.list_tools()).tools
            _sessions[name] = (session, tools)
            _errors.pop(name, None)
        except Exception as e:
            _errors[name] = f"{type(e).__name__}: {str(e)[:150]}"


def _connect():
    servers = _load_config()
    if not servers:
        return False
    try:
        import mcp  # noqa: F401
    except ImportError:
        _errors["mcp"] = "mcp library install nahi hai (pip install mcp)"
        return False
    _run(_connect_all(servers), timeout=120)
    return True


@tool(category="mcp", untrusted="MCP server", label="MCP: list tools")
def mcp_list_tools() -> str:
    """List the tools offered by the MCP servers configured in data/mcp_servers.json."""
    if not os.path.exists(CONFIG_PATH):
        return ("Koi MCP server configured nahi hai. data/mcp_servers.json banao (format Glacier ke README mein hai) "
                "aur 'pip install mcp' karo.")
    try:
        if not _connect() and _errors.get("mcp"):
            return _errors["mcp"]
    except Exception as e:
        return f"MCP connect nahi hua: {str(e)[:200]}"
    if not _sessions:
        return "Koi server connect nahi hua. Errors: " + json.dumps(_errors)
    lines = []
    for name, (_s, tools) in _sessions.items():
        for t in tools:
            props = list(((t.inputSchema or {}).get("properties") or {}).keys())
            lines.append(f"{name}.{t.name}({', '.join(props)}) - {(t.description or '')[:90]}")
    if _errors:
        lines.append("Errors: " + json.dumps(_errors))
    return "\n".join(lines)


@tool(category="mcp", dangerous=True, untrusted="MCP server", label="MCP: call tool")
def mcp_call(server: str, tool_name: str, arguments_json: str = "{}", confirmed: bool = False) -> str:
    """
    Call a tool on an MCP server (see mcp_list_tools). arguments_json is a JSON object string. External servers
    can do anything, so this needs confirmation: confirmed=False first, then confirmed=True (same arguments).
    """
    try:
        args = json.loads(arguments_json or "{}")
        if not isinstance(args, dict):
            raise ValueError
    except Exception:
        return "arguments_json valid JSON object nahi hai."
    gate = safety.confirm_gate("mcp_call", {"s": server, "t": tool_name, "a": args}, confirmed,
                               f"MCP server '{server}' ka tool '{tool_name}' chalau?\nArguments: {arguments_json[:300]}")
    if gate:
        return gate
    if server not in _sessions:
        try:
            _connect()
        except Exception as e:
            return f"MCP connect nahi hua: {str(e)[:200]}"
    if server not in _sessions:
        return f"'{server}' server connected nahi hai. {json.dumps(_errors)}"
    session = _sessions[server][0]

    async def call():
        res = await session.call_tool(tool_name, args)
        return "\n".join(getattr(c, "text", str(c)) for c in res.content) or "(khaali jawab)"
    try:
        return _run(call(), timeout=90)
    except Exception as e:
        return f"MCP call fail: {str(e)[:250]}"
