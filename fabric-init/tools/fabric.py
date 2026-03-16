#!/usr/bin/env python3
"""
fabric.py — Deterministic toolset for Fabric.

Philosophy:
- LLM should spend tokens on thinking, not on IO-heavy mechanical work.
- This CLI performs repeatable tasks deterministically: scan, index, patch YAML,
  create skeletons, run configured commands with log capture, apply plans.

This script is meant to be called BY SKILLS (LLM-driven development),
not manually by humans (although it can be used locally too).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fabric_lib import (
    CmdResult,
    build_ctx,
    discover_config,
    expand_obj,
    expand_placeholders,
    find_repo_root,
    get_paths_block,
    is_within,
    parse_config_md,
    parse_frontmatter,
    parse_yaml_fence,
    read_text,
    replace_frontmatter,
    replace_yaml_fence,
    safe_relpath,
    yaml_dump,
    yaml_load,
)

BACKLOG_KEY_ORDER = [
    "id",
    "title",
    "type",
    "tier",
    "status",
    "effort",
    "created",
    "updated",
    "source",
    "prio",
    "depends_on",
    "blocked_by",
    "branch",
    "review_report",
    "merge_commit",
]

INTAKE_KEY_ORDER = [
    "id",
    "schema",
    "title",
    "source",
    "date",
    "created_by",
    "initial_type",
    "raw_priority",
    "linked_vision_goal",
]

DEFAULT_REQUIRED_DIRS = [
    "backlog",
    "backlog/done",
    "intake",
    "intake/done",
    "intake/rejected",
    "reports",
    "logs",
    "logs/commands",
    "archive",
    "archive/backlog",
    "archive/sprints",
    "archive/reports",
    "archive/analyses",
    "archive/visions",
    "archive/quarantine",
    "sprints",
    "analyses",
    "templates",
    "visions",
    "decisions",
    "specs",
    "reviews",
]


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def generate_run_id() -> str:
    """Generate a correlation id for a Fabric loop run (UTC, collision-resistant)."""
    dt = datetime.now(timezone.utc)
    return f"RUN-{dt.strftime('%Y%m%d-%H%M%SZ')}-{dt.microsecond:06d}"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def append_jsonl(p: Path, obj: Any) -> None:
    """Append a single JSON line (UTF-8) deterministically.

    Used for flight-recorders (ticks/contract checks/etc.).
    This function must never raise in normal operation.
    """
    try:
        ensure_dir(p.parent)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging; do not fail critical commands.
        return


def append_md(p: Path, line: str) -> None:
    """Append a single Markdown line."""
    try:
        ensure_dir(p.parent)
        with p.open("a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")
    except Exception:
        return


def slugify(s: str, max_len: int = 48) -> str:
    """Deterministic slug for filenames."""
    t = (s or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    if not t:
        t = "item"
    return t[:max_len]


def load_config(repo_root: Path, config_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    if config_path is None:
        chosen, _ = discover_config(repo_root)
        if chosen is None:
            raise FileNotFoundError("config.md not found (no file with required Fabric markers).")
        config_path = chosen
    cfg = parse_config_md(config_path)
    return config_path, cfg


def resolve_rel(repo_root: Path, rel: str) -> Path:
    # Accept "./x" or "x"; normalize trailing slashes.
    rel = rel.strip()
    if rel.startswith("./"):
        rel = rel[2:]
    return (repo_root / rel).resolve()


def assets_root() -> Path:
    # skills/fabric-init/tools/fabric.py -> skills/fabric-init/assets
    return Path(__file__).resolve().parent.parent / "assets"


def canonical_templates_dir() -> Path:
    return assets_root() / "templates"


def copy_missing_templates(templates_dir: Path, required: List[str]) -> List[str]:
    copied: List[str] = []
    src_dir = canonical_templates_dir()
    for name in required:
        src = src_dir / name
        dst = templates_dir / name
        if not dst.exists():
            if not src.exists():
                # Source missing in skills assets: this is a framework bug, not workspace bug.
                raise FileNotFoundError(f"Canonical template missing in skills assets: {src}")
            ensure_dir(dst.parent)
            shutil.copy2(src, dst)
            copied.append(str(dst))
    return copied


def parse_required_templates(config: Dict[str, Any]) -> List[str]:
    contracts = config.get("TEMPLATES_REQUIRED")
    if isinstance(contracts, list) and all(isinstance(x, str) for x in contracts):
        return list(contracts)
    # fallback: scan canonical dir
    return sorted([p.name for p in canonical_templates_dir().glob("*.md")])


def ensure_workspace_skeleton(
    repo_root: Path, config_path: Optional[Path], create_vision_stub: bool
) -> Dict[str, Any]:
    """
    Idempotently ensure the Fabric workspace exists.
    Returns a summary dict (created dirs/files/templates).
    """
    summary: Dict[str, Any] = {
        "created_dirs": [],
        "created_files": [],
        "copied_templates": [],
        "config_path": None,
    }
    assets = assets_root()

    # Ensure config exists; if missing, bootstrap from template.
    if config_path is None:
        chosen, _ = discover_config(repo_root)
        if chosen is None:
            # Use config template to learn default WORK_ROOT
            template_path = assets / "config.template.md"
            tpl_cfg = parse_config_md(template_path)
            paths = get_paths_block(tpl_cfg)
            work_root_rel = paths.get("WORK_ROOT", "fabric/")
            work_root = resolve_rel(repo_root, work_root_rel)
            ensure_dir(work_root)
            dst_cfg = work_root / "config.md"
            if not dst_cfg.exists():
                shutil.copy2(template_path, dst_cfg)
                summary["created_files"].append(str(dst_cfg))
            config_path = dst_cfg
        else:
            config_path = chosen

    summary["config_path"] = safe_relpath(config_path, repo_root)

    cfg_path, cfg = load_config(repo_root, config_path)

    paths = get_paths_block(cfg)
    work_root_rel = paths.get("WORK_ROOT", "fabric/")
    templates_root_rel = paths.get("TEMPLATES_ROOT", f"{work_root_rel.rstrip('/')}/templates/")
    analyses_root_rel = paths.get("ANALYSES_ROOT", f"{work_root_rel.rstrip('/')}/analyses/")
    visions_root_rel = paths.get("VISIONS_ROOT", f"{work_root_rel.rstrip('/')}/visions/")
    decisions_root_rel = paths.get("DECISIONS_ROOT", f"{work_root_rel.rstrip('/')}/decisions/")
    specs_root_rel = paths.get("SPECS_ROOT", f"{work_root_rel.rstrip('/')}/specs/")
    reviews_root_rel = paths.get("REVIEWS_ROOT", f"{work_root_rel.rstrip('/')}/reviews/")

    work_root = resolve_rel(repo_root, work_root_rel)
    templates_dir = resolve_rel(repo_root, templates_root_rel)
    analyses_dir = resolve_rel(repo_root, analyses_root_rel)
    visions_dir = resolve_rel(repo_root, visions_root_rel)
    decisions_dir = resolve_rel(repo_root, decisions_root_rel)
    specs_dir = resolve_rel(repo_root, specs_root_rel)
    reviews_dir = resolve_rel(repo_root, reviews_root_rel)

    # Create required dirs
    for d in DEFAULT_REQUIRED_DIRS:
        p = work_root / d if not d.startswith(("analyses", "visions", "templates")) else None
        if d == "analyses":
            p = analyses_dir
        elif d == "visions":
            p = visions_dir
        elif d == "templates":
            p = templates_dir
        elif d == "decisions":
            p = decisions_dir
        elif d == "specs":
            p = specs_dir
        elif d == "reviews":
            p = reviews_dir
        assert p is not None
        if not p.exists():
            ensure_dir(p)
            summary["created_dirs"].append(str(p))

    # Ensure templates exist
    required_templates = parse_required_templates(cfg)
    copied = copy_missing_templates(templates_dir, required_templates)
    summary["copied_templates"] = copied

    # Ensure state.md
    state_path = work_root / "state.md"
    if not state_path.exists():
        # Prefer workspace template if present.
        src = templates_dir / "state.md"
        if not src.exists():
            src = canonical_templates_dir() / "state.md"
        shutil.copy2(src, state_path)
        summary["created_files"].append(str(state_path))

    # Ensure backlog index
    backlog_index = work_root / "backlog.md"
    if not backlog_index.exists():
        backlog_index.write_text(
            "# Backlog Index\n\n| ID | Title | Type | Status | Tier | Effort | PRIO |\n|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
        summary["created_files"].append(str(backlog_index))

    # Ensure vision.md
    vision_path = work_root / "vision.md"
    if not vision_path.exists() and create_vision_stub:
        vision_path.write_text(
            "# Vize (Core)\n\n> TODO: Doplň core vizi projektu. Bez vize je autonomie nebezpečná.\n",
            encoding="utf-8",
        )
        summary["created_files"].append(str(vision_path))

    # Ensure visions/ exists (already) and optionally drop README
    visions_readme = visions_dir / "README.md"
    if not visions_readme.exists():
        visions_readme.write_text(
            "# Sub-vize (visions/)\n\nTento adresář rozpracovává principy z core vision.md do hloubky.\n",
            encoding="utf-8",
        )
        summary["created_files"].append(str(visions_readme))

    # Ensure governance indices (lightweight, deterministic)
    for title, d in [
        ("Decisions (ADR) Index", decisions_dir),
        ("Specs Index", specs_dir),
        ("Reviews Index", reviews_dir),
    ]:
        idx = d / "INDEX.md"
        if not idx.exists():
            idx.write_text(
                f"# {title}\n\n| ID | Title | Status | Date | File |\n|---|---|---|---|---|\n",
                encoding="utf-8",
            )
            summary["created_files"].append(str(idx))

    return summary


def parse_backlog_items(backlog_dir: Path, include_done: bool) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    paths: List[Path] = []
    for p in backlog_dir.glob("*.md"):
        if p.is_file():
            paths.append(p)
    if include_done:
        done_dir = backlog_dir / "done"
        if done_dir.exists():
            for p in done_dir.glob("*.md"):
                if p.is_file():
                    paths.append(p)

    for p in sorted(paths, key=lambda x: x.name):
        txt = read_text(p)
        fm = parse_frontmatter(txt) or {}
        item = dict(fm)
        item["_path"] = str(p)
        items.append(item)
    return items


def parse_intake_items(intake_dir: Path, include_done: bool) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    paths: List[Path] = []
    for p in intake_dir.glob("*.md"):
        if p.is_file():
            paths.append(p)
    if include_done:
        done_dir = intake_dir / "done"
        if done_dir.exists():
            for p in done_dir.glob("*.md"):
                if p.is_file():
                    paths.append(p)

    for p in sorted(paths, key=lambda x: x.name):
        txt = read_text(p)
        fm = parse_frontmatter(txt) or {}
        item = dict(fm)
        item["_path"] = str(p)
        items.append(item)
    return items


def backlog_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_status: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    by_tier: Dict[str, int] = {}
    wip: List[str] = []
    for it in items:
        st = str(it.get("status", "UNKNOWN"))
        tp = str(it.get("type", "UNKNOWN"))
        tr = str(it.get("tier", "UNKNOWN"))
        by_status[st] = by_status.get(st, 0) + 1
        by_type[tp] = by_type.get(tp, 0) + 1
        by_tier[tr] = by_tier.get(tr, 0) + 1
        if st in ("IN_PROGRESS", "IN_REVIEW"):
            if "id" in it:
                wip.append(str(it.get("id")))
    return {
        "by_status": by_status,
        "by_type": by_type,
        "by_tier": by_tier,
        "wip": wip,
        "count": len(items),
    }


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_backlog_index(work_root: Path, items: List[Dict[str, Any]]) -> str:
    # Sort by prio desc (missing -> 0), then tier, then id.
    def prio_val(x: Dict[str, Any]) -> int:
        try:
            return int(x.get("prio", 0) or 0)
        except Exception:
            return 0

    def tier_val(x: Dict[str, Any]) -> str:
        return str(x.get("tier", ""))

    def id_val(x: Dict[str, Any]) -> str:
        return str(x.get("id", ""))

    items_sorted = sorted(items, key=lambda it: (-prio_val(it), tier_val(it), id_val(it)))
    lines = []
    lines.append("# Backlog Index\n")
    lines.append("| ID | Title | Type | Status | Tier | Effort | PRIO |")
    lines.append("|---|---|---|---|---|---|---|")
    for it in items_sorted:
        lines.append(
            f"| {it.get('id', '')} | {str(it.get('title', '')).replace('|', '/')} | {it.get('type', '')} | {it.get('status', '')} | {it.get('tier', '')} | {it.get('effort', '')} | {it.get('prio', 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _first_heading(md: str) -> str:
    for ln in md.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            # strip leading #'s and whitespace
            return s.lstrip("#").strip()
    return ""


def _parse_date_yyyy_mm_dd(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def parse_governance_items(dir_path: Path) -> List[Dict[str, Any]]:
    """Parse markdown files in a governance directory (decisions/specs/reviews).

    Deterministic order: filename.
    Supports both YAML-frontmatter files and plain markdown.
    """
    items: List[Dict[str, Any]] = []
    if not dir_path.exists():
        return items
    for p in sorted(dir_path.glob("*.md"), key=lambda x: x.name):
        if not p.is_file():
            continue
        if p.name.upper() == "INDEX.MD":
            continue
        txt = read_text(p)
        fm = parse_frontmatter(txt) or {}
        item: Dict[str, Any] = {}
        stem = p.stem
        item_id = fm.get("id") if isinstance(fm.get("id"), str) else None
        if not item_id and (stem.startswith("ADR-") or stem.startswith("SPEC-")):
            item_id = stem
        if not item_id:
            item_id = stem
        item["id"] = item_id
        title = fm.get("title") if isinstance(fm.get("title"), str) else ""
        if not title:
            title = _first_heading(txt)
        item["title"] = title
        item["schema"] = fm.get("schema") if isinstance(fm.get("schema"), str) else ""
        item["status"] = fm.get("status") if isinstance(fm.get("status"), str) else ""
        item["date"] = fm.get("date") if isinstance(fm.get("date"), str) else ""
        item["_file"] = p.name
        items.append(item)
    return items


def generate_governance_index(title: str, items: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append(f"# {title}\n")
    lines.append("| ID | Title | Status | Date | File |")
    lines.append("|---|---|---|---|---|")
    for it in items:
        file_name = str(it.get("_file", ""))
        file_cell = f"[{file_name}]({file_name})" if file_name else ""
        lines.append(
            f"| {it.get('id', '')} | {str(it.get('title', '')).replace('|', '/')} | {it.get('status', '')} | {it.get('date', '')} | {file_cell} |"
        )
    lines.append("")
    return "\n".join(lines)


def scan_governance(
    items: List[Dict[str, Any]],
    stale_status: str,
    stale_days: int,
    allowed_statuses: Optional[List[str]] = None,
    expected_schema: str = "",
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    by_status: Dict[str, int] = {}
    stale: List[Dict[str, Any]] = []
    missing_dates: List[Dict[str, Any]] = []
    invalid_status: List[Dict[str, Any]] = []
    invalid_schema: List[Dict[str, Any]] = []
    seen_ids: Dict[str, int] = {}
    duplicates: List[Dict[str, Any]] = []
    for it in items:
        st = str(it.get("status") or "UNKNOWN").strip() or "UNKNOWN"
        by_status[st] = by_status.get(st, 0) + 1
        item_id = str(it.get("id") or "")
        if item_id:
            seen_ids[item_id] = seen_ids.get(item_id, 0) + 1
            if seen_ids[item_id] == 2:
                duplicates.append({"id": item_id})
        if allowed_statuses and st not in allowed_statuses and st != "UNKNOWN":
            invalid_status.append({"id": it.get("id"), "file": it.get("_file"), "status": st})
        if expected_schema:
            sch = str(it.get("schema") or "")
            if sch and sch != expected_schema:
                invalid_schema.append({"id": it.get("id"), "file": it.get("_file"), "schema": sch})
        dt = _parse_date_yyyy_mm_dd(str(it.get("date") or "").strip())
        if not dt:
            missing_dates.append({"id": it.get("id"), "file": it.get("_file"), "status": st})
            continue
        age_days = (now - dt).days
        if st == stale_status and age_days > stale_days:
            stale.append(
                {
                    "id": it.get("id"),
                    "file": it.get("_file"),
                    "age_days": age_days,
                    "status": st,
                    "date": it.get("date"),
                }
            )
    return {
        "count": len(items),
        "by_status": by_status,
        "stale": stale[:200],
        "missing_dates": missing_dates[:200],
        "invalid_status": invalid_status[:200],
        "invalid_schema": invalid_schema[:200],
        "duplicates": duplicates[:200],
    }


def _cfg_gov_int(cfg: Dict[str, Any], section: str, key: str, default: int) -> int:
    gov = cfg.get("GOVERNANCE") if isinstance(cfg.get("GOVERNANCE"), dict) else {}
    if isinstance(gov, dict):
        sec = gov.get(section)
        if isinstance(sec, dict):
            v = sec.get(key)
            try:
                return int(v)
            except Exception:
                return default
    return default


def backlog_set(backlog_dir: Path, item_id: str, fields: Dict[str, Any]) -> None:
    path = backlog_dir / f"{item_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"Backlog item not found: {path}")
    txt = read_text(path)
    fm = parse_frontmatter(txt)
    if fm is None:
        raise ValueError(f"Missing/invalid frontmatter in {path}")
    for k, v in fields.items():
        fm[k] = v
    new_txt = replace_frontmatter(txt, fm, key_order=BACKLOG_KEY_ORDER)
    path.write_text(new_txt, encoding="utf-8")


def _cfg_schema(cfg: Dict[str, Any], key: str, default: str) -> str:
    sc = cfg.get("SCHEMA") if isinstance(cfg.get("SCHEMA"), dict) else {}
    if isinstance(sc, dict) and isinstance(sc.get(key), str):
        return str(sc.get(key))
    return default


def _cfg_enums(cfg: Dict[str, Any], key: str, default: List[str]) -> List[str]:
    en = cfg.get("ENUMS") if isinstance(cfg.get("ENUMS"), dict) else {}
    if isinstance(en, dict) and isinstance(en.get(key), list):
        vals = [str(x) for x in en.get(key) if isinstance(x, (str, int, float))]
        return vals or default
    return default


def validate_backlog_item(
    cfg: Dict[str, Any], fm: Dict[str, Any], path: Path
) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings) for a single backlog item."""
    errors: List[str] = []
    warnings: List[str] = []
    expected_schema = _cfg_schema(cfg, "backlog_item", "fabric.backlog_item.v1")
    schema = fm.get("schema")
    if str(schema or "").strip() != expected_schema:
        errors.append(f"schema mismatch (expected {expected_schema})")

    # id must match filename stem.
    stem = path.stem
    if not isinstance(fm.get("id"), str) or fm.get("id") != stem:
        errors.append("id mismatch (frontmatter.id must equal filename)")

    # Required core fields.
    for k in [
        "title",
        "type",
        "tier",
        "status",
        "effort",
        "created",
        "updated",
        "source",
        "prio",
        "depends_on",
        "blocked_by",
    ]:
        if k not in fm:
            errors.append(f"missing field: {k}")

    # Enums.
    statuses = set(
        _cfg_enums(
            cfg,
            "statuses",
            ["IDEA", "DESIGN", "READY", "IN_PROGRESS", "IN_REVIEW", "BLOCKED", "DONE"],
        )
    )
    tiers = set(_cfg_enums(cfg, "tiers", ["T0", "T1", "T2", "T3"]))
    types = set(_cfg_enums(cfg, "types", ["Epic", "Story", "Task", "Bug", "Chore", "Spike"]))
    efforts = set(_cfg_enums(cfg, "efforts", ["XS", "S", "M", "L", "XL"]))

    if "status" in fm and str(fm.get("status")) not in statuses:
        errors.append(f"invalid status: {fm.get('status')}")
    if "tier" in fm and str(fm.get("tier")) not in tiers:
        errors.append(f"invalid tier: {fm.get('tier')}")
    if "type" in fm and str(fm.get("type")) not in types:
        errors.append(f"invalid type: {fm.get('type')}")
    if "effort" in fm and str(fm.get("effort")) not in efforts:
        errors.append(f"invalid effort: {fm.get('effort')}")

    # Types.
    try:
        int(fm.get("prio", 0) or 0)
    except Exception:
        errors.append("prio must be int")
    if "depends_on" in fm and not isinstance(fm.get("depends_on"), list):
        errors.append("depends_on must be a list")
    if "blocked_by" in fm and not isinstance(fm.get("blocked_by"), list):
        errors.append("blocked_by must be a list")

    # Optional but recommended nullables.
    for k in ["branch", "review_report", "merge_commit"]:
        if k not in fm:
            warnings.append(f"missing optional field (recommended): {k}")

    return errors, warnings


