#!/usr/bin/env python3
"""
Fabric Protocol Logger

Appends machine-readable events to {WORK_ROOT}/logs/protocol.jsonl
and a human-readable trail to {WORK_ROOT}/logs/protocol.md.

Design goals:
- Zero external dependencies beyond stdlib + PyYAML (yaml).
- Works even if state.md/config.md are missing (best effort).
- Safe to call repeatedly; creates logs dir/files if missing.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Reuse Fabric placeholder expansion if available.
try:
    from fabric_lib import build_ctx, expand_placeholders  # type: ignore
except Exception:  # pragma: no cover
    build_ctx = None  # type: ignore
    expand_placeholders = None  # type: ignore


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_text(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _extract_yaml_blocks(md_text: str) -> list[str]:
    blocks: list[str] = []
    parts = md_text.split("```yaml")
    for part in parts[1:]:
        if "```" not in part:
            continue
        block = part.split("```", 1)[0].strip()
        if block:
            blocks.append(block)
    return blocks


def _load_config(work_root: Path) -> Dict[str, Any]:
    cfg_path = work_root / "config.md"
    text = _read_text(cfg_path)
    if not text:
        return {}
    merged: Dict[str, Any] = {}
    for b in _extract_yaml_blocks(text):
        try:
            data = yaml.safe_load(b) or {}
            if isinstance(data, dict):
                merged.update(data)
        except Exception:
            # best-effort: ignore broken blocks; validator should catch
            continue
    return merged


def _load_state(work_root: Path) -> Dict[str, Any]:
    st_path = work_root / "state.md"
    text = _read_text(st_path)
    if not text:
        return {}
    blocks = _extract_yaml_blocks(text)
    if not blocks:
        return {}
    try:
        data = yaml.safe_load(blocks[0]) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _resolve_cfg_path(repo_root: Path, value: Any, fallback: Path) -> Path:
    """Resolve a config path.
    - Absolute paths stay absolute.
    - Relative paths are interpreted relative to repo_root (work_root parent).
    """
    if not value:
        return fallback
    try:
        p = Path(str(value))
        return (repo_root / p).resolve() if not p.is_absolute() else p.resolve()
    except Exception:
        return fallback


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _append_md(path: Path, line: str) -> None:
    # create a lightweight header once for readability
    if not path.exists() or (path.exists() and path.stat().st_size == 0):
        _ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as f:
            f.write("# Fabric Protocol\n\n")
            f.write("- This file is append-only.\n")
            f.write("- Machine log is protocol.jsonl in the same directory.\n\n")

    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-root", required=True, help="Fabric workspace root, e.g. fabric/")
    ap.add_argument("--skill", required=True, help="Skill name, e.g. fabric-loop")
    ap.add_argument(
        "--event", required=True, choices=["start", "end", "error"], help="Lifecycle event"
    )
    ap.add_argument("--status", default=None, help="Optional status: OK|WARN|ERROR|SKIPPED")
    ap.add_argument("--message", default=None, help="Short human message")
    ap.add_argument("--report", default=None, help="Optional path to a report file")
    ap.add_argument("--data", default=None, help="Optional JSON string payload (small!)")
    args = ap.parse_args(argv)

    # Best-effort: allow passing literal placeholders (common in skills) without crashing.
    # If the caller passes "{WORK_ROOT}" we fall back to ./fabric if it exists.
    raw_wr = (args.work_root or "").strip()
    if "{" in raw_wr and "}" in raw_wr:
        # Minimal token expansion for the most common case.
        raw_wr = raw_wr.replace("{WORK_ROOT}", "fabric").replace("{work_root}", "fabric")
    work_root = Path(raw_wr).resolve()
    cfg = _load_config(work_root)
    st = _load_state(work_root)

    repo_root = work_root.parent

    logs_root = _resolve_cfg_path(repo_root, cfg.get("LOGS_ROOT"), work_root / "logs")
    jsonl_path = _resolve_cfg_path(
        repo_root, cfg.get("PROTOCOL_LOG_JSONL"), logs_root / "protocol.jsonl"
    )
    md_path = _resolve_cfg_path(repo_root, cfg.get("PROTOCOL_LOG_MD"), logs_root / "protocol.md")

    payload: Dict[str, Any] = {}
    if args.data:
        try:
            payload = json.loads(args.data)
            if not isinstance(payload, dict):
                payload = {"value": payload}
        except Exception:
            payload = {"raw": args.data}

    ts = _utc_now()

    # Expand placeholders in human fields (message/report) using config+state when possible.
    ctx: Dict[str, str] = {}
    if build_ctx and expand_placeholders:
        try:
            ctx = build_ctx(cfg, st)
        except Exception:
            ctx = {}

    message = args.message
    report = args.report
    if ctx and expand_placeholders:
        try:
            if isinstance(message, str):
                message = expand_placeholders(message, ctx)
            if isinstance(report, str):
                report = expand_placeholders(report, ctx)
        except Exception:
            # Best-effort only; never fail logging.
            pass
    record: Dict[str, Any] = {
        "ts": ts,
        "event": args.event,
        "skill": args.skill,
        "status": args.status,
        "message": message,
        "report": report,
        "run_id": st.get("run_id"),
        "phase": st.get("phase"),
        "step": st.get("step"),
        "sprint": st.get("sprint"),
        "wip_item": st.get("wip_item"),
        "wip_branch": st.get("wip_branch"),
        "payload": payload or None,
    }
    # Remove None keys for compactness
    record = {k: v for k, v in record.items() if v is not None}

    _append_jsonl(jsonl_path, record)

    # Human trail (very compact)
    status = args.status or "-"
    msg = f" — {message}" if message else ""
    rep = f" (report: {report})" if report else ""
    _append_md(md_path, f"- `{ts}` **{args.skill}** `{args.event}` `{status}`{msg}{rep}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
