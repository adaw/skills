#!/usr/bin/env python3
"""
fabric_lib.py — Shared deterministic helpers for Fabric tooling.

Goals:
- Keep mechanical filesystem/YAML/MD operations deterministic.
- Avoid YAML date auto-coercion (treat ISO dates as strings).
- Provide safe patch operations for frontmatter and YAML code fences.

This module is intentionally dependency-light (stdlib + PyYAML).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml  # type: ignore


# ----------------------------
# YAML loader without dates
# ----------------------------


class _NoDatesSafeLoader(yaml.SafeLoader):
    pass


# Remove implicit resolver for timestamps (YYYY-MM-DD etc.)
for ch, resolvers in list(_NoDatesSafeLoader.yaml_implicit_resolvers.items()):
    _NoDatesSafeLoader.yaml_implicit_resolvers[ch] = [
        (tag, regexp) for (tag, regexp) in resolvers if tag != "tag:yaml.org,2002:timestamp"
    ]


def yaml_load(s: str) -> Any:
    return yaml.load(s, Loader=_NoDatesSafeLoader)


def yaml_dump(data: Any) -> str:
    # Keep key order; emit 'null' not '~'; keep unicode.
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )


# ----------------------------
# Config discovery + parsing
# ----------------------------

CONFIG_MARKERS = ["WORK_ROOT:", "CODE_ROOT:", "COMMANDS:"]


def find_repo_root(start: Path) -> Path:
    """Walk parents until a directory containing 'skills' is found."""
    p = start.resolve()
    for candidate in [p] + list(p.parents):
        if (candidate / "skills").is_dir():
            return candidate
    return p


def discover_config(repo_root: Path) -> Tuple[Optional[Path], List[Path]]:
    """Find config.md candidates by content markers; choose deterministically."""
    candidates: List[Path] = []
    for p in repo_root.rglob("config.md"):
        if not p.is_file():
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if all(marker in txt for marker in CONFIG_MARKERS):
            candidates.append(p)

    if not candidates:
        return None, []
    candidates_sorted = sorted(candidates, key=lambda p: (len(str(p)), str(p)))
    return candidates_sorted[0], candidates_sorted


def extract_yaml_blocks(md: str) -> List[dict]:
    blocks: List[dict] = []
    for m in re.finditer(r"```yaml\s*(.*?)```", md, flags=re.S | re.I):
        raw = m.group(1)
        try:
            data = yaml_load(raw)
        except Exception:
            continue
        if isinstance(data, dict):
            blocks.append(data)
    return blocks


def merge_blocks(blocks: List[dict]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for b in blocks:
        merged.update(b)
    return merged


def parse_config_md(p: Path) -> Dict[str, Any]:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    blocks = extract_yaml_blocks(txt)
    merged = merge_blocks(blocks)
    return merged


def get_paths_block(config: Dict[str, Any]) -> Dict[str, str]:
    # Paths are top-level keys in the paths YAML fence (WORK_ROOT etc.).
    # In merged form, they are top-level keys.
    keys = [
        "WORK_ROOT",
        "SKILLS_ROOT",
        "CODE_ROOT",
        "TEST_ROOT",
        "DOCS_ROOT",
        "CONFIG_ROOT",
        "TEMPLATES_ROOT",
        "ANALYSES_ROOT",
        "VISIONS_ROOT",
        "DECISIONS_ROOT",
        "SPECS_ROOT",
        "REVIEWS_ROOT",
    ]
    out: Dict[str, str] = {}
    for k in keys:
        v = config.get(k)
        if isinstance(v, str):
            out[k] = v
    return out


# ----------------------------
# Markdown frontmatter + code fences
# ----------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def parse_frontmatter(md: str) -> Optional[dict]:
    m = FRONTMATTER_RE.match(md)
    if not m:
        return None
    raw = m.group(1)
    try:
        data = yaml_load(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def replace_frontmatter(md: str, fm: dict, key_order: Optional[List[str]] = None) -> str:
    # preserve body after frontmatter
    m = FRONTMATTER_RE.match(md)
    body = md[m.end() :] if m else md

    ordered: Dict[str, Any] = {}
    if key_order:
        for k in key_order:
            if k in fm:
                ordered[k] = fm[k]
        for k, v in fm.items():
            if k not in ordered:
                ordered[k] = v
    else:
        ordered = fm  # type: ignore

    raw = yaml_dump(ordered).strip("\n")
    return f"---\n{raw}\n---\n{body}"


YAML_FENCE_RE = re.compile(r"```yaml\s*(.*?)```", re.S | re.I)


def parse_yaml_fence(md: str) -> Optional[Tuple[dict, Tuple[int, int]]]:
    """
    Return (data, (start_index, end_index)) for the first ```yaml ... ``` block.
    start/end refer to slice covering the raw YAML content inside the fence.
    """
    m = YAML_FENCE_RE.search(md)
    if not m:
        return None
    raw = m.group(1)
    try:
        data = yaml_load(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data, (m.start(1), m.end(1))


def replace_yaml_fence(md: str, data: dict, span: Tuple[int, int]) -> str:
    start, end = span
    raw = yaml_dump(data).strip("\n")
    # Ensure the closing ``` stays on its own line for readability.
    return md[:start] + raw + "\n" + md[end:]


# ----------------------------
# Template utilities
# ----------------------------


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def safe_relpath(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except Exception:
        return str(p)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


@dataclass
class CmdResult:
    ok: bool
    exit_code: int
    duration_s: float
    log_path: Optional[str]
    tail: Optional[str]


# ----------------------------
# Placeholder expansion (deterministic)
# ----------------------------

# Curly-brace placeholders used across templates/skills.
# We intentionally replace only *known* tokens; unknown placeholders are left as-is.
# Allow both UPPER and lower tokens (older docs often used {wip_item}).
PLACEHOLDER_TOKEN_RE = re.compile(r"\{([A-Za-z0-9_:\-]+)\}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def time_tokens(dt: Optional[datetime] = None) -> Dict[str, str]:
    dt = dt or utc_now()
    return {
        "YYYY": dt.strftime("%Y"),
        "MM": dt.strftime("%m"),
        "DD": dt.strftime("%d"),
        "YYYY-MM-DD": dt.strftime("%Y-%m-%d"),
        "YYYYMMDD": dt.strftime("%Y%m%d"),
        "HHMMSS": dt.strftime("%H%M%S"),
        "YYYY-MM-DDTHH:MM:SSZ": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "YYYYMMDD-HHMMSSZ": dt.strftime("%Y%m%d-%H%M%SZ"),
    }


def build_ctx(
    config: Optional[Dict[str, Any]] = None,
    state: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    dt: Optional[datetime] = None,
) -> Dict[str, str]:
    """Build a placeholder context from config/state + current time.

    Returns a string-only mapping (safe for template substitution).
    """
    ctx: Dict[str, str] = {}

    # Time tokens
    for k, v in time_tokens(dt).items():
        ctx[k] = v

    # Config-derived tokens
    if config:
        paths = get_paths_block(config)
        for k, v in paths.items():
            # For template substitution we prefer normalized "no trailing slash".
            # (Filesystem joins elsewhere handle both forms.)
            ctx[k] = v.rstrip("/") if v.endswith("/") else v

        git = config.get("GIT") if isinstance(config.get("GIT"), dict) else {}
        if isinstance(git, dict):
            main_branch = git.get("main_branch")
            if isinstance(main_branch, str):
                ctx["MAIN_BRANCH"] = main_branch

        run = config.get("RUN") if isinstance(config.get("RUN"), dict) else {}
        if isinstance(run, dict):
            # expose as strings when useful
            for k in ["max_ticks_default", "max_ticks_clamp", "auto_max_ticks"]:
                if k in run and isinstance(run[k], (int, float, str)):
                    ctx[f"RUN.{k}"] = str(run[k])

    # State-derived tokens
    if state:
        for sk, tk in [
            ("run_id", "RUN_ID"),
            ("phase", "PHASE"),
            ("step", "STEP"),
            ("wip_item", "WIP_ITEM"),
            ("wip_branch", "WIP_BRANCH"),
            ("sprint_goal", "SPRINT_GOAL"),
        ]:
            v = state.get(sk)
            if v is None:
                continue
            if isinstance(v, (int, float)):
                ctx[tk] = str(v)
            elif isinstance(v, str):
                ctx[tk] = v

        sprint = state.get("sprint")
        if isinstance(sprint, (int, float, str)):
            ctx["SPRINT_NUMBER"] = str(sprint)

    # Extra tokens (caller-supplied)
    if extra:
        for k, v in extra.items():
            if v is None:
                continue
            if isinstance(v, (int, float)):
                ctx[k] = str(v)
            elif isinstance(v, str):
                ctx[k] = v

    # Convenience lowercase aliases (older docs often use {wip_item} etc.).
    # These do not replace the canonical uppercase tokens; they just improve compatibility.
    for k in [
        "WORK_ROOT",
        "REPO_ROOT",
        "RUN_ID",
        "SPRINT_NUMBER",
        "SPRINT_GOAL",
        "WIP_ITEM",
        "WIP_BRANCH",
        "STEP",
        "PHASE",
    ]:
        if k in ctx:
            ctx[k.lower()] = ctx[k]
    return ctx


def expand_placeholders(s: str, ctx: Dict[str, str]) -> str:
    """Replace {TOKEN} placeholders using ctx. Unknown tokens remain unchanged."""
    if not s:
        return s

    def _repl(m: re.Match) -> str:
        token = m.group(1)
        return ctx.get(token, m.group(0))

    return PLACEHOLDER_TOKEN_RE.sub(_repl, s)


def expand_obj(obj: Any, ctx: Dict[str, str]) -> Any:
    """Recursively expand placeholders in strings inside obj."""
    if isinstance(obj, str):
        return expand_placeholders(obj, ctx)
    if isinstance(obj, list):
        return [expand_obj(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: expand_obj(v, ctx) for k, v in obj.items()}
    return obj