def normalize_backlog_item_file(
    cfg: Dict[str, Any], path: Path, today: str, dry_run: bool = False
) -> Dict[str, Any]:
    """Normalize backlog item frontmatter deterministically. Returns change summary."""
    txt = read_text(path)
    fm = parse_frontmatter(txt)
    if fm is None:
        raise ValueError(f"Missing/invalid frontmatter in {path}")

    changed = False
    expected_schema = _cfg_schema(cfg, "backlog_item", "fabric.backlog_item.v1")
    if fm.get("schema") != expected_schema:
        fm["schema"] = expected_schema
        changed = True
    # id must equal file stem
    if fm.get("id") != path.stem:
        fm["id"] = path.stem
        changed = True

    # Normalize timestamps
    if not isinstance(fm.get("created"), str) or not fm.get("created"):
        fm["created"] = today
        changed = True
    if not isinstance(fm.get("updated"), str) or not fm.get("updated"):
        fm["updated"] = today
        changed = True

    # Normalize list fields
    for k in ["depends_on", "blocked_by"]:
        if k not in fm or fm.get(k) is None:
            fm[k] = []
            changed = True
        elif not isinstance(fm.get(k), list):
            fm[k] = [str(fm.get(k))]
            changed = True

    # Normalize prio to int
    try:
        prio_int = int(fm.get("prio", 0) or 0)
    except Exception:
        prio_int = 0
    if fm.get("prio") != prio_int:
        fm["prio"] = prio_int
        changed = True

    # Ensure nullable keys exist
    for k in ["branch", "review_report", "merge_commit"]:
        if k not in fm:
            fm[k] = None
            changed = True

    if changed:
        # Always bump updated when we rewrite.
        fm["updated"] = today
        new_txt = replace_frontmatter(txt, fm, key_order=BACKLOG_KEY_ORDER)
        if not dry_run:
            path.write_text(new_txt, encoding="utf-8")

    return {"path": str(path), "changed": changed}


def backlog_create(
    backlog_dir: Path, templates_dir: Path, fields: Dict[str, Any], body: Optional[str] = None
) -> Path:
    """
    Create a new backlog item file deterministically.
    - Uses the body skeleton from a template (epic/story/task) but writes frontmatter from `fields`.
    - Never overwrites existing files.
    """
    item_id = str(fields.get("id") or "")
    if not item_id:
        raise ValueError("backlog.create requires fields.id")
    out_path = backlog_dir / f"{item_id}.md"
    if out_path.exists():
        raise FileExistsError(f"Backlog item already exists: {out_path}")

    item_type = str(fields.get("type") or "Task")
    template_name = "task.md"
    if item_type == "Epic":
        template_name = "epic.md"
    elif item_type == "Story":
        template_name = "story.md"

    tpl_path = templates_dir / template_name
    tpl_txt = read_text(tpl_path) if tpl_path.exists() else ""
    tpl_fm = parse_frontmatter(tpl_txt) or {}
    # Body skeleton = template content after frontmatter
    m = re.match(r"^---\s*\n.*?\n---\s*\n", tpl_txt, flags=re.S)
    skeleton = tpl_txt[m.end() :] if (m and tpl_txt) else "\n\n## Popis\n\n...\n"

    # Merge: template fm provides schema defaults; fields override.
    fm: Dict[str, Any] = dict(tpl_fm)
    fm.update(fields)

    # Normalize common fields
    if "schema" not in fm:
        fm["schema"] = "fabric.backlog_item.v1"
    if "prio" not in fm:
        fm["prio"] = 0

    # Required timestamps (deterministic)
    if not fm.get("created") or ("{" in str(fm.get("created")) and "}" in str(fm.get("created"))):
        fm["created"] = today_date()
    if not fm.get("updated") or ("{" in str(fm.get("updated")) and "}" in str(fm.get("updated"))):
        fm["updated"] = today_date()

    # Order frontmatter
    txt = (
        "---\n"
        + yaml_dump(
            {k: fm.get(k) for k in BACKLOG_KEY_ORDER if k in fm}
            | {k: v for k, v in fm.items() if k not in BACKLOG_KEY_ORDER}
        ).strip("\n")
        + "\n---\n"
    )
    if body is not None:
        txt += body
    else:
        txt += skeleton

    ensure_dir(out_path.parent)
    out_path.write_text(txt, encoding="utf-8")
    return out_path


def state_read(state_path: Path) -> Dict[str, Any]:
    txt = read_text(state_path)
    parsed = parse_yaml_fence(txt)
    if parsed is None:
        raise ValueError("state.md missing valid ```yaml block")
    data, _span = parsed
    return data


def state_patch(state_path: Path, fields: Dict[str, Any]) -> None:
    txt = read_text(state_path)
    parsed = parse_yaml_fence(txt)
    if parsed is None:
        raise ValueError("state.md missing valid ```yaml block")
    data, span = parsed
    for k, v in fields.items():
        data[k] = v
    new_txt = replace_yaml_fence(txt, data, span)
    state_path.write_text(new_txt, encoding="utf-8")


def state_append_history_row(state_path: Path, step: str, result: str, note: str = "") -> None:
    """Append a row to the History table in state.md.

    Best-effort: if the History table isn't found, this is a no-op.
    """
    try:
        txt = read_text(state_path)
    except Exception:
        return

    lines = txt.splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.strip() == "| Date | Step | Result | Note |":
            header_idx = i
            break
    if header_idx is None:
        return
    # Expect separator in next line, then table rows until a non-table line.
    insert_at = None
    for j in range(header_idx + 2, len(lines)):
        if not lines[j].lstrip().startswith("|"):
            insert_at = j
            break
    if insert_at is None:
        insert_at = len(lines)

    safe_note = (note or "").replace("|", "\\|")
    row = f"| {today_date()} | {step} | {result} | {safe_note} |"
    lines.insert(insert_at, row)
    try:
        state_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        return


def run_command(
    repo_root: Path, work_root: Path, cfg: Dict[str, Any], key: str, tail_lines: int
) -> CmdResult:
    commands = cfg.get("COMMANDS") or {}
    if not isinstance(commands, dict):
        raise ValueError("config COMMANDS missing or invalid")
    cmd = commands.get(key)
    if cmd in (None, "", "TBD"):
        return CmdResult(
            ok=False,
            exit_code=127,
            duration_s=0.0,
            log_path=None,
            tail=f"COMMANDS.{key} is not configured: {cmd!r}",
        )

    cmd = str(cmd).strip()
    logs_dir = work_root / "logs" / "commands"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"{key}-{ts}.log"

    env = os.environ.copy()

    # Best-effort Python venv management: if the repo looks like Python (or venv exists),
    # ensure `.venv` and run commands with venv PATH first. This keeps Makefile targets
    # (`pytest`, `ruff`, `python -m ...`) working deterministically.
    try:
        env_cfg = cfg.get("ENV") or {}
        venv_dir = ".venv"
        if isinstance(env_cfg, dict):
            venv_dir = str(env_cfg.get("venv") or env_cfg.get("venv_dir") or venv_dir)
        venv_path = (repo_root / venv_dir) if not Path(venv_dir).is_absolute() else Path(venv_dir)

        paths = get_paths_block(cfg)
        code_root = resolve_rel(repo_root, paths.get("CODE_ROOT", "goden/"))

        dep_root = repo_root
        if not any(
            (repo_root / f).exists()
            for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
        ):
            if any(
                (code_root / f).exists()
                for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
            ):
                dep_root = code_root

        looks_python = any(
            (dep_root / f).exists()
            for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
        )
        if looks_python or venv_path.exists():
            ensure_script = Path(__file__).resolve().parent / "ensure_venv.py"
            ensure_cmd = [
                sys.executable,
                str(ensure_script),
                "--repo-root",
                str(repo_root),
                "--dep-root",
                str(dep_root),
                "--venv",
                str(venv_dir),
                "--json",
            ]
            ensure_proc = subprocess.run(
                ensure_cmd,
                cwd=str(repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            with log_path.open("w", encoding="utf-8") as f:
                f.write("=== ensure_venv ===\n")
                if ensure_proc.stdout:
                    f.write(ensure_proc.stdout.strip() + "\n")
                if ensure_proc.stderr:
                    f.write(ensure_proc.stderr.strip() + "\n")
                f.write("=== command ===\n")

            bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
            if bin_dir.exists():
                env["VIRTUAL_ENV"] = str(venv_path)
                env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        else:
            with log_path.open("w", encoding="utf-8") as f:
                f.write("=== command ===\n")
    except Exception as e:
        with log_path.open("w", encoding="utf-8") as f:
            f.write("=== ensure_venv (error) ===\n")
            f.write(str(e) + "\n")
            f.write("=== command ===\n")

    start = time.time()
    tail: List[str] = []
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    assert proc.stdout is not None
    with log_path.open("a", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line)
            tail.append(line.rstrip("\n"))
            if len(tail) > tail_lines:
                tail.pop(0)
    rc = proc.wait()
    dur = round(time.time() - start, 3)
    return CmdResult(
        ok=(rc == 0), exit_code=rc, duration_s=dur, log_path=str(log_path), tail="\n".join(tail)
    )


def snapshot_status(
    repo_root: Path, cfg: Dict[str, Any], out_path: Path, tail_lines: int
) -> Dict[str, Any]:
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    # snapshot_status is a helper (not a cmd_* wrapper) — no args namespace available.
    _resolve_tier_max(cfg, None, None)
    code_root = resolve_rel(repo_root, paths.get("CODE_ROOT", "goden/"))
    test_root = resolve_rel(repo_root, paths.get("TEST_ROOT", "tests/"))
    docs_root = resolve_rel(repo_root, paths.get("DOCS_ROOT", "docs/"))

    # file extension histogram in code root
    exts: Dict[str, int] = {}
    file_count = 0
    loc = 0
    for p in code_root.rglob("*"):
        if not p.is_file():
            continue
        # ignore vendored node_modules/ etc
        rel = safe_relpath(p, repo_root)
        if "/node_modules/" in rel or "/.venv/" in rel or "/dist/" in rel or "/build/" in rel:
            continue
        file_count += 1
        ext = p.suffix.lower() or "<none>"
        exts[ext] = exts.get(ext, 0) + 1
        try:
            loc += sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
        except Exception:
            pass

    # backlog stats
    backlog_dir = work_root / "backlog"
    items = parse_backlog_items(backlog_dir, include_done=False) if backlog_dir.exists() else []
    bstats = backlog_stats(items)

    # git snapshot (best-effort)
    git = {"is_git": False}
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo_root), text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(repo_root), text=True
        ).strip()
        git = {
            "is_git": True,
            "head": head,
            "branch": branch,
            "dirty": bool(status),
            "porcelain": status.splitlines() if status else [],
        }
    except Exception:
        pass

    # run configured commands (best-effort; do not fail snapshot if commands missing)
    cmd_results: Dict[str, Any] = {}
    for key in ["test", "lint", "format_check"]:
        try:
            res = run_command(repo_root, work_root, cfg, key, tail_lines=tail_lines)
            cmd_results[key] = asdict(res)
        except Exception as e:
            cmd_results[key] = {"ok": False, "error": str(e)}

    snap = {
        "schema": "fabric.snapshot.status.v1",
        "created_at": now_iso_utc(),
        "paths": {
            "work_root": safe_relpath(work_root, repo_root),
            "code_root": safe_relpath(code_root, repo_root),
            "test_root": safe_relpath(test_root, repo_root),
            "docs_root": safe_relpath(docs_root, repo_root),
        },
        "git": git,
        "code": {
            "file_count": file_count,
            "loc": loc,
            "exts_top": sorted(exts.items(), key=lambda kv: (-kv[1], kv[0]))[:10],
        },
        "backlog": bstats,
        "commands": cmd_results,
    }
    write_json(out_path, snap)
    return snap


