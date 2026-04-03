"""
prolog-mcp-server.py — MCP server wrapping the prolog-reasoning engine.

Tools:    prolog_query, prolog_assert, prolog_retract, prolog_validate, prolog_manifest
Resource: prolog://kb  (raw KB content)

Config:   ~/.prolog-mcp/config.toml
"""

import datetime
import importlib.util
import io
import os
import shutil
import sys
import tomllib
from contextlib import redirect_stdout
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_DIR  = Path.home() / ".prolog-mcp"
CONFIG_PATH = CONFIG_DIR / "config.toml"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}

_cfg = _load_config()

KB_PATH       = Path(os.path.expanduser(_cfg.get("kb", {}).get("path",        str(CONFIG_DIR / "knowledge-base.pl"))))
BACKUP_DIR    = Path(os.path.expanduser(_cfg.get("backups", {}).get("dir",    str(CONFIG_DIR / "backups"))))
BACKUP_RETAIN = int(_cfg.get("backups", {}).get("retain", 7))
EXECUTOR_PATH = Path(os.path.expanduser(_cfg.get("engine", {}).get(
    "executor_path", str(Path(__file__).parent / "prolog-executor.py")
)))

# ---------------------------------------------------------------------------
# Load executor (hyphenated filename requires importlib)
# ---------------------------------------------------------------------------

def _load_executor():
    spec = importlib.util.spec_from_file_location("prolog_executor", EXECUTOR_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_ex = _load_executor()

# ---------------------------------------------------------------------------
# Backup helper (mirrors executor logic, uses config paths)
# ---------------------------------------------------------------------------

def _backup_kb() -> None:
    if not KB_PATH.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().strftime("%Y-%m-%d")
    dest  = BACKUP_DIR / f"knowledge-base-{today}.pl"
    if not dest.exists():
        shutil.copy2(KB_PATH, dest)
    backups = sorted(
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith("knowledge-base-") and f.endswith(".pl")
    )
    for old in backups[:-BACKUP_RETAIN]:
        (BACKUP_DIR / old).unlink()

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "prolog-kb",
    instructions="Persistent lossless fact store with Prolog inference. "
                 "Use prolog_query for retrieval, prolog_assert/prolog_retract to mutate, "
                 "prolog_manifest to orient yourself to what is known.",
)


@mcp.tool()
def prolog_query(goal: str) -> dict:
    """Run a Prolog query against the knowledge base.

    Returns bindings on success (e.g. {"X": "alice", "Y": "bob"}) or an error dict.
    Supports full Prolog syntax: unification, rules, findall/3, negation-as-failure.

    Examples:
        prolog_query("person(X)")
        prolog_query("parent(alice, X), female(X)")
        prolog_query("findall(X, friend(scott, X), Friends)")
    """
    return _ex.run_query(goal, str(KB_PATH))


@mcp.tool()
def prolog_assert(fact: str) -> dict:
    """Assert a new fact into the knowledge base.

    Validates syntax before writing. Silently deduplicates — safe to call repeatedly.
    Triggers a daily backup on the first write of the day.

    Examples:
        prolog_assert("friend(alice, bob)")
        prolog_assert("owns(scott, guitar)")
    """
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = _ex.run_assert(fact, str(KB_PATH))
    if result.get("success") and not result.get("skipped"):
        _backup_kb()
    return result


@mcp.tool()
def prolog_retract(fact: str) -> dict:
    """Remove a matching fact from the knowledge base.

    Matches by structural equality. Rewrites the file preserving comments and ordering.
    Only removes single-line facts — multi-line rules are not affected.

    Examples:
        prolog_retract("friend(alice, bob)")
        prolog_retract("owns(scott, guitar)")
    """
    if not KB_PATH.exists():
        return {"success": False, "error": "Knowledge base not found"}

    fact   = fact.strip().rstrip(".")
    engine = _ex.PrologEngine()
    target = engine._parse_term(fact)
    if target is None:
        return {"success": False, "error": f"Could not parse: {fact!r}"}

    lines     = KB_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = []
    removed   = 0

    for line in lines:
        stripped = line.strip()
        # Keep comments and blank lines untouched
        if not stripped or stripped.startswith("%"):
            new_lines.append(line)
            continue
        # Only attempt to match single-line facts (end with a period)
        if stripped.endswith("."):
            parsed = engine._parse_term(stripped.rstrip("."))
            if parsed is not None and parsed == target:
                removed += 1
                continue
        new_lines.append(line)

    if removed == 0:
        return {"success": False, "error": f"No matching fact found: {fact!r}"}

    KB_PATH.write_text("".join(new_lines), encoding="utf-8")
    _backup_kb()
    return {"success": True, "retracted": removed}


@mcp.tool()
def prolog_validate() -> dict:
    """Validate the knowledge base for common syntax errors.

    Catches unquoted dates (2026-03-31 parsed as arithmetic), hyphenated names,
    and arithmetic expressions in data positions. Returns warnings with suggested fixes.
    """
    if not KB_PATH.exists():
        return {"success": False, "error": "Knowledge base not found"}

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            _ex.run_validate(str(KB_PATH))
        return {"success": True, "warnings": [], "output": buf.getvalue()}
    except SystemExit as e:
        output = buf.getvalue()
        return {
            "success": e.code == 0,
            "warnings": [l for l in output.splitlines() if l.strip()],
            "exit_code": int(e.code) if e.code is not None else 0,
        }


@mcp.tool()
def prolog_manifest() -> str:
    """Summarise the knowledge base: entity list, predicate inventory, fact/rule counts.

    Call this at the start of a session to orient yourself to what is known.
    """
    if not KB_PATH.exists():
        return "Knowledge base not found. Use prolog_assert to start adding facts."
    data = _ex._introspect_kb(str(KB_PATH))
    if data is None:
        return "Could not read knowledge base."
    return "\n".join(_ex._kb_block("Knowledge Base", data))


@mcp.resource("prolog://kb")
def kb_resource() -> str:
    """Raw content of the knowledge base (.pl file)."""
    if not KB_PATH.exists():
        return ""
    return KB_PATH.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()
