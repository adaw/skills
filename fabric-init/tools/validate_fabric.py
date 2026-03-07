#!/usr/bin/env python3
"""
Fabric Validator (static)

Goals:
- Catch drift between config/contracts, templates, and skills BEFORE an agent runs.
- Provide fast feedback in CI or locally.

Modes:
- default (framework): validates framework structure + contracts (config/templates/skills).
- --workspace: additionally validates runtime workspace directories/files under WORK_ROOT (requires init run).
- --runnable: require COMMANDS to be resolved for a safe autonomous run.

This validator is intentionally conservative: it only checks what can be verified statically.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import yaml  # type: ignore


# ---------- helpers ----------

CONFIG_MARKERS = ["WORK_ROOT:", "CODE_ROOT:", "COMMANDS:"]

REQUIRED_SKILLS = [
    "fabric-init",
    "fabric-loop",
    "fabric-vision",
    "fabric-status",
    "fabric-architect",
    "fabric-gap",
    "fabric-generate",
    "fabric-intake",
    "fabric-prio",
    "fabric-sprint",
    "fabric-analyze",
    "fabric-implement",
    "fabric-test",
    "fabric-review",
    "fabric-close",
    "fabric-docs",
    "fabric-check",
    "fabric-archive",
]

DEFAULT_REQUIRED_TEMPLATES = [
    "adr.md",
    "spec.md",
    "audit-report.md",
    "close-report.md",
    "epic.md",
    "intake.md",
    "migration-report.md",
    "review-summary.md",
    "sprint-plan.md",
    "state.md",
    "status-report.md",
    "story.md",
    "task.md",
	"report.md",
	"test-report.md",
]

FORBIDDEN_HARDCODED_SNIPPETS = ["goden/", "tests/", "docs/", "fabric/"]  # allowed only via {VARS} or in marked examples


@dataclass
class Result:
    ok: bool
    warnings: List[str]
    errors: List[str]


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


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
            data = yaml.safe_load(raw)
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


def find_paths_block(blocks: List[dict]) -> Optional[dict]:
    for b in blocks:
        if isinstance(b, dict) and "WORK_ROOT" in b and "CODE_ROOT" in b:
            return b
    return None


def parse_frontmatter(md: str) -> Optional[dict]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, flags=re.S)
    if not m:
        return None
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")




# ---------- security lint (skills) ----------

CODE_FENCE_RE = re.compile(r"```(?P<lang>[A-Za-z0-9_-]*)\n(?P<body>.*?)(?:\n)?```", re.DOTALL)

FORBIDDEN_CMD_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard (history rewrite / destructive)"),
    (re.compile(r"\bgit\s+push\b[^\n]*\s(--force|-f)\b"), "git push --force/-f (rewriting shared history)"),
    (re.compile(r"\bgit\s+rebase\b"), "git rebase (unsafe on published branches)"),
    (re.compile(r"\brm\s+-rf\b"), "rm -rf (destructive)"),
    (re.compile(r"\bgit\s+clean\b[^\n]*\s-([fF].*)\b"), "git clean -f (destructive)"),
]


def extract_code_fences(md: str) -> List[Tuple[str, str]]:
    fences: List[Tuple[str, str]] = []
    for m in CODE_FENCE_RE.finditer(md):
        lang = (m.group("lang") or "").strip().lower()
        body = m.group("body") or ""
        fences.append((lang, body))
    return fences

# ---------- validations ----------

def validate_config(config_path: Path, runnable: bool) -> Tuple[Result, dict, dict]:
    warnings: List[str] = []
    errors: List[str] = []

    txt = read_text(config_path)
    blocks = extract_yaml_blocks(txt)
    merged = merge_blocks(blocks)

    paths = find_paths_block(blocks)
    if not paths:
        errors.append("config.md: missing YAML paths block with WORK_ROOT/CODE_ROOT.")
        return Result(False, warnings, errors), {}, {}

    for key in ["WORK_ROOT", "CODE_ROOT", "TEMPLATES_ROOT", "ANALYSES_ROOT"]:
        if key not in paths:
            errors.append(f"config.md: missing {key} in paths block.")

    schema = merged.get("SCHEMA")
    enums = merged.get("ENUMS")
    quality = merged.get("QUALITY")
    templates_required = merged.get("TEMPLATES_REQUIRED")

    if not isinstance(schema, dict):
        warnings.append("config.md: SCHEMA block missing (recommended).")
        schema = {}
    else:
        for k in ["backlog_item", "intake_item", "sprint_plan", "state", "reports"]:
            if k not in schema:
                errors.append(f"config.md: SCHEMA.{k} missing.")
        # Governance schemas are strongly recommended (used by decisions/specs tooling)
        for k in ["adr", "spec"]:
            if k not in schema:
                warnings.append(f"config.md: SCHEMA.{k} missing (recommended).")

    if not isinstance(enums, dict):
        warnings.append("config.md: ENUMS block missing (recommended).")
        enums = {}
    else:
        for k in ["statuses", "types", "task_types"]:
            if k not in enums:
                errors.append(f"config.md: ENUMS.{k} missing.")
        for k in ["adr_statuses", "spec_statuses"]:
            if k not in enums:
                warnings.append(f"config.md: ENUMS.{k} missing (recommended).")

    if not isinstance(quality, dict):
        warnings.append("config.md: QUALITY block missing (recommended). Assuming bootstrap.")
        quality = {"mode": "bootstrap"}
    else:
        mode = quality.get("mode")
        if mode not in ("bootstrap", "strict"):
            errors.append("config.md: QUALITY.mode must be 'bootstrap' or 'strict'.")

    if templates_required is not None and not isinstance(templates_required, list):
        errors.append("config.md: TEMPLATES_REQUIRED must be a list.")
        templates_required = None

    commands = merged.get("COMMANDS")
    if not isinstance(commands, dict):
        errors.append("config.md: missing COMMANDS YAML block.")
        commands = {}
    else:
        test_cmd = commands.get("test")
        if test_cmd is None:
            errors.append("config.md: COMMANDS.test key missing.")
        elif test_cmd in ("", "TBD"):
            (errors if runnable else warnings).append(
                f"config.md: COMMANDS.test is '{test_cmd}' (must be resolved for runnable mode)."
            )

        for opt in ["lint", "format_check"]:
            val = commands.get(opt)
            if val is None:
                warnings.append(f"config.md: COMMANDS.{opt} key missing (ok if not enforcing).")
            elif val == "TBD":
                (errors if runnable else warnings).append(
                    f"config.md: COMMANDS.{opt} is TBD (set to a command or disable as '')."
                )
            elif val == "" and quality.get("mode") == "strict":
                (errors if runnable else warnings).append(
                    f"config.md: COMMANDS.{opt} is disabled (''), but QUALITY.mode=strict expects it enabled."
                )

    git = merged.get("GIT")
    if not isinstance(git, dict) or not git.get("main_branch"):
        warnings.append("config.md: GIT block missing or main_branch not set.")

    sprint = merged.get("SPRINT")
    if not isinstance(sprint, dict):
        warnings.append("config.md: SPRINT block missing.")
    else:
        if sprint.get("wip_limit") != 1:
            warnings.append("config.md: SPRINT.wip_limit should be 1 for single-piece flow.")

    # Optional: deterministic IO contracts (recommended for robust loop).
    contracts = merged.get("CONTRACTS")
    if contracts is not None:
        if not isinstance(contracts, dict):
            warnings.append("config.md: CONTRACTS should be a dict if present.")
        else:
            outs = contracts.get("outputs")
            if outs is None:
                warnings.append("config.md: CONTRACTS.outputs missing (recommended).")
            elif not isinstance(outs, dict):
                warnings.append("config.md: CONTRACTS.outputs should be a dict.")
            else:
                lifecycle = merged.get("LIFECYCLE")
                steps: List[str] = []
                if isinstance(lifecycle, dict):
                    for phase_steps in lifecycle.values():
                        if isinstance(phase_steps, list):
                            steps.extend([str(x) for x in phase_steps])
                missing_steps = [s for s in steps if s not in outs]
                if missing_steps:
                    warnings.append(
                        "config.md: CONTRACTS.outputs missing steps: " + ", ".join(missing_steps)
                    )

    contracts = {
        "SCHEMA": schema,
        "ENUMS": enums,
        "QUALITY": quality,
        "TEMPLATES_REQUIRED": templates_required or DEFAULT_REQUIRED_TEMPLATES,
    }

    return Result(len(errors) == 0, warnings, errors), paths, contracts


def validate_templates(repo_root: Path, templates_root_rel: str, contracts: dict) -> Result:
    warnings: List[str] = []
    errors: List[str] = []
    templates_dir = (repo_root / templates_root_rel).resolve()
    if not templates_dir.exists():
        errors.append(f"Missing templates directory: {templates_dir}")
        return Result(False, warnings, errors)

    required = contracts.get("TEMPLATES_REQUIRED") or DEFAULT_REQUIRED_TEMPLATES
    for t in required:
        p = templates_dir / t
        if not p.exists():
            errors.append(f"Missing template: {p}")

    schema = contracts.get("SCHEMA") or {}
    expected = {
        "report.md": schema.get("reports"),
        "task.md": schema.get("backlog_item"),
        "story.md": schema.get("backlog_item"),
        "review-summary.md": schema.get("reports"),
        "audit-report.md": schema.get("reports"),
        "test-report.md": schema.get("reports"),
        "sprint-plan.md": schema.get("sprint_plan"),
        "state.md": schema.get("state"),
        "status-report.md": schema.get("reports"),
        # Governance templates can have their own schema (preferred) or fallback to reports for legacy.
        "adr.md": schema.get("adr") or schema.get("reports"),
        "spec.md": schema.get("spec") or schema.get("reports"),
    }

    for fname, expected_schema in expected.items():
        if not expected_schema:
            continue
        p = templates_dir / fname
        if not p.exists():
            continue
        txt = read_text(p)
        fm = parse_frontmatter(txt)
        if not fm:
            warnings.append(f"Template {fname}: missing YAML frontmatter (schema not verifiable).")
            continue
        if fm.get("schema") != expected_schema:
            errors.append(f"Template {fname}: schema='{fm.get('schema')}' != expected '{expected_schema}'.")

    state_tpl = templates_dir / "state.md"
    if state_tpl.exists() and schema.get("state"):
        txt = read_text(state_tpl)
        m = re.search(r"```yaml\s*(.*?)```", txt, flags=re.S | re.I)
        if not m:
            errors.append("Template state.md: missing ```yaml block.")
        else:
            raw = m.group(1)
            if f"schema: {schema.get('state')}" not in raw:
                errors.append("Template state.md: schema line missing or mismatched in YAML block.")

    return Result(len(errors) == 0, warnings, errors)


def validate_skills(repo_root: Path, skills_root_rel: str) -> Result:
    warnings: List[str] = []
    errors: List[str] = []

    skills_root = (repo_root / skills_root_rel).resolve()
    if not skills_root.exists():
        errors.append(f"Missing skills directory: {skills_root}")
        return Result(False, warnings, errors)

    
    # Required deterministic tools (used by many skills)
    required_tools = [
        skills_root / "fabric-init" / "tools" / "protocol_log.py",
        skills_root / "fabric-init" / "tools" / "validate_fabric.py",
        skills_root / "fabric-init" / "tools" / "fabric.py",
        skills_root / "fabric-init" / "tools" / "fabric_lib.py",
    ]
    for p in required_tools:
        if not p.exists():
            errors.append(f"Missing required tool: {p}")

    for name in REQUIRED_SKILLS:
        skill_dir = skills_root / name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"Missing skill file: {skill_file}")
            continue

        md = read_text(skill_file)
        # Security lint: ensure skills do not contain forbidden destructive commands in runnable code fences.
        for lang, body in extract_code_fences(md):
            # Only scan fences that are likely runnable. If lang is empty, still scan (many skills omit language).
            for rx, label in FORBIDDEN_CMD_PATTERNS:
                if rx.search(body):
                    errors.append(f"{skill_file}: forbidden command in code fence: {label}")
                    break

        fm = parse_frontmatter(md)
        if not fm:
            errors.append(f"{skill_file}: missing/invalid YAML frontmatter.")
            continue

        # --- Frontmatter validation (Claude Code Agent Skills spec) ---
        fm_name = fm.get("name", "")
        if not fm_name:
            errors.append(f"{skill_file}: frontmatter missing 'name' field.")
        else:
            if fm_name != name:
                warnings.append(f"{skill_file}: frontmatter name='{fm_name}' != dir '{name}'.")
            if len(fm_name) > 64:
                errors.append(f"{skill_file}: frontmatter name exceeds 64 chars ({len(fm_name)}).")
            if not re.match(r"^[a-z0-9-]+$", fm_name):
                errors.append(f"{skill_file}: frontmatter name='{fm_name}' must be lowercase+hyphens only.")

        fm_desc = fm.get("description", "")
        if not fm_desc:
            errors.append(f"{skill_file}: frontmatter missing or empty 'description'.")
        else:
            if len(str(fm_desc)) > 1024:
                errors.append(f"{skill_file}: frontmatter description exceeds 1024 chars ({len(str(fm_desc))}).")
            if "<" in str(fm_desc) and ">" in str(fm_desc):
                warnings.append(f"{skill_file}: frontmatter description contains XML-like tags (not recommended).")

        # Forbidden fields (not part of Claude Code spec)
        for forbidden in ["title", "type", "schema", "version"]:
            if forbidden in fm:
                errors.append(f"{skill_file}: frontmatter contains forbidden field '{forbidden}'.")

        # Recommended fields
        for recommended in ["tags", "depends_on", "feeds_into"]:
            if recommended not in fm:
                warnings.append(f"{skill_file}: frontmatter missing recommended field '{recommended}'.")

        # builder-template tag position check (must be AFTER ---, not inside YAML)
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, flags=re.S)
        if fm_match and "built from" in fm_match.group(1):
            errors.append(f"{skill_file}: builder-template tag is inside YAML frontmatter (must be after ---).")

        line_count = md.count("\n") + 1
        if line_count > 500:
            warnings.append(f"{skill_file}: {line_count} lines (>500). Consider splitting to avoid LLM truncation.")

        for snippet in FORBIDDEN_HARDCODED_SNIPPETS:
            for m in re.finditer(re.escape(snippet), md):
                line_no = md.count("\n", 0, m.start()) + 1
                line = md.splitlines()[line_no - 1]
                if "PŘÍKLAD" in line or "EXAMPLE" in line:
                    continue
                if md[max(0, m.start() - 2):m.start()] == "}/":
                    continue
                errors.append(f"{skill_file}: hardcoded '{snippet}' at line {line_no}: {line.strip()}")
                break  # one error per snippet per file is enough

    
    # CANON assets (portable-by-copying skills/)
    canon_templates = repo_root / "skills" / "fabric-init" / "assets" / "templates"
    if not canon_templates.exists():
        errors.append(f"Missing canonical templates dir: {canon_templates}")
    else:
        for t in DEFAULT_REQUIRED_TEMPLATES:
            if not (canon_templates / t).exists():
                errors.append(f"Missing canonical template: {canon_templates / t}")

    canon_tools = repo_root / "skills" / "fabric-init" / "tools"
    for tool in ["validate_fabric.py", "protocol_log.py"]:
        if not (canon_tools / tool).exists():
            errors.append(f"Missing canonical tool: {canon_tools / tool}")

    return Result(len(errors) == 0, warnings, errors)


def validate_workspace(repo_root: Path, work_root_rel: str, runnable: bool) -> Result:
    warnings: List[str] = []
    errors: List[str] = []
    work_root = (repo_root / work_root_rel).resolve()

    required_dirs = [
        "backlog",
        "backlog/done",
        "intake",
        "intake/done",
        "intake/rejected",
        "reports",
        "sprints",
        "analyses",
        "templates",
        "visions",
        "decisions",
        "specs",
        "reviews",
        "logs",
        "logs/commands",
        "archive",
        "archive/backlog",
        "archive/sprints",
        "archive/reports",
        "archive/analyses",
        "archive/visions",
        "archive/quarantine",
    ]
    for d in required_dirs:
        p = work_root / d
        if not p.exists():
            errors.append(f"Missing required directory: {p}")

    for f in ["state.md", "vision.md", "backlog.md", "config.md"]:
        p = work_root / f
        if not p.exists():
            errors.append(f"Missing required file: {p}")

    if runnable and (work_root / "state.md").exists():
        txt = read_text(work_root / "state.md")
        if "```yaml" not in txt:
            warnings.append("state.md: expected ```yaml block (template format).")

    # Vision sanity (lightweight, always-on in workspace mode)
    v_path = work_root / "vision.md"
    if v_path.exists():
        v_txt = read_text(v_path)
        placeholder_re = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b", re.IGNORECASE)
        if placeholder_re.search(v_txt or ""):
            warnings.append("vision.md contains placeholder markers (TODO/TBD/FIXME/XXX). Consider finishing the core vision.")
    visions_dir = work_root / "visions"
    if visions_dir.exists():
        md_files = sorted([p for p in visions_dir.glob("*.md") if p.is_file()])
        if len(md_files) == 0:
            warnings.append("visions/ is empty (recommended to have sub-visions for deeper concepts).")
        else:
            # Warn about very short sub-visions
            for p in md_files:
                txt = read_text(p) or ""
                lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                if len(lines) < 8:
                    warnings.append(f"sub-vision looks very short: {p}")
                if re.search(r"\b(TODO|TBD|FIXME|XXX)\b", txt, re.IGNORECASE):
                    warnings.append(f"placeholder markers in {p} (consider finishing).")

    
    # Governance indices (recommended for readability + automation)
    for d in ["decisions", "specs", "reviews"]:
        idx = work_root / d / "INDEX.md"
        if not idx.exists():
            warnings.append(f"Missing governance index file: {idx} (recommended; regenerate via fabric.py governance-index).")



    return Result(len(errors) == 0, warnings, errors)




def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runnable", action="store_true", help="Require COMMANDS to be resolved for a safe autonomous run.")
    ap.add_argument("--workspace", action="store_true", help="Validate runtime workspace under WORK_ROOT (requires init).")
    args = ap.parse_args()

    repo_root = Path(os.getcwd()).resolve()

    config_path, candidates = discover_config(repo_root)
    if not config_path:
        die("ERROR: No Fabric config.md found (searched for config.md containing WORK_ROOT:, CODE_ROOT:, COMMANDS:).", code=2)

    if len(candidates) > 1:
        print("WARNING: Multiple config.md candidates found; using:", config_path)
        for c in candidates:
            print(" -", c)

    res_cfg, paths, contracts = validate_config(config_path, runnable=args.runnable)
    for w in res_cfg.warnings:
        print("WARNING:", w)
    for e in res_cfg.errors:
        print("ERROR:", e)
    if not res_cfg.ok:
        die("Config validation failed.", code=3)

    work_root_rel = paths.get("WORK_ROOT")
    if not isinstance(work_root_rel, str):
        die("ERROR: Could not extract WORK_ROOT from config.md.", code=4)
    templates_root_rel = paths.get("TEMPLATES_ROOT") or f"{work_root_rel}/templates"
    if not isinstance(templates_root_rel, str):
        templates_root_rel = f"{work_root_rel}/templates"
        print("WARNING: Could not extract TEMPLATES_ROOT from config.md; defaulting to", templates_root_rel)

    skills_root_rel = paths.get("SKILLS_ROOT") or "skills"
    if not isinstance(skills_root_rel, str):
        skills_root_rel = "skills"
        print("WARNING: Could not extract SKILLS_ROOT from config.md; defaulting to", skills_root_rel)


    res_tpl = validate_templates(repo_root, templates_root_rel, contracts)
    for w in res_tpl.warnings:
        print("WARNING:", w)
    for e in res_tpl.errors:
        print("ERROR:", e)

    res_sk = validate_skills(repo_root, skills_root_rel)
    for w in res_sk.warnings:
        print("WARNING:", w)
    for e in res_sk.errors:
        print("ERROR:", e)

    res_ws = Result(True, [], [])
    if args.workspace:
        res_ws = validate_workspace(repo_root, work_root_rel, runnable=args.runnable)
        for w in res_ws.warnings:
            print("WARNING:", w)
        for e in res_ws.errors:
            print("ERROR:", e)

    ok = res_cfg.ok and res_tpl.ok and res_sk.ok and res_ws.ok
    if ok:
        print("OK: Fabric validation passed.", "(runnable)" if args.runnable else "(framework)")
        sys.exit(0)

    die("Validation failed.", code=5)


if __name__ == "__main__":
    main()