def apply_plan(repo_root: Path, cfg: Dict[str, Any], plan_path: Path) -> Dict[str, Any]:
    data = yaml_load(read_text(plan_path))
    if not isinstance(data, dict) or data.get("schema") != "fabric.plan.v1":
        raise ValueError("plan schema must be fabric.plan.v1")
    ops = data.get("ops")
    if not isinstance(ops, list):
        raise ValueError("plan.ops must be a list")

    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    # apply_plan is a helper (not a cmd_* wrapper) — no args namespace available.
    _resolve_tier_max(cfg, None, None)
    backlog_dir = work_root / "backlog"
    templates_dir = resolve_rel(
        repo_root,
        paths.get("TEMPLATES_ROOT", f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/templates/"),
    )
    state_path = work_root / "state.md"

    # Placeholder context for deterministic substitution inside plans.
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}
    applied: List[dict] = []
    for op in ops:
        if not isinstance(op, dict) or "op" not in op:
            raise ValueError(f"Invalid op entry: {op!r}")

        # Expand placeholders in all string values, using *current* state.
        ctx = build_ctx(cfg, state)
        op = expand_obj(op, ctx)
        kind = op["op"]

        if kind == "state.patch":
            fields = op.get("fields") or {}
            if not isinstance(fields, dict):
                raise ValueError("state.patch.fields must be dict")
            fields = expand_obj(fields, ctx)
            state_patch(state_path, fields)
            # keep in-memory state aligned for subsequent ops
            try:
                state.update(fields)
            except Exception:
                pass
            applied.append({"op": kind, "fields": list(fields.keys())})

        elif kind == "backlog.set":
            item_id = str(op.get("id") or "")
            if not item_id:
                raise ValueError("backlog.set requires id")
            fields = op.get("fields") or {}
            if not isinstance(fields, dict):
                raise ValueError("backlog.set.fields must be dict")
            fields = expand_obj(fields, ctx)
            backlog_set(backlog_dir, item_id, fields)
            applied.append({"op": kind, "id": item_id, "fields": list(fields.keys())})

        elif kind == "backlog.create":
            fields = op.get("fields") or {}
            if not isinstance(fields, dict):
                raise ValueError("backlog.create.fields must be dict")
            # Allow top-level convenience keys: id/title/type/tier/status/effort/source/prio/depends_on/blocked_by
            for k in [
                "id",
                "title",
                "type",
                "tier",
                "status",
                "effort",
                "source",
                "prio",
                "depends_on",
                "blocked_by",
            ]:
                if k in op and k not in fields:
                    fields[k] = op.get(k)
            fields = expand_obj(fields, ctx)
            created = backlog_create(backlog_dir, templates_dir, fields, body=op.get("body"))
            applied.append(
                {"op": kind, "id": str(fields.get("id")), "path": safe_relpath(created, repo_root)}
            )

        elif kind == "backlog.index":
            items = parse_backlog_items(backlog_dir, include_done=False)
            idx = generate_backlog_index(work_root, items)
            (work_root / "backlog.md").write_text(idx + "\n", encoding="utf-8")
            applied.append({"op": kind, "count": len(items)})

        elif kind == "fs.move":
            src = str(op.get("src") or "")
            dest_dir = str(op.get("dest_dir") or "")
            if not src or not dest_dir:
                raise ValueError("fs.move requires src and dest_dir")
            src_p = (repo_root / src).resolve()
            dest_p = (repo_root / dest_dir).resolve()
            if not is_within(src_p, work_root) or not is_within(dest_p, work_root):
                raise ValueError("fs.move restricted to WORK_ROOT")
            ensure_dir(dest_p)
            target = dest_p / src_p.name
            shutil.move(str(src_p), str(target))
            applied.append(
                {
                    "op": kind,
                    "src": safe_relpath(src_p, repo_root),
                    "dest": safe_relpath(target, repo_root),
                }
            )

        elif kind == "fs.copy":
            src = str(op.get("src") or "")
            dest = str(op.get("dest") or "")
            dest_dir = str(op.get("dest_dir") or "")
            if not src or (not dest and not dest_dir):
                raise ValueError("fs.copy requires src and (dest or dest_dir)")
            src_p = (repo_root / src).resolve()
            if dest:
                dest_p = (repo_root / dest).resolve()
            else:
                ddir = (repo_root / dest_dir).resolve()
                dest_p = ddir / src_p.name
            if not is_within(src_p, work_root) or not is_within(dest_p, work_root):
                raise ValueError("fs.copy restricted to WORK_ROOT")
            ensure_dir(dest_p.parent)
            shutil.copy2(str(src_p), str(dest_p))
            applied.append(
                {
                    "op": kind,
                    "src": safe_relpath(src_p, repo_root),
                    "dest": safe_relpath(dest_p, repo_root),
                }
            )

        elif kind == "report.new":
            # Create a report file from a template with placeholder replacement.
            template = str(op.get("template") or "report.md")
            out = str(op.get("out") or "")
            if not out:
                raise ValueError("report.new requires out path")
            kv = op.get("set") or {}
            if not isinstance(kv, dict):
                raise ValueError("report.new.set must be dict")
            kv = expand_obj(kv, ctx)
            src = templates_dir / template
            if not src.exists():
                raise FileNotFoundError(f"Template not found: {src}")
            txt = read_text(src)
            mapping = build_ctx(cfg, state, extra=kv)
            # Apply mapping only for known placeholders (unknown are kept).
            txt = expand_placeholders(txt, mapping)
            out_p = (repo_root / out).resolve()
            if not is_within(out_p, work_root):
                raise ValueError("report.new output must be within WORK_ROOT")
            ensure_dir(out_p.parent)
            out_p.write_text(txt, encoding="utf-8")
            applied.append(
                {"op": kind, "template": template, "out": safe_relpath(out_p, repo_root)}
            )

        else:
            raise ValueError(f"Unsupported op: {kind}")

    return {"schema": "fabric.plan_result.v1", "applied": applied, "count": len(applied)}


def cmd_bootstrap(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    cfg_path = Path(args.config).resolve() if args.config else None
    summary = ensure_workspace_skeleton(
        repo_root, cfg_path, create_vision_stub=args.create_vision_stub
    )

    # Best-effort venv creation: if the project looks like Python, ensure .venv exists
    # so that subsequent steps (status, gate-test, snapshot-status) can run commands immediately.
    venv_status = "skipped"
    try:
        _cfg_path, cfg = load_config(repo_root, cfg_path)
        env_cfg = cfg.get("ENV") or {}
        venv_dir = ".venv"
        if isinstance(env_cfg, dict):
            venv_dir = str(env_cfg.get("venv") or env_cfg.get("venv_dir") or venv_dir)
        venv_path = (repo_root / venv_dir) if not Path(venv_dir).is_absolute() else Path(venv_dir)

        paths = get_paths_block(cfg)
        code_root = resolve_rel(repo_root, paths.get("CODE_ROOT", "goden/"))

        dep_root = repo_root
        if not any(
            (repo_root / f).exists()
            for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
        ):
            if any(
                (code_root / f).exists()
                for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
            ):
                dep_root = code_root

        looks_python = any(
            (dep_root / f).exists()
            for f in ("pyproject.toml", "requirements.txt", "setup.py", "setup.cfg")
        )
        if looks_python or venv_path.exists():
            ensure_script = Path(__file__).resolve().parent / "ensure_venv.py"
            ensure_cmd = [
                sys.executable,
                str(ensure_script),
                "--repo-root",
                str(repo_root),
                "--dep-root",
                str(dep_root),
                "--venv",
                str(venv_dir),
                "--json",
            ]
            ensure_proc = subprocess.run(
                ensure_cmd,
                cwd=str(repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if ensure_proc.returncode == 0:
                venv_status = "created" if "updated" in (ensure_proc.stdout or "") else "ok"
            else:
                venv_status = f"error (rc={ensure_proc.returncode})"
                if ensure_proc.stderr:
                    venv_status += f": {ensure_proc.stderr.strip()[:200]}"
    except Exception as e:
        venv_status = f"error: {e}"

    summary["venv"] = venv_status

    if args.out_json:
        out = (repo_root / args.out_json).resolve()
        if not is_within(out, repo_root):
            raise ValueError("--out-json must be within repo")
        ensure_dir(out.parent)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def cmd_templates_ensure(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    templates_dir = resolve_rel(repo_root, paths.get("TEMPLATES_ROOT", "fabric/templates/"))
    ensure_dir(templates_dir)
    required = parse_required_templates(cfg)
    copied = copy_missing_templates(templates_dir, required)
    print(
        json.dumps(
            {"copied": copied, "templates_dir": safe_relpath(templates_dir, repo_root)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_backlog_scan(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    items = (
        parse_backlog_items(backlog_dir, include_done=args.include_done)
        if backlog_dir.exists()
        else []
    )
    data = {
        "schema": "fabric.backlog_scan.v1",
        "created_at": now_iso_utc(),
        "count": len(items),
        "items": items,
        "stats": backlog_stats(items),
    }
    if args.json_out:
        out = (repo_root / args.json_out).resolve()
        ensure_dir(out.parent)
        write_json(out, data)
        print(str(out))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_backlog_validate(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    items: List[Tuple[Path, Dict[str, Any]]] = []

    def _collect(dir_path: Path) -> None:
        if not dir_path.exists():
            return
        for p in sorted(dir_path.glob("*.md"), key=lambda x: x.name):
            fm = parse_frontmatter(read_text(p)) or {}
            items.append((p, fm))

    _collect(backlog_dir)
    if args.include_done:
        _collect(backlog_dir / "done")

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    for p, fm in items:
        e, w = validate_backlog_item(cfg, fm, p)
        if e:
            errors.append({"path": safe_relpath(p, repo_root), "errors": e})
        if w:
            warnings.append({"path": safe_relpath(p, repo_root), "warnings": w})

    payload = {
        "schema": "fabric.backlog_validate.v1",
        "created_at": now_iso_utc(),
        "count": len(items),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    strict = bool(args.strict)
    return 0 if not errors and (not strict or not warnings) else 2


def cmd_backlog_normalize(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    today = today_date()

    paths_to_norm: List[Path] = []
    if backlog_dir.exists():
        paths_to_norm.extend(sorted(backlog_dir.glob("*.md"), key=lambda x: x.name))
    if args.include_done:
        done_dir = backlog_dir / "done"
        if done_dir.exists():
            paths_to_norm.extend(sorted(done_dir.glob("*.md"), key=lambda x: x.name))

    changes: List[Dict[str, Any]] = []
    for p in paths_to_norm:
        try:
            changes.append(
                normalize_backlog_item_file(cfg, p, today=today, dry_run=bool(args.dry_run))
            )
        except Exception as e:
            changes.append({"path": safe_relpath(p, repo_root), "changed": False, "error": str(e)})

    payload = {
        "schema": "fabric.backlog_normalize.v1",
        "created_at": now_iso_utc(),
        "count": len(paths_to_norm),
        "dry_run": bool(args.dry_run),
        "changes": changes,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_intake_scan(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    intake_dir = work_root / "intake"
    items = (
        parse_intake_items(intake_dir, include_done=args.include_done)
        if intake_dir.exists()
        else []
    )
    data = {
        "schema": "fabric.intake_scan.v1",
        "created_at": now_iso_utc(),
        "count": len(items),
        "items": items,
    }
    if args.json_out:
        out = (repo_root / args.json_out).resolve()
        ensure_dir(out.parent)
        write_json(out, data)
        print(str(out))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_intake_new(args: argparse.Namespace) -> int:
    """Create a new intake item from template with deterministic placeholder expansion."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    templates_dir = resolve_rel(repo_root, paths.get("TEMPLATES_ROOT", "fabric/templates/"))
    state_path = work_root / "state.md"

    # Optional state for context (wip_item/run_id) but not required.
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    year = datetime.now(timezone.utc).strftime("%Y")
    nnn = _next_intake_seq(work_root, year)

    # Build placeholders.
    extra: Dict[str, Any] = {
        "TITLE": args.title,
        "SOURCE_TYPE": args.source,
        "SUGGESTED_TYPE": args.initial_type,
        "RAW_PRIORITY": args.raw_priority,
        "LINKED_VISION_GOAL": args.vision_goal or "",
        "DETAILED_DESCRIPTION": args.description or "",
        "CONTEXT_INFORMATION": args.context or "",
        "RECOMMENDED_APPROACH": args.recommended or "",
        "AUTHOR_NAME_OR_AGENT": args.author or "fabric-agent",
        "NNN": nnn,
    }

    mapping = build_ctx(cfg, state, extra=extra)

    # Output path.
    if args.out:
        out_rel = expand_placeholders(args.out, mapping)
    else:
        slug = slugify(args.title)
        out_rel = (
            f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/intake/intake-{year}-{nnn}-{slug}.md"
        )
        out_rel = expand_placeholders(out_rel, mapping)
    out_p = (repo_root / out_rel).resolve()
    if not is_within(out_p, work_root):
        raise ValueError("intake-new --out must be within WORK_ROOT")

    tpl = templates_dir / "intake.md"
    if not tpl.exists():
        raise FileNotFoundError(f"Template not found: {tpl}")
    txt = expand_placeholders(read_text(tpl), mapping)
    ensure_dir(out_p.parent)
    out_p.write_text(txt, encoding="utf-8")

    # Extract ID for convenience.
    fm = parse_frontmatter(txt) or {}
    iid = fm.get("id") if isinstance(fm.get("id"), str) else None
    print(
        json.dumps(
            {
                "schema": "fabric.intake_new.v1",
                "written": safe_relpath(out_p, repo_root),
                "id": iid,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_work_status(args: argparse.Namespace) -> int:
    """Return a deterministic classification of whether there is actionable work to do.

    Output status:
    - work: there is pending intake and/or backlog items not DONE/BLOCKED
    - blocked: there is backlog but all items are BLOCKED (no actionable work)
    - none: no pending intake and no actionable backlog items
    """
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    eff_tier_max = _resolve_tier_max(cfg, goal, tier_max)

    backlog_dir = work_root / "backlog"
    intake_dir = work_root / "intake"

    backlog_items = (
        parse_backlog_items(backlog_dir, include_done=False) if backlog_dir.exists() else []
    )
    intake_items = parse_intake_items(intake_dir, include_done=False) if intake_dir.exists() else []

    def _st(it: Dict[str, Any]) -> str:
        return str(it.get("status", "UNKNOWN"))

    def _in_scope(it: Dict[str, Any]) -> bool:
        return _within_tier(it.get("tier"), eff_tier_max)

    total_work = sum(1 for it in backlog_items if _st(it) not in ("DONE", "BLOCKED"))
    total_blocked = sum(1 for it in backlog_items if _st(it) == "BLOCKED")
    total_done = sum(1 for it in backlog_items if _st(it) == "DONE")

    work_count = sum(
        1 for it in backlog_items if _in_scope(it) and _st(it) not in ("DONE", "BLOCKED")
    )
    blocked_count = sum(1 for it in backlog_items if _in_scope(it) and _st(it) == "BLOCKED")
    done_count = sum(1 for it in backlog_items if _in_scope(it) and _st(it) == "DONE")

    # Include a small, deterministic sample of blocked items for reporting / escalation.
    blocked_items_preview: List[Dict[str, Any]] = []
    for it in backlog_items:
        if _st(it) == "BLOCKED":
            if eff_tier_max is not None and not _within_tier(it.get("tier"), eff_tier_max):
                continue
            blocked_items_preview.append(
                {
                    "id": it.get("id"),
                    "title": it.get("title"),
                    "type": it.get("type"),
                    "tier": it.get("tier"),
                    "prio": it.get("prio"),
                    "effort": it.get("effort"),
                    "_path": it.get("_path"),
                }
            )
    blocked_items_preview = blocked_items_preview[:50]

    intake_pending = len(intake_items)

    if intake_pending > 0 or work_count > 0:
        status = "work"
    elif blocked_count > 0:
        status = "blocked"
    else:
        status = "none"

    data = {
        "schema": "fabric.work_status.v1",
        "created_at": now_iso_utc(),
        "status": status,
        "goal": goal,
        "goal_tier_max": eff_tier_max,
        "intake_pending": intake_pending,
        "backlog": {
            "count": len(backlog_items),
            "work": work_count,
            "blocked": blocked_count,
            "done": done_count,
            "totals": {"work": total_work, "blocked": total_blocked, "done": total_done},
            "stats": backlog_stats(backlog_items),
            "blocked_items": blocked_items_preview,
        },
    }

    if args.json_out:
        out = (repo_root / args.json_out).resolve()
        ensure_dir(out.parent)
        write_json(out, data)
        print(str(out))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_backlog_index(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    items = parse_backlog_items(backlog_dir, include_done=False) if backlog_dir.exists() else []
    idx = generate_backlog_index(work_root, items)
    (work_root / "backlog.md").write_text(idx + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"written": safe_relpath(work_root / "backlog.md", repo_root), "count": len(items)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_governance_index(args: argparse.Namespace) -> int:
    """Regenerate decisions/specs/reviews indices deterministically."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)

    work_root_rel = paths.get("WORK_ROOT", "fabric/")
    resolve_rel(repo_root, work_root_rel)

    decisions_root_rel = paths.get("DECISIONS_ROOT", f"{str(work_root_rel).rstrip('/')}/decisions/")
    specs_root_rel = paths.get("SPECS_ROOT", f"{str(work_root_rel).rstrip('/')}/specs/")
    reviews_root_rel = paths.get("REVIEWS_ROOT", f"{str(work_root_rel).rstrip('/')}/reviews/")

    decisions_dir = resolve_rel(repo_root, decisions_root_rel)
    specs_dir = resolve_rel(repo_root, specs_root_rel)
    reviews_dir = resolve_rel(repo_root, reviews_root_rel)

    written: List[str] = []

    kind = args.kind or "all"
    if kind in ("all", "decisions"):
        items = parse_governance_items(decisions_dir)
        txt = generate_governance_index("Decisions (ADR) Index", items)
        out = decisions_dir / "INDEX.md"
        ensure_dir(out.parent)
        out.write_text(txt + "\n", encoding="utf-8")
        written.append(safe_relpath(out, repo_root))

    if kind in ("all", "specs"):
        items = parse_governance_items(specs_dir)
        txt = generate_governance_index("Specs Index", items)
        out = specs_dir / "INDEX.md"
        ensure_dir(out.parent)
        out.write_text(txt + "\n", encoding="utf-8")
        written.append(safe_relpath(out, repo_root))

    if kind in ("all", "reviews"):
        items = parse_governance_items(reviews_dir)
        txt = generate_governance_index("Reviews Index", items)
        out = reviews_dir / "INDEX.md"
        ensure_dir(out.parent)
        out.write_text(txt + "\n", encoding="utf-8")
        written.append(safe_relpath(out, repo_root))

    print(
        json.dumps(
            {"schema": "fabric.governance_index.v1", "written": written},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_governance_scan(args: argparse.Namespace) -> int:
    """Scan decisions/specs for stale items and missing metadata."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)

    work_root_rel = paths.get("WORK_ROOT", "fabric/")
    decisions_root_rel = paths.get("DECISIONS_ROOT", f"{str(work_root_rel).rstrip('/')}/decisions/")
    specs_root_rel = paths.get("SPECS_ROOT", f"{str(work_root_rel).rstrip('/')}/specs/")
    reviews_root_rel = paths.get("REVIEWS_ROOT", f"{str(work_root_rel).rstrip('/')}/reviews/")

    decisions_dir = resolve_rel(repo_root, decisions_root_rel)
    specs_dir = resolve_rel(repo_root, specs_root_rel)
    reviews_dir = resolve_rel(repo_root, reviews_root_rel)

    dec_items = parse_governance_items(decisions_dir)
    spec_items = parse_governance_items(specs_dir)
    rev_items = parse_governance_items(reviews_dir)

    stale_proposed_days = _cfg_gov_int(cfg, "decisions", "stale_proposed_days", 14)
    stale_draft_days = _cfg_gov_int(cfg, "specs", "stale_draft_days", 30)

    out = {
        "schema": "fabric.governance_scan.v1",
        "created_at": now_iso_utc(),
        "decisions": scan_governance(
            dec_items,
            stale_status="proposed",
            stale_days=stale_proposed_days,
            allowed_statuses=(cfg.get("ENUMS", {}) or {}).get("adr_statuses"),
            expected_schema=((cfg.get("SCHEMA", {}) or {}).get("adr") or ""),
        ),
        "specs": scan_governance(
            spec_items,
            stale_status="draft",
            stale_days=stale_draft_days,
            allowed_statuses=(cfg.get("ENUMS", {}) or {}).get("spec_statuses"),
            expected_schema=((cfg.get("SCHEMA", {}) or {}).get("spec") or ""),
        ),
        "reviews": {"count": len(rev_items)},
    }
    if args.json_out:
        out_p = (repo_root / args.json_out).resolve()
        write_json(out_p, out)
        print(str(out_p))
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_review_publish(args: argparse.Namespace) -> int:
    """Publish a report into reviews/ for easier human/agent consumption."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root_rel = paths.get("WORK_ROOT", "fabric/")
    reviews_root_rel = paths.get("REVIEWS_ROOT", f"{str(work_root_rel).rstrip('/')}/reviews/")
    reviews_dir = resolve_rel(repo_root, reviews_root_rel)

    src = (repo_root / args.src).resolve()
    if not src.exists():
        raise FileNotFoundError(f"review-publish: src not found: {src}")
    ensure_dir(reviews_dir)
    dest = reviews_dir / src.name
    shutil.copy2(src, dest)
    # update index deterministically
    items = parse_governance_items(reviews_dir)
    idx = generate_governance_index("Reviews Index", items)
    (reviews_dir / "INDEX.md").write_text(idx + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": "fabric.review_publish.v1",
                "src": safe_relpath(src, repo_root),
                "dest": safe_relpath(dest, repo_root),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_backlog_set(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    state_path = work_root / "state.md"
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}
    ctx = build_ctx(cfg, state)
    fields = json.loads(args.fields_json)
    if not isinstance(fields, dict):
        raise ValueError("--fields-json must be a JSON object")
    fields = expand_obj(fields, ctx)
    backlog_set(backlog_dir, args.id, fields)
    print(
        json.dumps(
            {"updated": args.id, "fields": list(fields.keys())}, indent=2, ensure_ascii=False
        )
    )
    return 0


def cmd_state_read(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"
    data = state_read(state_path)
    if hasattr(args, "field") and args.field:
        val = data.get(args.field)
        print(json.dumps(val) if not isinstance(val, str) else val)
        return 0
    if args.json_out:
        out = (repo_root / args.json_out).resolve()
        write_json(out, data)
        print(str(out))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_state_patch(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}
    ctx = build_ctx(cfg, state)
    fields = json.loads(args.fields_json)
    if not isinstance(fields, dict):
        raise ValueError("--fields-json must be a JSON object")
    fields = expand_obj(fields, ctx)
    state_patch(state_path, fields)
    print(
        json.dumps(
            {"patched": safe_relpath(state_path, repo_root), "fields": list(fields.keys())},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    res = run_command(repo_root, work_root, cfg, args.key, tail_lines=args.tail)
    out = asdict(res)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if res.tail:
        print("\n--- tail ---\n" + res.tail)
    return 0 if res.exit_code == 0 else res.exit_code


def cmd_gate_test(args: argparse.Namespace) -> int:
    """Deterministic test gate.

    Runs COMMANDS.test, captures logs, and writes a parsable test report:
      - must contain `- Result: PASS` or `- Result: FAIL`

    This is designed to remove brittle, manual report creation from LLM-driven flows.
    """
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    templates_dir = resolve_rel(repo_root, paths.get("TEMPLATES_ROOT", "fabric/templates/"))
    state_path = work_root / "state.md"

    # State required for correlation (wip_item + run_id).
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    wip_item = (
        state.get("wip_item")
        if isinstance(state.get("wip_item"), str) and state.get("wip_item")
        else None
    )
    if not wip_item:
        print(
            json.dumps(
                {"schema": "fabric.gate_test.v1", "ok": False, "error": "missing state.wip_item"},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    run_id = (
        state.get("run_id")
        if isinstance(state.get("run_id"), str) and state.get("run_id")
        else None
    )
    if not run_id:
        run_id = generate_run_id()
        try:
            state_patch(state_path, {"run_id": run_id})
        except Exception:
            # If state can't be patched, still proceed but mark NO-RUN.
            run_id = "NO-RUN"
        state["run_id"] = run_id

    # Run tests deterministically.
    res = run_command(repo_root, work_root, cfg, "test", tail_lines=int(args.tail))
    result = "PASS" if res.ok else "FAIL"
    status = "OK" if res.ok else "ERROR"

    # Write report from template.
    year = datetime.now(timezone.utc).strftime("%Y")
    extra: Dict[str, Any] = {
        "SKILL_NAME": "fabric-test",
        "STEP": "test",
        "KIND": "test",
        "STATUS": status,
        "RESULT": result,
        "TEST_COMMAND": str((cfg.get("COMMANDS") or {}).get("test")),
        "LOG_PATH": str(res.log_path or ""),
        "DURATION_S": f"{res.duration_s:.3f}",
        "NNN": _next_report_seq(work_root, year),
    }
    mapping = build_ctx(cfg, state, extra=extra)

    out_rel = f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/reports/test-{wip_item}-{{YYYY-MM-DD}}-{run_id}.md"
    out_rel = expand_placeholders(out_rel, mapping)
    out_p = (repo_root / out_rel).resolve()
    if not is_within(out_p, work_root):
        raise ValueError("gate-test: output path must be within WORK_ROOT")

    tpl = templates_dir / "test-report.md"
    if not tpl.exists():
        raise FileNotFoundError(f"gate-test: missing template {tpl}")
    txt = expand_placeholders(read_text(tpl), mapping)
    ensure_dir(out_p.parent)
    out_p.write_text(txt, encoding="utf-8")
    try:
        _register_report(repo_root, work_root, out_p)
    except Exception:
        pass

    payload = {
        "schema": "fabric.gate_test.v1",
        "created_at": now_iso_utc(),
        "ok": bool(res.ok),
        "result": result,
        "exit_code": res.exit_code,
        "duration_s": res.duration_s,
        "log_path": safe_relpath(Path(res.log_path), repo_root) if res.log_path else None,
        "report": safe_relpath(out_p, repo_root),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if res.tail:
        print("\n--- tail ---\n" + res.tail)
    return 0 if res.ok else 2


def cmd_snapshot_status(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    out = (repo_root / args.out).resolve()
    snap = snapshot_status(repo_root, cfg, out, tail_lines=args.tail)
    print(
        json.dumps(
            {"written": safe_relpath(out, repo_root), "schema": snap.get("schema")},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    plan_path = (repo_root / args.plan).resolve()
    result = apply_plan(repo_root, cfg, plan_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _next_report_seq(work_root: Path, year: str) -> str:
    """Return next 3-digit sequence for *-{YYYY}-{NNN} by scanning report frontmatter.

    Why: we use multiple report id prefixes (REPORT/TEST/REVIEW/...), but we still want
    a single monotonic sequence per year to avoid collisions.
    """
    reports_dir = work_root / "reports"
    if not reports_dir.exists():
        return "001"
    pat = re.compile(rf"^[A-Za-z0-9_.]+-{re.escape(year)}-(\d{{3}})$")
    max_n = 0
    for p in reports_dir.glob("*.md"):
        try:
            fm = parse_frontmatter(read_text(p)) or {}
        except Exception:
            continue
        rid = fm.get("id")
        if not isinstance(rid, str):
            continue
        m = pat.match(rid.strip())
        if not m:
            continue
        try:
            n = int(m.group(1))
            max_n = max(max_n, n)
        except Exception:
            continue
    return f"{max_n + 1:03d}"


def _next_intake_seq(work_root: Path, year: str) -> str:
    """Return next 3-digit sequence for INTAKE-{YYYY}-{NNN} by scanning intake/* frontmatter."""
    intake_dir = work_root / "intake"
    if not intake_dir.exists():
        return "001"
    pat = re.compile(rf"^INTAKE-{re.escape(year)}-(\d{{3}})$")
    max_n = 0
    for p in intake_dir.glob("*.md"):
        try:
            fm = parse_frontmatter(read_text(p)) or {}
        except Exception:
            continue
        iid = fm.get("id")
        if not isinstance(iid, str):
            continue
        m = pat.match(iid.strip())
        if not m:
            continue
        try:
            n = int(m.group(1))
            max_n = max(max_n, n)
        except Exception:
            continue
    return f"{max_n + 1:03d}"


def cmd_run_start(args: argparse.Namespace) -> int:
    """Start a new Fabric RUN: set run_id + clear transient error fields."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"

    run_id = generate_run_id()
    fields: Dict[str, Any] = {
        "run_id": run_id,
        "error": None,
        "last_run": today_date(),
    }
    # Optional: caller can force step/phase reset
    if args.step is not None:
        fields["step"] = args.step
    if args.phase is not None:
        fields["phase"] = args.phase

    state_patch(state_path, fields)
    print(
        json.dumps(
            {"run_id": run_id, "patched": safe_relpath(state_path, repo_root)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_report_new(args: argparse.Namespace) -> int:
    """Create a report file from a template with deterministic placeholder expansion."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    templates_dir = resolve_rel(repo_root, paths.get("TEMPLATES_ROOT", "fabric/templates/"))
    state_path = work_root / "state.md"

    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    # Ensure run_id exists if requested.
    if args.ensure_run_id and not state.get("run_id"):
        run_id = generate_run_id()
        state_patch(state_path, {"run_id": run_id})
        state["run_id"] = run_id

    # Build extra variables.
    extra: Dict[str, Any] = {}
    if args.set_json:
        extra_raw = json.loads(args.set_json)
        if not isinstance(extra_raw, dict):
            raise ValueError("--set-json must be a JSON object")
        extra.update(extra_raw)
    extra["SKILL_NAME"] = args.skill or "unknown-skill"
    if args.phase:
        extra["PHASE"] = args.phase
    if args.step:
        extra["STEP"] = args.step
    extra["STATUS"] = args.status or "OK"

    # Report sequence (optional; used by report.md template)
    year = datetime.now(timezone.utc).strftime("%Y")
    extra.setdefault("NNN", _next_report_seq(work_root, year))

    # Logical kind (used for indexing & filenames). Defaults to step.
    step = args.step or (state.get("step") if isinstance(state.get("step"), str) else "report")
    kind = (getattr(args, "kind", None) or step) if isinstance(step, str) else "report"
    extra["KIND"] = kind

    # Auto out path if omitted: stable prefix by kind + optional item/sprint + run_id.
    out_rel = args.out
    if not out_rel:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
        run_id = (
            state.get("run_id")
            if isinstance(state.get("run_id"), str) and state.get("run_id")
            else "NO-RUN"
        )
        wip_item = (
            state.get("wip_item")
            if isinstance(state.get("wip_item"), str) and state.get("wip_item")
            else None
        )
        sprint = state.get("sprint")
        if wip_item:
            fname = f"{kind}-{wip_item}-{stamp}-{run_id}.md"
        elif sprint is not None:
            fname = f"{kind}-s{str(sprint)}-{stamp}-{run_id}.md"
        else:
            fname = f"{kind}-{stamp}-{run_id}.md"
        out_rel = f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/reports/{fname}"

    # Expand placeholders in output path.
    mapping_for_path = build_ctx(cfg, state, extra=extra)
    out_rel = expand_placeholders(out_rel, mapping_for_path)
    out_p = (repo_root / out_rel).resolve()
    if not is_within(out_p, work_root):
        raise ValueError("report-new --out must be within WORK_ROOT")

    template_name = args.template or "report.md"
    src = templates_dir / template_name
    if not src.exists():
        raise FileNotFoundError(f"Template not found: {src}")
    txt = read_text(src)

    mapping = build_ctx(cfg, state, extra=extra)
    txt = expand_placeholders(txt, mapping)

    ensure_dir(out_p.parent)
    out_p.write_text(txt, encoding="utf-8")

    # Register in a lightweight append-only registry for deterministic retrieval.
    try:
        _register_report(repo_root, work_root, out_p)
    except Exception:
        # Registry is non-critical; do not fail report creation.
        pass

    print(
        json.dumps(
            {"written": safe_relpath(out_p, repo_root), "template": template_name, "kind": kind},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


# ----------------------------
# Report registry + retrieval
# ----------------------------

REPORT_REGISTRY_SCHEMA = "fabric.report_registry.v1"
REPORT_ENTRY_SCHEMA = "fabric.report_entry.v1"


def _parse_dt(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    s = value.strip()
    # Accept ISO date or ISO datetime (Z).
    try:
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return datetime.fromisoformat(s + "T00:00:00+00:00")
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        # fromisoformat supports offset.
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _infer_kind_from_name(name: str) -> str:
    base = name.strip().lower()
    # Heuristic: prefix before first dash.
    if "-" in base:
        return base.split("-", 1)[0]
    return base.rsplit(".", 1)[0]


def _is_placeholder_str(s: Optional[str]) -> bool:
    if not isinstance(s, str):
        return False
    t = s.strip()
    return "{" in t and "}" in t


def _infer_item_id_from_filename(kind: str, filename: str) -> Optional[str]:
    """Infer item id from common report naming conventions.

    Supported examples:
      - test-TASK-123-2026-03-02.md
      - review-TASK-123-20260302-120000Z-RUN-....md
    """
    base = filename
    if base.lower().endswith(".md"):
        base = base[:-3]
    prefix = kind.lower() + "-"
    if not base.lower().startswith(prefix):
        return None
    rest = base[len(prefix) :]
    # date suffix
    m = re.match(r"^(?P<item>.+)-(?P<date>\d{4}-\d{2}-\d{2})(?:-.*)?$", rest)
    if m:
        return m.group("item")
    # stamp suffix
    m2 = re.match(r"^(?P<item>.+)-(?P<stamp>\d{8}-\d{6}Z)(?:-.*)?$", rest)
    if m2:
        return m2.group("item")
    return None


def _sha256_text(txt: str) -> str:
    import hashlib

    return hashlib.sha256(txt.encode("utf-8", errors="ignore")).hexdigest()


def _report_entry_from_file(repo_root: Path, work_root: Path, p: Path) -> Optional[Dict[str, Any]]:
    if not p.is_file() or p.suffix.lower() != ".md":
        return None
    txt = read_text(p)
    fm = parse_frontmatter(txt) or {}

    # Note: reports without frontmatter are still indexed (kind inferred from filename),
    # but `reports-validate` can flag them.

    created_at = _parse_dt(fm.get("created_at")) or _parse_dt(fm.get("date"))
    if created_at is None:
        try:
            created_at = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        except Exception:
            created_at = datetime.now(timezone.utc)

    kind = fm.get("kind") if isinstance(fm.get("kind"), str) else None
    step = fm.get("step") if isinstance(fm.get("step"), str) else None
    if _is_placeholder_str(kind):
        kind = None
    if _is_placeholder_str(step):
        step = None
    if not kind:
        kind = step or _infer_kind_from_name(p.name)

    # Common correlation fields.
    run_id = fm.get("run_id") if isinstance(fm.get("run_id"), str) else None
    item_id = fm.get("item_id") if isinstance(fm.get("item_id"), str) else None
    if not item_id:
        # try common alternates
        for k in ["wip_item", "id", "backlog_id"]:
            v = fm.get(k)
            if isinstance(v, str) and v.strip():
                item_id = v.strip()
                break

    if _is_placeholder_str(item_id):
        item_id = None
    if not item_id and isinstance(kind, str):
        item_id = _infer_item_id_from_filename(kind, p.name)

    sprint = fm.get("sprint")
    if isinstance(sprint, (int, float)):
        sprint_val: Optional[str] = str(int(sprint))
    elif isinstance(sprint, str) and sprint.strip():
        sprint_val = sprint.strip()
    else:
        sprint_val = None

    rel = safe_relpath(p, repo_root)
    entry: Dict[str, Any] = {
        "schema": REPORT_ENTRY_SCHEMA,
        "path": rel,
        "kind": kind,
        "step": step,
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "item_id": item_id,
        "sprint": sprint_val,
        "sha256": _sha256_text(txt),
    }
    return entry


def _scan_reports(
    repo_root: Path, work_root: Path, include_archive: bool = False
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    report_dirs = [work_root / "reports"]
    if include_archive:
        report_dirs.append(work_root / "archive" / "reports")

    for d in report_dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md"), key=lambda x: str(x)):
            # Skip internal registry/index artifacts.
            if p.name in ("registry.jsonl", "report-index.json"):
                continue
            e = _report_entry_from_file(repo_root, work_root, p)
            if e:
                entries.append(e)

    # Sort deterministically by created_at then path.
    def _dt_key(e: Dict[str, Any]) -> str:
        return str(e.get("created_at") or "")

    entries.sort(key=lambda e: (_dt_key(e), str(e.get("path"))))
    return entries


def _registry_path(work_root: Path) -> Path:
    return work_root / "reports" / "registry.jsonl"


def _register_report(repo_root: Path, work_root: Path, report_path: Path) -> None:
    entry = _report_entry_from_file(repo_root, work_root, report_path)
    if not entry:
        return
    reg = _registry_path(work_root)
    ensure_dir(reg.parent)
    with reg.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cmd_report_index(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)

    entries = _scan_reports(repo_root, work_root, include_archive=args.include_archive)
    out = (
        (work_root / "reports" / "report-index.json")
        if not args.out
        else (repo_root / args.out).resolve()
    )
    if not is_within(out, repo_root):
        raise ValueError("report-index --out must be within repo")
    payload = {
        "schema": REPORT_REGISTRY_SCHEMA,
        "created_at": now_iso_utc(),
        "count": len(entries),
        "entries": entries,
    }
    write_json(out, payload)
    print(
        json.dumps(
            {"written": safe_relpath(out, repo_root), "count": len(entries)},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def _latest_report(
    entries: List[Dict[str, Any]],
    kind: str,
    item_id: Optional[str] = None,
    run_id: Optional[str] = None,
    sprint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    kind_l = kind.strip().lower()
    filtered: List[Dict[str, Any]] = []
    for e in entries:
        ek = str(e.get("kind", "")).lower()
        if ek != kind_l:
            continue
        if item_id and str(e.get("item_id") or "") != item_id:
            continue
        if run_id and str(e.get("run_id") or "") != run_id:
            continue
        if sprint and str(e.get("sprint") or "") != sprint:
            continue
        filtered.append(e)
    if not filtered:
        return None
    # entries already sorted ascending; latest is last.
    return filtered[-1]


def _parse_test_result(md: str) -> Optional[str]:
    m = re.search(r"^\s*-\s*Result\s*:\s*(PASS|FAIL|SKIPPED|UNKNOWN)\b", md, flags=re.I | re.M)
    if m:
        return m.group(1).upper()
    m2 = re.search(
        r"\b(?:Result|Verdict)\s*[:=]\s*\*{0,2}(PASS|FAIL|SKIPPED|UNKNOWN)\b", md, flags=re.I
    )
    if m2:
        return m2.group(1).upper()
    # Fallback: check YAML frontmatter fields
    fm = parse_frontmatter(md) or {}
    for key in ("result", "status", "verdict", "test_result"):
        v = fm.get(key)
        if isinstance(v, str) and v.strip().upper() in ("PASS", "FAIL", "SKIPPED", "UNKNOWN"):
            return v.strip().upper()
    return None


def _parse_review_verdict(md: str) -> Optional[str]:
    fm = parse_frontmatter(md) or {}
    for key in ("verdict", "result"):
        v = fm.get(key)
        if isinstance(v, str) and v.strip().upper() in ("CLEAN", "REWORK", "REDESIGN"):
            return v.strip().upper()
    m = re.search(
        r"^\s*\*{0,2}Verdict\*{0,2}\s*:\s*\*{0,2}(CLEAN|REWORK|REDESIGN)\b", md, flags=re.I | re.M
    )
    if m:
        return m.group(1).upper()
    m2 = re.search(r"Verdict\s*[:=]\s*\*{0,2}(CLEAN|REWORK|REDESIGN)\b", md, flags=re.I)
    if m2:
        return m2.group(1).upper()
    return None


def cmd_report_latest(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)

    entries = _scan_reports(repo_root, work_root, include_archive=args.include_archive)
    latest = _latest_report(
        entries, kind=args.kind, item_id=args.item_id, run_id=args.run_id, sprint=args.sprint
    )
    if not latest:
        print(
            json.dumps(
                {"schema": "fabric.report_latest.v1", "found": False, "kind": args.kind},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    # Optional parsed semantic signals for gating.
    parsed: Dict[str, Any] = {}
    p = (repo_root / str(latest["path"])).resolve()
    try:
        md = read_text(p)
        if str(latest.get("kind", "")).lower() == "test":
            parsed["test_result"] = _parse_test_result(md)
        if str(latest.get("kind", "")).lower() == "review":
            parsed["review_verdict"] = _parse_review_verdict(md)
    except Exception:
        pass

    payload = {
        "schema": "fabric.report_latest.v1",
        "found": True,
        "entry": latest,
        "parsed": parsed,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_reports_validate(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)

    schema_reports = (
        (cfg.get("SCHEMA") or {}).get("reports") if isinstance(cfg.get("SCHEMA"), dict) else None
    ) or "fabric.report.v1"
    strict = bool(args.strict)
    entries = _scan_reports(repo_root, work_root, include_archive=args.include_archive)
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for e in entries:
        p = (repo_root / str(e.get("path"))).resolve()
        md = read_text(p)
        fm = parse_frontmatter(md)
        if fm is None:
            msg = "missing or invalid YAML frontmatter"
            (errors if strict else warnings).append({"path": e.get("path"), "issue": msg})
            continue
        actual_schema = str(fm.get("schema") or "").strip()
        valid_schemas = {schema_reports, "fabric.audit.v1"}
        if actual_schema not in valid_schemas:
            errors.append(
                {
                    "path": e.get("path"),
                    "issue": f"schema mismatch: expected {schema_reports} or fabric.audit.v1",
                    "schema": fm.get("schema"),
                }
            )
        if not fm.get("created_at") and not fm.get("date"):
            (errors if strict else warnings).append(
                {"path": e.get("path"), "issue": "missing created_at or date"}
            )
        else:
            dt_val = fm.get("created_at") or fm.get("date")
            if _parse_dt(dt_val) is None:
                errors.append({"path": e.get("path"), "issue": "created_at/date not ISO"})
        if not (fm.get("kind") or fm.get("step")):
            (errors if strict else warnings).append(
                {"path": e.get("path"), "issue": "missing kind/step"}
            )
        elif not fm.get("kind"):
            warnings.append({"path": e.get("path"), "issue": "missing kind (has step)"})
        elif not fm.get("step"):
            warnings.append({"path": e.get("path"), "issue": "missing step (has kind)"})

        k = str(e.get("kind") or "").lower()
        if k == "test":
            if _parse_test_result(md) is None:
                (errors if strict else warnings).append(
                    {"path": e.get("path"), "issue": "test report missing Result: PASS|FAIL"}
                )
        if k == "review":
            if _parse_review_verdict(md) is None:
                (errors if strict else warnings).append(
                    {"path": e.get("path"), "issue": "review report missing verdict"}
                )

    payload = {
        "schema": "fabric.reports_validate.v1",
        "created_at": now_iso_utc(),
        "count": len(entries),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors and (not strict or not warnings) else 2


# ----------------------------
# Contracts (deterministic IO checks)
# ----------------------------


def _default_contract_outputs() -> Dict[str, List[str]]:
    """Default post-step output contracts.

    These are intentionally conservative (existence checks only).
    Projects can override/extend via config CONTRACTS.outputs.
    """
    return {
        "vision": ["reports/vision-*.md"],
        "status": ["reports/status-*.md"],
        "architect": ["reports/architect-*.md"],
        "gap": ["reports/gap-*.md"],
        "generate": ["reports/generate-*.md"],
        "intake": ["reports/intake-*.md"],
        "prio": ["reports/prio-*.md", "backlog.md"],
        "sprint": ["sprints/sprint-*.md", "reports/sprint-*.md"],
        "analyze": ["reports/analyze-*.md"],
        "implement": ["reports/implement-*.md"],
        "test": ["reports/test-*.md"],
        "review": ["reports/review-*.md"],
        "close": ["reports/close-*.md"],
        "docs": ["reports/docs-*.md"],
        "check": ["reports/check-*.md"],
        "archive": ["reports/archive-*.md"],
    }


def cmd_contract_check(args: argparse.Namespace) -> int:
    """Validate deterministic file-level contracts for a given step."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    step = str(args.step).strip().lower()

    outputs = _default_contract_outputs()
    cfg_contracts = cfg.get("CONTRACTS") if isinstance(cfg.get("CONTRACTS"), dict) else None
    if isinstance(cfg_contracts, dict):
        co = cfg_contracts.get("outputs")
        if isinstance(co, dict):
            # Override/extend.
            for k, v in co.items():
                if isinstance(v, list):
                    outputs[str(k).strip().lower()] = [str(x) for x in v]

    patterns = outputs.get(step)
    if not patterns:
        print(
            json.dumps(
                {
                    "schema": "fabric.contract_check.v1",
                    "ok": False,
                    "error": f"unknown step: {step}",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    ctx = build_ctx(cfg, state)
    matched: Dict[str, List[str]] = {}
    missing: List[str] = []
    for pat in patterns:
        # Expand any placeholders in patterns.
        pat2 = expand_placeholders(str(pat), ctx)
        # Glob relative to work_root.
        hits = sorted(
            [safe_relpath(p, repo_root) for p in (work_root / pat2).parent.glob(Path(pat2).name)]
        )
        if hits:
            matched[pat2] = hits
        else:
            missing.append(pat2)

    ok = len(missing) == 0
    payload = {
        "schema": "fabric.contract_check.v1",
        "created_at": now_iso_utc(),
        "step": step,
        "ok": ok,
        "missing": missing,
        "matched": matched,
    }

    # Flight recorder
    try:
        logs_root = resolve_rel(
            repo_root,
            paths.get("LOGS_ROOT", str(paths.get("WORK_ROOT", "fabric/")).rstrip("/") + "/logs/"),
        )
    except Exception:
        logs_root = work_root / "logs"
    append_jsonl(logs_root / "contract-check.jsonl", payload)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 2


def cmd_run_report(args: argparse.Namespace) -> int:
    """Append deterministic entries to the per-run run report.

    The run report is a human-readable timeline anchored by state.run_id.
    It complements protocol.jsonl/ticks.jsonl.
    """
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"

    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    run_id = (
        state.get("run_id")
        if isinstance(state.get("run_id"), str) and state.get("run_id")
        else None
    )
    if not run_id and args.ensure_run_id:
        run_id = generate_run_id()
        try:
            state_patch(state_path, {"run_id": run_id})
        except Exception:
            pass
        state["run_id"] = run_id
    if not run_id:
        print(
            json.dumps(
                {"schema": "fabric.run_report.v1", "ok": False, "error": "missing state.run_id"},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    out_rel = args.out
    if not out_rel:
        out_rel = f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/reports/run-{run_id}.md"
    out_p = (repo_root / out_rel).resolve()
    if not is_within(out_p, work_root):
        raise ValueError("run-report --out must be within WORK_ROOT")

    created = False
    if not out_p.exists():
        # Create a minimal run report skeleton.
        year = datetime.now(timezone.utc).strftime("%Y")
        nnn = _next_report_seq(work_root, year)
        header = {
            "id": f"RUNREPORT-{year}-{nnn}",
            "schema": (
                (cfg.get("SCHEMA") or {}).get("reports")
                if isinstance(cfg.get("SCHEMA"), dict)
                else None
            )
            or "fabric.report.v1",
            "date": today_date(),
            "created_at": now_iso_utc(),
            "kind": "run",
            "step": "loop",
            "skill": "fabric-loop",
            "run_id": run_id,
            "status": "OK",
        }
        txt = "---\n" + yaml_dump(header).strip("\n") + "\n---\n\n" + f"# Run — {run_id}\n\n"
        txt += "## Summary\n\n- Trigger: \n- Goal: \n\n"
        txt += "## Inputs\n\n- state.md\n- config.md\n\n"
        txt += "## Timeline\n\n| ts | step | status | report | note |\n|---|---|---|---|---|\n"
        ensure_dir(out_p.parent)
        out_p.write_text(txt, encoding="utf-8")
        created = True
        try:
            _register_report(repo_root, work_root, out_p)
        except Exception:
            pass

    # Append entry if requested.
    appended = False
    if args.completed:
        step = str(args.completed).strip().lower()
        status = (args.status or "OK").strip().upper()
        note = (args.note or "").replace("|", "\\|")

        # Find latest report for this step (by kind) unless explicit.
        report_path = args.report
        if not report_path:
            try:
                entries = _scan_reports(repo_root, work_root, include_archive=False)
                latest = _latest_report(entries, kind=step)
                report_path = latest.get("path") if latest else ""
            except Exception:
                report_path = ""

        row = f"| {now_iso_utc()} | {step} | {status} | {report_path or ''} | {note} |"
        append_md(out_p, row)
        appended = True

    payload = {
        "schema": "fabric.run_report.v1",
        "created_at": now_iso_utc(),
        "ok": True,
        "written": safe_relpath(out_p, repo_root),
        "created": created,
        "appended": appended,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_evidence_pack(args: argparse.Namespace) -> int:
    """Create a deterministic evidence ZIP for debugging/escalation.

    Includes a curated subset of workspace files (state/config/recent logs/reports).
    """
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)

    # Load state for context.
    state_path = work_root / "state.md"
    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}

    run_id = state.get("run_id") if isinstance(state.get("run_id"), str) else None
    wip_item = state.get("wip_item") if isinstance(state.get("wip_item"), str) else None
    sprint = state.get("sprint")
    sprint_str = str(sprint) if sprint is not None else None

    label = slugify(args.label or "evidence")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_rel = args.out
    if not out_rel:
        rid = run_id or "NO-RUN"
        out_rel = f"{paths.get('WORK_ROOT', 'fabric/').rstrip('/')}/reports/evidence-{label}-{stamp}-{rid}.zip"
    out_p = (repo_root / out_rel).resolve()
    if not is_within(out_p, work_root):
        raise ValueError("evidence-pack --out must be within WORK_ROOT")

    # Collect candidates.
    include: List[Path] = []

    def _add(p: Path) -> None:
        if p.exists() and p.is_file() and is_within(p, repo_root):
            include.append(p)

    _add(work_root / "config.md")
    _add(work_root / "state.md")
    _add(work_root / "vision.md")
    _add(work_root / "backlog.md")

    if sprint_str:
        _add(work_root / "sprints" / f"sprint-{sprint_str}.md")

    if wip_item:
        _add(work_root / "backlog" / f"{wip_item}.md")

    # Run report if exists.
    if run_id:
        _add(work_root / "reports" / f"run-{run_id}.md")

    # Latest reports for this run/wip.
    try:
        entries = _scan_reports(repo_root, work_root, include_archive=False)
        for kind in [
            "vision",
            "status",
            "architect",
            "gap",
            "generate",
            "intake",
            "prio",
            "sprint",
            "analyze",
            "implement",
            "test",
            "review",
            "close",
            "docs",
            "check",
            "archive",
        ]:
            rep = (
                _latest_report(entries, kind=kind, item_id=wip_item)
                if wip_item
                else _latest_report(entries, kind=kind)
            )
            if rep and isinstance(rep.get("path"), str):
                _add((repo_root / rep["path"]).resolve())
    except Exception:
        pass

    # Logs: protocol/ticks + last N command logs.
    logs_root = work_root / "logs"
    _add(logs_root / "protocol.jsonl")
    _add(logs_root / "protocol.md")
    _add(logs_root / "ticks.jsonl")
    _add(logs_root / "ticks.md")
    _add(logs_root / "contract-check.jsonl")
    cmds_dir = logs_root / "commands"
    if cmds_dir.exists():
        logs = [p for p in cmds_dir.glob("*.log") if p.is_file()]
        logs.sort(key=lambda p: p.stat().st_mtime)
        for p in logs[-int(args.max_command_logs) :]:
            _add(p)

    # De-dup while preserving order.
    seen = set()
    uniq: List[Path] = []
    for p in include:
        rp = str(p)
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)

    ensure_dir(out_p.parent)
    included_rel: List[str] = []
    with zipfile.ZipFile(out_p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in uniq:
            arc = safe_relpath(p, repo_root)
            z.write(p, arcname=arc)
            included_rel.append(arc)

    payload = {
        "schema": "fabric.evidence_pack.v1",
        "created_at": now_iso_utc(),
        "written": safe_relpath(out_p, repo_root),
        "count": len(included_rel),
        "files": included_rel,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


# ----------------------------
# Deterministic tick engine
# ----------------------------


def _lifecycle_sections(cfg: Dict[str, Any]) -> Dict[str, List[str]]:
    lc = cfg.get("LIFECYCLE") if isinstance(cfg.get("LIFECYCLE"), dict) else {}
    out: Dict[str, List[str]] = {}
    if isinstance(lc, dict):
        for sec in ["orientation", "planning", "implementation", "closing"]:
            v = lc.get(sec)
            if isinstance(v, list):
                out[sec] = [str(x) for x in v]
    return out


def _flatten_lifecycle(cfg: Dict[str, Any]) -> List[str]:
    sec = _lifecycle_sections(cfg)
    seq: List[str] = []
    for k in ["orientation", "planning", "implementation", "closing"]:
        seq.extend(sec.get(k, []))
    return seq


def _phase_for_step(cfg: Dict[str, Any], step: str) -> str:
    sec = _lifecycle_sections(cfg)
    for phase, steps in sec.items():
        if step in steps:
            return phase
    return "unknown"


def _default_next_step(cfg: Dict[str, Any], step: str) -> str:
    seq = _flatten_lifecycle(cfg)
    if not seq:
        return step
    if step not in seq:
        return seq[0]
    i = seq.index(step)
    return seq[(i + 1) % len(seq)]


_TIER_RE = re.compile(r"^T(\d+)$", re.IGNORECASE)


def _tier_num(tier: Any) -> Optional[int]:
    """Parse tier string like T0/T1... into integer. Unknown/None -> None."""
    if tier is None:
        return None
    if isinstance(tier, (int, float)):
        return int(tier)
    s = str(tier).strip()
    m = _TIER_RE.match(s)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _within_tier(tier: Any, tier_max: Optional[str]) -> bool:
    """Return True if `tier` is within tier_max. If tier_max is None, always True.

    Safety rule: unknown tier counts as within scope (so we don't silently ignore work).
    """
    if tier_max is None:
        return True
    max_n = _tier_num(tier_max)
    if max_n is None:
        # If tier_max itself is invalid, treat as no filter.
        return True
    n = _tier_num(tier)
    if n is None:
        return True
    return n <= max_n


def _resolve_tier_max(
    cfg: Dict[str, Any], goal: Optional[str], tier_max: Optional[str]
) -> Optional[str]:
    """Resolve effective tier_max from explicit tier_max or goal mapping in config.

    Precedence:
    1) explicit --tier-max
    2) RUN.goals[goal].tier_max (or GOALS[goal].tier_max)
    3) if goal looks like a tier (T0/T1/...), accept it directly
    4) unknown goal -> None (no filter)
    """
    if tier_max:
        return str(tier_max).strip()
    if not goal:
        return None
    g = str(goal).strip()
    if not g:
        return None
    # Direct tier (T0, T1, ...)
    if _TIER_RE.match(g):
        return g.upper()

    gk = g.lower()
    run_cfg = cfg.get("RUN") if isinstance(cfg.get("RUN"), dict) else {}
    goals = None
    if isinstance(run_cfg, dict) and isinstance(run_cfg.get("goals"), dict):
        goals = run_cfg.get("goals")
    elif isinstance(cfg.get("GOALS"), dict):
        goals = cfg.get("GOALS")
    if isinstance(goals, dict) and gk in goals:
        entry = goals.get(gk)
        if isinstance(entry, dict):
            tm = (
                entry.get("tier_max")
                if entry.get("tier_max") is not None
                else entry.get("max_tier")
            )
        else:
            tm = entry
        if tm is None:
            return None
        s = str(tm).strip()
        if not s or s.lower() == "null":
            return None
        if _TIER_RE.match(s):
            return s.upper()
    # Built-in fallback goals (only used if config has no mapping)
    if gk == "mvp":
        return "T0"
    if gk == "t1":
        return "T1"
    if gk == "release":
        return None
    return None


def _compute_work_status(work_root: Path, *, tier_max: Optional[str] = None) -> Dict[str, Any]:
    backlog_dir = work_root / "backlog"
    intake_dir = work_root / "intake"
    backlog_items = (
        parse_backlog_items(backlog_dir, include_done=False) if backlog_dir.exists() else []
    )
    intake_items = parse_intake_items(intake_dir, include_done=False) if intake_dir.exists() else []

    def _st(it: Dict[str, Any]) -> str:
        return str(it.get("status", "UNKNOWN"))

    # Totals (all tiers)
    total_work = sum(1 for it in backlog_items if _st(it) not in ("DONE", "BLOCKED"))
    total_blocked = sum(1 for it in backlog_items if _st(it) == "BLOCKED")

    # In-scope (tier filter)
    in_scope_work = sum(
        1
        for it in backlog_items
        if _within_tier(it.get("tier"), tier_max) and _st(it) not in ("DONE", "BLOCKED")
    )
    in_scope_blocked = sum(
        1 for it in backlog_items if _within_tier(it.get("tier"), tier_max) and _st(it) == "BLOCKED"
    )

    intake_pending = len(intake_items)

    if intake_pending > 0 or in_scope_work > 0:
        status = "work"
    elif in_scope_blocked > 0:
        status = "blocked"
    else:
        status = "none"

    return {
        "status": status,
        "goal_tier_max": tier_max,
        "intake_pending": intake_pending,
        "backlog_work": in_scope_work,
        "backlog_blocked": in_scope_blocked,
        "backlog_work_total": total_work,
        "backlog_blocked_total": total_blocked,
    }


def _blocked_items(work_root: Path, *, tier_max: Optional[str] = None) -> List[Dict[str, Any]]:
    backlog_dir = work_root / "backlog"
    items = parse_backlog_items(backlog_dir, include_done=False) if backlog_dir.exists() else []
    blocked: List[Dict[str, Any]] = []
    for it in items:
        if str(it.get("status")) != "BLOCKED":
            continue
        if not _within_tier(it.get("tier"), tier_max):
            continue
        blocked.append(
            {
                "id": it.get("id"),
                "title": it.get("title"),
                "prio": it.get("prio"),
                "tier": it.get("tier"),
                "blocked_by": it.get("blocked_by") or [],
                "path": it.get("path"),
            }
        )
    return blocked


def _write_blocker_report(
    repo_root: Path,
    work_root: Path,
    state: Dict[str, Any],
    reason: str,
    *,
    tier_max: Optional[str] = None,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    run_id = (
        state.get("run_id")
        if isinstance(state.get("run_id"), str) and state.get("run_id")
        else "NO-RUN"
    )
    out = work_root / "reports" / f"blocker-{stamp}-{run_id}.md"
    ensure_dir(out.parent)
    blocked = _blocked_items(work_root, tier_max=tier_max)
    created_at = now_iso_utc()

    lines: List[str] = []
    lines.append("---")
    lines.append("schema: fabric.report.v1")
    lines.append(f'date: "{today_date()}"')
    lines.append(f'created_at: "{created_at}"')
    lines.append('kind: "blocker"')
    lines.append('step: "idle"')
    lines.append(f'run_id: "{run_id}"')
    lines.append(f'reason: "{reason}"')
    lines.append("---\n")
    lines.append(f"# Blocker escalation ({today_date()})\n")
    lines.append("## Why we are blocked\n")
    lines.append(f"- {reason}\n")
    lines.append("## Blocked items\n")
    lines.append("| id | title | prio | tier | blocked_by | path |")
    lines.append("|---|---|---:|---|---|---|")
    for it in blocked:
        bid = str(it.get("id") or "")
        title = str(it.get("title") or "")
        prio = str(it.get("prio") or "")
        tier = str(it.get("tier") or "")
        bb = ", ".join([str(x) for x in (it.get("blocked_by") or [])])
        path = str(it.get("path") or "")
        # minimal escaping for pipes
        title = title.replace("|", "\\|")
        bb = bb.replace("|", "\\|")
        path = path.replace("|", "\\|")
        lines.append(f"| {bid} | {title} | {prio} | {tier} | {bb} | {path} |")
    lines.append("\n## What we need from a human\n")
    lines.append("- [ ] Provide missing access / secrets / credentials")
    lines.append("- [ ] Decide policy / priority / trade-off")
    lines.append("- [ ] Unblock dependencies or mark items as not needed\n")
    lines.append("## Evidence\n")
    lines.append("- This report was generated deterministically by `fabric.py tick`.")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Register for retrieval.
    try:
        _register_report(repo_root, work_root, out)
    except Exception:
        pass
    return out


def cmd_tick(args: argparse.Namespace) -> int:
    """Advance Fabric state deterministically after a step completes.

    This does NOT run skills. It only:
    - reads config/state
    - checks gating evidence (test/review)
    - patches state.step/phase (and some related fields)

    Designed to be called by `fabric-loop` after each skill.
    """
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    eff_tier_max = _resolve_tier_max(cfg, goal, tier_max)
    state_path = work_root / "state.md"
    state = state_read(state_path) if state_path.exists() else {}

    run_mode = args.run_mode or "fixed"
    run_mode = run_mode.lower().strip()
    if run_mode not in ("fixed", "auto"):
        raise ValueError("tick --run-mode must be fixed|auto")

    run_cfg = cfg.get("RUN") if isinstance(cfg.get("RUN"), dict) else {}
    idle_step = run_cfg.get("idle_step") if isinstance(run_cfg.get("idle_step"), str) else "idle"

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    eff_tier_max = _resolve_tier_max(cfg, goal, tier_max)

    completed = args.completed
    now_iso = now_iso_utc()

    patch: Dict[str, Any] = {"last_run": today_date()}
    next_step: Optional[str] = None
    reason: str = ""
    gating: Dict[str, Any] = {}
    if eff_tier_max is not None:
        gating["goal_tier_max"] = eff_tier_max
    if goal is not None:
        gating["goal"] = goal

    # Idle tick: decide whether to wake up.
    if not completed:
        if str(state.get("step")) != idle_step:
            # No-op (caller should pass --completed in normal flow)
            payload = {"schema": "fabric.tick.v1", "noop": True, "reason": "missing --completed"}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        ws = _compute_work_status(work_root, tier_max=eff_tier_max)
        gating["work_status"] = ws
        if ws["status"] == "work":
            next_step = _lifecycle_sections(cfg).get("orientation", ["vision"])[0]
            reason = "idle->orientation (work detected)"
        elif ws["status"] == "blocked":
            rep = _write_blocker_report(
                repo_root,
                work_root,
                state,
                reason="BLOCKED_ONLY (idle tick): all remaining backlog work is BLOCKED",
                tier_max=eff_tier_max,
            )
            patch["error"] = f"BLOCKED_ONLY: see {safe_relpath(rep, repo_root)}"
            next_step = idle_step
            reason = "idle (blocked)"
        else:
            next_step = idle_step
            reason = "idle (no work)"

    else:
        completed = str(completed).strip()
        patch["last_completed"] = completed

        # Default next step from lifecycle.
        next_step = _default_next_step(cfg, completed)
        reason = "default lifecycle"

        # Gating overrides.
        entries = _scan_reports(repo_root, work_root, include_archive=False)
        wip_item = state.get("wip_item") if isinstance(state.get("wip_item"), str) else None
        state.get("run_id") if isinstance(state.get("run_id"), str) else None
        sprint = state.get("sprint")
        sprint_str = str(sprint) if sprint is not None else None

        if completed == "test":
            if not wip_item:
                patch["error"] = "tick(test): missing state.wip_item"
                next_step = idle_step
                reason = "error"
            else:
                rep = _latest_report(entries, kind="test", item_id=wip_item)
                gating["test_report"] = rep
                if not rep:
                    patch["error"] = f"tick(test): missing test report for {wip_item}"
                    next_step = idle_step
                    reason = "error"
                else:
                    md = read_text((repo_root / rep["path"]).resolve())
                    res = _parse_test_result(md)
                    gating["test_result"] = res
                    if res == "FAIL":
                        next_step = "implement"
                        reason = "test FAIL -> implement"
                    elif res == "PASS":
                        next_step = "review"
                        reason = "test PASS -> review"
                    else:
                        patch["error"] = f"tick(test): unparseable Result in {rep['path']}"
                        next_step = idle_step
                        reason = "error"

        if completed == "review":
            if not wip_item:
                patch["error"] = "tick(review): missing state.wip_item"
                next_step = idle_step
                reason = "error"
            else:
                rep = _latest_report(entries, kind="review", item_id=wip_item)
                gating["review_report"] = rep
                if not rep:
                    patch["error"] = f"tick(review): missing review report for {wip_item}"
                    next_step = idle_step
                    reason = "error"
                else:
                    md = read_text((repo_root / rep["path"]).resolve())
                    verdict = _parse_review_verdict(md)
                    gating["review_verdict"] = verdict
                    if verdict == "CLEAN":
                        next_step = "close"
                        reason = "review CLEAN -> close"
                    elif verdict == "REWORK":
                        next_step = "implement"
                        reason = "review REWORK -> implement"
                    elif verdict == "REDESIGN":
                        next_step = "analyze"
                        reason = "review REDESIGN -> analyze"
                    else:
                        patch["error"] = f"tick(review): unparseable verdict in {rep['path']}"
                        next_step = idle_step
                        reason = "error"

        if completed == "close":
            # Close ends WIP.
            patch["wip_item"] = None
            patch["wip_branch"] = None

            # Decide whether there is another READY task in sprint.
            # If no sprint plan, proceed to docs.
            next_ready = None
            remaining = None
            try:
                if sprint_str is not None:
                    # reuse sprint-next logic by reading the plan and backlog.
                    sprint_path = work_root / "sprints" / f"sprint-{sprint_str}.md"
                    if sprint_path.exists():
                        md = read_text(sprint_path)
                        rows = _parse_md_table_rows(md, "## Task Queue")
                        task_ids: List[str] = []
                        for cols in rows:
                            if len(cols) >= 2:
                                tid = cols[1]
                                if tid and "{" not in tid:
                                    task_ids.append(tid)
                        # Load statuses
                        statuses: Dict[str, str] = {}
                        backlog_dir = work_root / "backlog"
                        for tid in task_ids:
                            cand = [backlog_dir / f"{tid}.md", backlog_dir / "done" / f"{tid}.md"]
                            st = ""
                            for cp in cand:
                                if cp.exists():
                                    fm = parse_frontmatter(read_text(cp)) or {}
                                    st = str(fm.get("status") or "")
                                    break
                            statuses[tid] = st
                        remaining = len([tid for tid in task_ids if statuses.get(tid) != "DONE"])
                        # Choose first READY (optionally constrained by tier_max)
                        for tid in task_ids:
                            if statuses.get(tid) != "READY":
                                continue
                            if eff_tier_max is not None:
                                # Load tier for constraint check
                                tier_val = ""
                                cand = [
                                    backlog_dir / f"{tid}.md",
                                    backlog_dir / "done" / f"{tid}.md",
                                ]
                                for cp in cand:
                                    if cp.exists():
                                        fm = parse_frontmatter(read_text(cp)) or {}
                                        tier_val = str(fm.get("tier") or "")
                                        break
                                if tier_val and not _within_tier(tier_val, eff_tier_max):
                                    continue
                            next_ready = tid
                            break
            except Exception:
                next_ready = None

            gating["sprint_next_ready"] = next_ready
            gating["sprint_remaining"] = remaining
            if next_ready:
                next_step = "implement"
                reason = "close -> implement next READY task"
            else:
                next_step = "docs"
                reason = "close -> docs (no READY tasks)"

        if completed == "prio" and run_mode == "auto":
            ws = _compute_work_status(work_root, tier_max=eff_tier_max)
            gating["work_status"] = ws
            if ws["status"] == "work":
                next_step = "sprint"
                reason = "auto guard: work -> sprint"
            elif ws["status"] == "blocked":
                rep = _write_blocker_report(
                    repo_root,
                    work_root,
                    state,
                    reason="BLOCKED_ONLY (auto guard after prio)",
                    tier_max=eff_tier_max,
                )
                patch["error"] = f"BLOCKED_ONLY: see {safe_relpath(rep, repo_root)}"
                next_step = idle_step
                reason = "auto guard: blocked -> idle+error"
            else:
                next_step = idle_step
                reason = "auto guard: no work -> idle"

        if completed == "archive":
            # New cycle = increment sprint.
            try:
                s = state.get("sprint")
                s_int = int(s) if s is not None else 0
            except Exception:
                s_int = 0
            patch["sprint"] = s_int + 1
            patch["sprint_goal"] = None
            patch["wip_item"] = None
            patch["wip_branch"] = None

            if run_mode == "auto":
                ws = _compute_work_status(work_root, tier_max=eff_tier_max)
                gating["work_status"] = ws
                if ws["status"] == "work":
                    next_step = _lifecycle_sections(cfg).get("orientation", ["vision"])[0]
                    reason = "auto guard after archive: work -> new cycle"
                elif ws["status"] == "blocked":
                    rep = _write_blocker_report(
                        repo_root,
                        work_root,
                        state,
                        reason="BLOCKED_ONLY (auto guard after archive)",
                        tier_max=eff_tier_max,
                    )
                    patch["error"] = f"BLOCKED_ONLY: see {safe_relpath(rep, repo_root)}"
                    next_step = idle_step
                    reason = "auto guard after archive: blocked -> idle+error"
                else:
                    next_step = idle_step
                    reason = "auto guard after archive: no work -> idle"
            else:
                next_step = _lifecycle_sections(cfg).get("orientation", ["vision"])[0]
                reason = "archive -> new cycle"

    assert next_step is not None
    patch["step"] = next_step
    patch["phase"] = "idle" if next_step == idle_step else _phase_for_step(cfg, next_step)
    patch["last_tick_at"] = now_iso

    state_patch(state_path, patch)
    payload = {
        "schema": "fabric.tick.v1",
        "created_at": now_iso,
        "completed": completed,
        "run_mode": run_mode,
        "next_step": next_step,
        "reason": reason,
        "patched": patch,
        "gating": gating,
    }

    # Flight recorder: persist every tick deterministically for debugging.
    try:
        logs_root = resolve_rel(
            repo_root,
            paths.get("LOGS_ROOT", str(paths.get("WORK_ROOT", "fabric/")).rstrip("/") + "/logs/"),
        )
    except Exception:
        logs_root = work_root / "logs"
    append_jsonl(logs_root / "ticks.jsonl", payload)
    append_md(
        logs_root / "ticks.md",
        f"- `{now_iso}` completed=`{completed}` next=`{next_step}` status=`{'ERROR' if patch.get('error') else 'OK'}` reason=`{reason}`",
    )

    # State history (human audit trail)
    hist_step = str(completed) if completed is not None else "idle"
    hist_result = "ERROR" if patch.get("error") else "OK"
    state_append_history_row(state_path, hist_step, hist_result, note=str(reason))

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not patch.get("error") else 2


def _parse_md_table_rows(md: str, header_prefix: str) -> List[List[str]]:
    """Parse a markdown table located after a line matching header_prefix."""
    lines = md.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith(header_prefix):
            start = i
            break
    if start is None:
        return []

    # find first table row after header
    rows: List[List[str]] = []
    in_table = False
    for ln in lines[start + 1 :]:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            cols = [c.strip() for c in s.strip("|").split("|")]
            # skip header separator
            if all(set(c) <= set("-:") for c in cols):
                continue
            rows.append(cols)
            in_table = True
        else:
            if in_table:
                break
    # Drop header row if present
    if rows and any(h.lower() in ("order", "id", "title") for h in rows[0]):
        return rows[1:]
    return rows


def cmd_sprint_next(args: argparse.Namespace) -> int:
    """Return deterministic next task info from current sprint plan + backlog statuses."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    state_path = work_root / "state.md"

    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}
    sprint = args.sprint
    if sprint is None:
        s = state.get("sprint")
        if isinstance(s, int):
            sprint = s
        elif isinstance(s, str) and s.isdigit():
            sprint = int(s)
    if sprint is None:
        raise ValueError("sprint-next requires --sprint or state.sprint")

    sprint_path = work_root / "sprints" / f"sprint-{sprint}.md"
    if not sprint_path.exists():
        print(
            json.dumps(
                {"schema": "fabric.sprint_next.v1", "sprint": sprint, "has_sprint": False},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    md = read_text(sprint_path)
    rows = _parse_md_table_rows(md, "## Task Queue")
    # Expected columns: Order, ID, Title, Type, Effort, Status, Depends on
    tasks: List[Dict[str, Any]] = []
    for cols in rows:
        if len(cols) < 2:
            continue
        try:
            order = int(cols[0])
        except Exception:
            continue
        tid = cols[1]
        if not tid or "{" in tid:
            continue
        tasks.append(
            {
                "order": order,
                "id": tid,
                "status": cols[5] if len(cols) > 5 else "",
                "depends_on": cols[6] if len(cols) > 6 else "",
            }
        )
    tasks.sort(key=lambda t: t["order"])

    # Load statuses from backlog frontmatter
    by_id: Dict[str, Dict[str, Any]] = {}
    for t in tasks:
        bid = t["id"]
        # search in backlog and backlog/done
        cand = [backlog_dir / f"{bid}.md", backlog_dir / "done" / f"{bid}.md"]
        fm: Dict[str, Any] = {}
        for p in cand:
            if p.exists():
                fm = parse_frontmatter(read_text(p)) or {}
                break
        by_id[bid] = fm

    # Helper: is dep done?
    def _is_done(dep_id: str) -> bool:
        fm = by_id.get(dep_id) or {}
        st = fm.get("status")
        return st == "DONE"

    current = None
    next_ready = None
    blocked = None

    for t in tasks:
        fm = by_id.get(t["id"]) or {}
        st = fm.get("status") if isinstance(fm.get("status"), str) else ""
        if st == "IN_PROGRESS":
            current = t["id"]
            break
    if current is None:
        for t in tasks:
            fm = by_id.get(t["id"]) or {}
            st = fm.get("status") if isinstance(fm.get("status"), str) else ""
            if st == "READY":
                # dependencies
                deps = fm.get("depends_on")
                dep_ids: List[str] = []
                if isinstance(deps, list):
                    dep_ids = [str(x) for x in deps]
                elif isinstance(deps, str) and deps.strip():
                    dep_ids = [x.strip() for x in deps.split(",") if x.strip()]
                if dep_ids and not all(_is_done(d) for d in dep_ids):
                    blocked = {"id": t["id"], "missing": [d for d in dep_ids if not _is_done(d)]}
                    continue
                next_ready = t["id"]
                break

    remaining = [t["id"] for t in tasks if (by_id.get(t["id"]) or {}).get("status") != "DONE"]

    out = {
        "schema": "fabric.sprint_next.v1",
        "sprint": sprint,
        "has_sprint": True,
        "tasks_total": len(tasks),
        "remaining": len(remaining),
        "current_in_progress": current,
        "next_ready": next_ready,
        "blocked": blocked,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def _safe_copy(src: Path, dest: Path) -> Path:
    """Copy src to dest; if dest exists, add a numeric suffix."""
    ensure_dir(dest.parent)
    if not dest.exists():
        shutil.copy2(str(src), str(dest))
        return dest
    stem = dest.stem
    suf = dest.suffix
    for i in range(1, 1000):
        cand = dest.with_name(f"{stem}-{i}{suf}")
        if not cand.exists():
            shutil.copy2(str(src), str(cand))
            return cand
    raise RuntimeError(f"Could not find free destination name for: {dest}")


def _safe_move(src: Path, dest: Path) -> Path:
    """Move src to dest; if dest exists, add a numeric suffix."""
    ensure_dir(dest.parent)
    if not dest.exists():
        shutil.move(str(src), str(dest))
        return dest
    stem = dest.stem
    suf = dest.suffix
    for i in range(1, 1000):
        cand = dest.with_name(f"{stem}-{i}{suf}")
        if not cand.exists():
            shutil.move(str(src), str(cand))
            return cand
    raise RuntimeError(f"Could not find free destination name for: {dest}")


def cmd_archive_sprint(args: argparse.Namespace) -> int:
    """Archive sprint artifacts deterministically (copy reports/analyses, move DONE backlog to done/)."""
    repo_root = find_repo_root(Path(args.repo_root) if args.repo_root else Path.cwd())
    _cfg_path, cfg = load_config(repo_root, Path(args.config).resolve() if args.config else None)
    paths = get_paths_block(cfg)
    work_root = resolve_rel(repo_root, paths.get("WORK_ROOT", "fabric/"))

    goal = args.goal if hasattr(args, "goal") else None
    tier_max = args.tier_max if hasattr(args, "tier_max") else None
    _resolve_tier_max(cfg, goal, tier_max)
    backlog_dir = work_root / "backlog"
    done_dir = backlog_dir / "done"
    reports_dir = work_root / "reports"
    analyses_dir = work_root / "analyses"
    visions_dir = work_root / "visions"
    state_path = work_root / "state.md"

    state: Dict[str, Any] = {}
    if state_path.exists():
        try:
            state = state_read(state_path)
        except Exception:
            state = {}
    sprint = args.sprint
    if sprint is None:
        s = state.get("sprint")
        if isinstance(s, int):
            sprint = s
        elif isinstance(s, str) and s.isdigit():
            sprint = int(s)
    if sprint is None:
        raise ValueError("archive-sprint requires --sprint or state.sprint")

    sprint_path = work_root / "sprints" / f"sprint-{sprint}.md"
    if not sprint_path.exists():
        raise FileNotFoundError(f"Sprint plan not found: {safe_relpath(sprint_path, repo_root)}")

    # Parse Task Queue IDs
    md = read_text(sprint_path)
    rows = _parse_md_table_rows(md, "## Task Queue")
    task_ids: List[str] = []
    for cols in rows:
        if len(cols) < 2:
            continue
        tid = cols[1].strip()
        if not tid or "{" in tid:
            continue
        task_ids.append(tid)

    # Verify no remaining tasks
    remaining_not_done: List[str] = []
    missing_backlog: List[str] = []
    backlog_paths: Dict[str, Path] = {}
    for tid in task_ids:
        cand = [backlog_dir / f"{tid}.md", done_dir / f"{tid}.md"]
        p = next((c for c in cand if c.exists()), None)
        if not p:
            missing_backlog.append(tid)
            continue
        backlog_paths[tid] = p
        fm = parse_frontmatter(read_text(p)) or {}
        st = fm.get("status")
        if st != "DONE":
            remaining_not_done.append(tid)

    if missing_backlog or remaining_not_done:
        out = {
            "schema": "fabric.archive_sprint.v1",
            "sprint": sprint,
            "ok": False,
            "missing_backlog": missing_backlog,
            "remaining_not_done": remaining_not_done,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 2

    stamp = args.stamp or f"sprint-{sprint}-{today_date()}"
    archive_root = work_root / "archive"
    dest_sprints = archive_root / "sprints" / stamp
    dest_reports = archive_root / "reports" / stamp
    dest_backlog = archive_root / "backlog" / stamp
    dest_analyses = archive_root / "analyses" / stamp
    dest_visions = archive_root / "visions" / stamp

    ensure_dir(dest_sprints)
    ensure_dir(dest_reports)
    ensure_dir(dest_backlog)
    ensure_dir(dest_analyses)
    ensure_dir(dest_visions)

    copied: List[str] = []
    moved: List[str] = []

    # Copy sprint plan
    copied.append(safe_relpath(_safe_copy(sprint_path, dest_sprints / sprint_path.name), repo_root))

    # Archive backlog items + move to done/
    for tid, p in backlog_paths.items():
        copied.append(safe_relpath(_safe_copy(p, dest_backlog / p.name), repo_root))
        if p.parent == backlog_dir:
            moved.append(safe_relpath(_safe_move(p, done_dir / p.name), repo_root))

    # Copy reports: heuristic = modified after sprint plan OR mention task id OR mention sprint id
    start_ts = sprint_path.stat().st_mtime
    if reports_dir.exists():
        for rp in sorted(reports_dir.glob("*.md")):
            try:
                mtime = rp.stat().st_mtime
            except Exception:
                mtime = 0
            name = rp.name
            include = (mtime >= (start_ts - 60)) or (f"sprint-{sprint}" in name)
            if not include:
                for tid in task_ids:
                    if tid in name:
                        include = True
                        break
            if include:
                copied.append(safe_relpath(_safe_copy(rp, dest_reports / rp.name), repo_root))

    # Copy analyses: modified after sprint plan
    if analyses_dir.exists():
        for ap in sorted(analyses_dir.glob("**/*")):
            if ap.is_dir():
                continue
            try:
                if ap.stat().st_mtime < (start_ts - 60):
                    continue
            except Exception:
                continue
            rel = safe_relpath(ap, analyses_dir)
            copied.append(safe_relpath(_safe_copy(ap, dest_analyses / rel), repo_root))

    # Copy visions: modified after sprint plan (rare, but useful)
    if visions_dir.exists():
        for vp in sorted(visions_dir.glob("**/*")):
            if vp.is_dir():
                continue
            try:
                if vp.stat().st_mtime < (start_ts - 60):
                    continue
            except Exception:
                continue
            rel = safe_relpath(vp, visions_dir)
            copied.append(safe_relpath(_safe_copy(vp, dest_visions / rel), repo_root))

    # Refresh backlog index after moves
    items = parse_backlog_items(backlog_dir, include_done=True) if backlog_dir.exists() else []
    generate_backlog_index(work_root, items)

    out = {
        "schema": "fabric.archive_sprint.v1",
        "sprint": sprint,
        "ok": True,
        "stamp": stamp,
        "copied": copied,
        "moved": moved,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="fabric")
    ap.add_argument(
        "--repo-root", default=None, help="Repo root (defaults to auto-detect from CWD)."
    )
    ap.add_argument(
        "--config", default=None, help="Path to config.md (optional; auto-discover if omitted)."
    )

    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("bootstrap", help="Ensure workspace skeleton + templates + state/backlog.")
    p.add_argument(
        "--create-vision-stub",
        action="store_true",
        help="Create a minimal vision.md stub if missing.",
    )
    p.add_argument(
        "--out-json", default=None, help="Write summary JSON to this path (relative to repo root)."
    )
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("templates-ensure", help="Copy missing templates into TEMPLATES_ROOT.")
    p.set_defaults(func=cmd_templates_ensure)

    p = sub.add_parser("backlog-scan", help="Scan backlog items and output JSON.")
    p.add_argument("--include-done", action="store_true")
    p.add_argument("--json-out", default=None)
    p.set_defaults(func=cmd_backlog_scan)

    p = sub.add_parser("backlog-validate", help="Validate backlog item frontmatter schemas/enums.")
    p.add_argument("--include-done", action="store_true")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    p.set_defaults(func=cmd_backlog_validate)

    p = sub.add_parser(
        "backlog-normalize", help="Normalize backlog item frontmatter deterministically."
    )
    p.add_argument("--include-done", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_backlog_normalize)

    p = sub.add_parser("intake-scan", help="Scan intake items and output JSON.")
    p.add_argument("--include-done", action="store_true")
    p.add_argument("--json-out", default=None)
    p.set_defaults(func=cmd_intake_scan)

    p = sub.add_parser(
        "intake-new", help="Create a new intake item from template deterministically."
    )
    p.add_argument("--title", required=True)
    p.add_argument("--source", default="manual", help="SOURCE_TYPE placeholder")
    p.add_argument("--initial-type", default="Task", help="SUGGESTED_TYPE placeholder")
    p.add_argument("--raw-priority", default="5", help="RAW_PRIORITY placeholder")
    p.add_argument("--vision-goal", default=None, help="LINKED_VISION_GOAL placeholder")
    p.add_argument("--description", default=None)
    p.add_argument("--context", default=None)
    p.add_argument("--recommended", default=None)
    p.add_argument("--author", default=None)
    p.add_argument(
        "--out",
        default=None,
        help="Output path (relative to repo root). Defaults to WORK_ROOT/intake/...",
    )
    p.set_defaults(func=cmd_intake_new)

    p = sub.add_parser(
        "work-status", help="Summarize whether there is actionable work to do (intake/backlog)."
    )
    p.add_argument(
        "--goal",
        default=None,
        help="Optional goal name (resolved via RUN.goals) or direct tier (T0/T1/...).",
    )
    p.add_argument(
        "--tier-max",
        default=None,
        help="Optional max tier (T0/T1/...) to scope what counts as remaining work.",
    )
    p.add_argument("--json-out", default=None)
    p.set_defaults(func=cmd_work_status)

    p = sub.add_parser("backlog-index", help="Regenerate backlog.md index from items.")
    p.set_defaults(func=cmd_backlog_index)

    p = sub.add_parser(
        "governance-index", help="Regenerate decisions/specs/reviews INDEX.md deterministically."
    )
    p.add_argument(
        "--kind",
        default="all",
        choices=["all", "decisions", "specs", "reviews"],
        help="Which index to regenerate.",
    )
    p.set_defaults(func=cmd_governance_index)

    p = sub.add_parser(
        "governance-scan", help="Scan decisions/specs for stale items and missing metadata."
    )
    p.add_argument("--json-out", default="", help="Optional path to write JSON output.")
    p.set_defaults(func=cmd_governance_scan)

    p = sub.add_parser(
        "review-publish", help="Copy a report into reviews/ and refresh reviews/INDEX.md."
    )
    p.add_argument(
        "--src",
        required=True,
        help="Source report path relative to repo root (e.g., fabric/reports/review-...md)",
    )
    p.set_defaults(func=cmd_review_publish)

    p = sub.add_parser(
        "backlog-set", help="Patch frontmatter fields for a backlog item (JSON dict)."
    )
    p.add_argument("--id", required=True)
    p.add_argument(
        "--fields-json", required=True, help='JSON object, e.g. {"prio": 80, "effort": "S"}'
    )
    p.set_defaults(func=cmd_backlog_set)

    p = sub.add_parser("state-read", help="Read YAML fence from state.md.")
    p.add_argument("--field", default=None, help="Return single field value (e.g. --field run_id)")
    p.add_argument("--json-out", default=None)
    p.set_defaults(func=cmd_state_read)

    p = sub.add_parser("state-patch", help="Patch YAML fence in state.md (JSON dict).")
    p.add_argument("--fields-json", required=True)
    p.set_defaults(func=cmd_state_patch)

    p = sub.add_parser("run-start", help="Start a new Fabric RUN (set run_id, clear error fields).")
    p.add_argument("--step", default=None, help="Optional step reset (e.g., vision).")
    p.add_argument("--phase", default=None, help="Optional phase reset (e.g., orientation).")
    p.set_defaults(func=cmd_run_start)

    p = sub.add_parser(
        "report-new", help="Create a report file from a template with placeholder expansion."
    )
    p.add_argument("--template", default="report.md", help="Template name in TEMPLATES_ROOT.")
    p.add_argument(
        "--out",
        default=None,
        help="Output path (relative to repo root). If omitted, auto-generates.",
    )
    p.add_argument("--skill", default=None, help="Skill name to inject as {SKILL_NAME}.")
    p.add_argument("--step", default=None, help="Step to inject as {STEP}.")
    p.add_argument("--kind", default=None, help="Logical report kind (defaults to step).")
    p.add_argument("--phase", default=None, help="Phase to inject as {PHASE}.")
    p.add_argument("--status", default=None, help="Status to inject as {STATUS} (OK/WARN/ERROR).")
    p.add_argument("--set-json", default=None, help="Extra placeholders as JSON object.")
    p.add_argument(
        "--ensure-run-id", action="store_true", help="If state.run_id is empty, generate one."
    )
    p.set_defaults(func=cmd_report_new)

    p = sub.add_parser("report-index", help="Build deterministic report index (report-index.json).")
    p.add_argument("--include-archive", action="store_true")
    p.add_argument(
        "--out",
        default=None,
        help="Output path (relative to repo root). Defaults to WORK_ROOT/reports/report-index.json",
    )
    p.set_defaults(func=cmd_report_index)

    p = sub.add_parser(
        "report-latest",
        help="Return latest report entry for kind (+ optional item/run/sprint filters).",
    )
    p.add_argument("--kind", required=True)
    p.add_argument("--item-id", default=None)
    p.add_argument("--run-id", default=None)
    p.add_argument("--sprint", default=None)
    p.add_argument("--include-archive", action="store_true")
    p.set_defaults(func=cmd_report_latest)

    p = sub.add_parser("reports-validate", help="Validate report frontmatter + gating fields.")
    p.add_argument("--include-archive", action="store_true")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    p.set_defaults(func=cmd_reports_validate)

    p = sub.add_parser(
        "contract-check", help="Check deterministic file-level contracts for a given step."
    )
    p.add_argument("--step", required=True, help="Step name (vision/status/...)")
    p.set_defaults(func=cmd_contract_check)

    p = sub.add_parser(
        "run-report", help="Create/append per-run timeline report (reports/run-{run_id}.md)."
    )
    p.add_argument("--completed", default=None, help="Step name to append (optional).")
    p.add_argument("--status", default=None, help="OK|WARN|ERROR")
    p.add_argument("--note", default=None)
    p.add_argument(
        "--report", default=None, help="Explicit report path to link (relative to repo root)."
    )
    p.add_argument(
        "--out",
        default=None,
        help="Run report path (relative to repo root). Defaults to WORK_ROOT/reports/run-{run_id}.md",
    )
    p.add_argument("--ensure-run-id", action="store_true")
    p.set_defaults(func=cmd_run_report)

    p = sub.add_parser("evidence-pack", help="Create an evidence ZIP for debugging/escalation.")
    p.add_argument("--label", default="evidence")
    p.add_argument(
        "--out",
        default=None,
        help="Output ZIP path (relative to repo root). Defaults to WORK_ROOT/reports/evidence-...",
    )
    p.add_argument("--max-command-logs", type=int, default=5)
    p.set_defaults(func=cmd_evidence_pack)

    p = sub.add_parser("tick", help="Advance state deterministically after a step completes.")
    p.add_argument(
        "--completed",
        default=None,
        help="Completed step name. If omitted and state.step is idle, performs idle tick.",
    )
    p.add_argument("--run-mode", default="fixed", help="fixed|auto (affects prio/archive guards).")
    p.add_argument(
        "--goal",
        default=None,
        help="Optional goal name (resolved via RUN.goals) or direct tier (T0/T1/...).",
    )
    p.add_argument(
        "--tier-max",
        default=None,
        help="Optional max tier (T0/T1/...) to scope done-condition checks.",
    )
    p.set_defaults(func=cmd_tick)

    p = sub.add_parser(
        "sprint-next", help="Inspect current sprint plan and report next actionable task."
    )
    p.add_argument(
        "--sprint", type=int, default=None, help="Sprint number (defaults to state.sprint)."
    )
    p.set_defaults(func=cmd_sprint_next)

    p = sub.add_parser(
        "archive-sprint",
        help="Archive sprint artifacts (reports/analyses/visions, backlog snapshots).",
    )
    p.add_argument(
        "--sprint", type=int, default=None, help="Sprint number (defaults to state.sprint)."
    )
    p.add_argument(
        "--stamp", default=None, help="Archive stamp (defaults to sprint-<N>-<YYYY-MM-DD>)."
    )
    p.set_defaults(func=cmd_archive_sprint)

    p = sub.add_parser("run", help="Run COMMANDS.<key> from config with log capture.")
    p.add_argument("key")
    p.add_argument("--tail", type=int, default=120)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser(
        "gate-test", help="Run COMMANDS.test + write parsable test report deterministically."
    )
    p.add_argument("--tail", type=int, default=200)
    p.set_defaults(func=cmd_gate_test)

    p = sub.add_parser(
        "snapshot-status",
        help="Write deterministic status snapshot JSON (git, code stats, backlog, commands).",
    )
    p.add_argument("--out", required=True, help="Output JSON path (relative to repo root).")
    p.add_argument("--tail", type=int, default=120, help="Tail lines for command outputs.")
    p.set_defaults(func=cmd_snapshot_status)

    p = sub.add_parser("apply", help="Apply a deterministic plan file (fabric.plan.v1).")
    p.add_argument("plan")
    p.set_defaults(func=cmd_apply)

    return ap


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()
    try:
        rc = args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(rc)


if __name__ == "__main__":
    main()
