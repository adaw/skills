#!/usr/bin/env python3
"""T10: Config key stale read — automatická detekce.

Prochází bash bloky ve všech skills/fabric-*/SKILL.md,
extrahuje config klíče čtené přes grep/awk a ověřuje,
že existují v fabric/config.md.

Použití:
    python3 scripts/t10_config_stale_check.py
    python3 scripts/t10_config_stale_check.py --verbose
"""

import re
import os
import sys
from pathlib import Path


def extract_config_keys(config_path: str) -> set[str]:
    """Vytáhne všechny klíče (top-level, nested i tečkové) z config.md.

    Generuje:
    - top-level: COMMANDS, QUALITY, RUN, ...
    - nested: test, lint, mode, ...
    - dotted: COMMANDS.test, QUALITY.mode, RUN.skill_timeout, ...
    """
    text = Path(config_path).read_text()
    keys = set()
    current_top = None

    for line in text.splitlines():
        # Top-level key (no indent, uppercase start)
        m = re.match(r"^([A-Z][\w]*)\s*:", line)
        if m:
            current_top = m.group(1)
            keys.add(current_top)
            continue
        # Nested key (2-space indent)
        m = re.match(r"^  (\w[\w_]*)\s*:", line)
        if m and current_top:
            nested = m.group(1)
            keys.add(nested)
            keys.add(f"{current_top}.{nested}")
            continue
        # Reset on non-indented non-comment line
        if re.match(r"^\S", line) and not line.startswith("#"):
            current_top = None

    return keys


def extract_bash_blocks(skill_path: str) -> list[str]:
    """Vytáhne obsah ```bash ... ``` bloků ze SKILL.md."""
    text = Path(skill_path).read_text()
    return re.findall(r"```bash\n(.*?)```", text, re.DOTALL)


def extract_referenced_keys(bash_blocks: list[str]) -> list[tuple[str, str]]:
    """Z bash bloků vytáhne (klíč, zdrojový_pattern) config čtení.

    Detekuje:
    - grep 'KEY:' ... config.md
    - grep '^KEY:' ... config.md
    - awk '/KEY:/...' ... config.md
    - awk patterns s vnořenými klíči: /timeout_bounds:/,/^[^ ]/{if(/  test:/)...}
    """
    refs = []

    for block in bash_blocks:
        # Pattern 1: grep 'KEY:' nebo grep '^KEY:' ... config
        for m in re.finditer(
            r"""grep\s+(?:-\w+\s+)*['"]?\^?(\w[\w.]*\w?):['"]?\s+.*config""", block
        ):
            refs.append((m.group(1), f"grep {m.group(0)[:60]}"))

        # Pattern 2: awk '/KEY:/...' config
        for m in re.finditer(r"awk\s+'([^']+)'", block):
            pat = m.group(1)
            # Hlavní klíč v awk range: /timeout_bounds:/,/...
            for k in re.finditer(r"/(\w[\w_]+):", pat):
                key = k.group(1)
                # Filtr: ignoruj regex metaznaky (^, [^ ] apod.)
                if key not in ("if", "print", "NR", "NF", "FS", "OFS"):
                    refs.append((key, f"awk '{pat[:60]}'"))

    return refs


def check_skill_references(
    skill_dir: str,
    skill_name: str,
    config_keys: set[str],
    verbose: bool = False,
) -> list[str]:
    """Zkontroluje jeden skill a vrátí seznam chyb."""
    skill_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_path):
        return []

    blocks = extract_bash_blocks(skill_path)
    refs = extract_referenced_keys(blocks)
    errors = []

    for key, source in refs:
        if key not in config_keys:
            errors.append(f"FAIL: {skill_name} reads '{key}' but not in config.md — {source}")
        elif verbose:
            print(f"  OK: {skill_name} → {key}")

    return errors


def check_references_files(skill_dir: str, skill_name: str) -> list[str]:
    """Zkontroluje, že references/ zmíněné v SKILL.md existují."""
    skill_path = os.path.join(skill_dir, "SKILL.md")
    text = Path(skill_path).read_text()
    warnings = []

    # Najdi odkazy na references/*.md
    # Ignoruj: template/instruction lines a markdown code blocks
    # (builder/checker obsahují šablony pro jiné skilly)
    in_code_block = False
    for line in text.splitlines():
        if line.startswith("```"):
            # Toggle code block state; skip ```bash blocks (real code)
            # but detect ```markdown blocks (templates/examples)
            if not in_code_block and "markdown" in line:
                in_code_block = True
                continue
            elif in_code_block and line.strip() == "```":
                in_code_block = False
                continue
        if in_code_block:
            continue  # Skip references inside template code blocks
        if "→" in line or "${" in line:
            continue  # Skip instruction/template lines
        for m in re.finditer(r"references/([\w][\w-]*\.md)", line):
            ref_file = m.group(1)
            ref_path = os.path.join(skill_dir, "references", ref_file)
            if not os.path.exists(ref_path):
                warnings.append(f"WARN: {skill_name} references/{ref_file} — file missing")

    return warnings


def main():
    verbose = "--verbose" in sys.argv

    # Najdi root (fabric/config.md)
    root = os.getcwd()
    config_path = os.path.join(root, "fabric", "config.md")
    if not os.path.exists(config_path):
        print(f"ERROR: {config_path} not found. Run from project root.")
        sys.exit(1)

    config_keys = extract_config_keys(config_path)
    if verbose:
        print(f"Config keys ({len(config_keys)}): {sorted(config_keys)[:20]}...")

    skills_dir = os.path.join(root, "skills")
    all_errors = []
    all_warnings = []
    skill_count = 0

    for d in sorted(os.listdir(skills_dir)):
        if not d.startswith("fabric-"):
            continue
        skill_name = d.replace("fabric-", "")
        skill_path = os.path.join(skills_dir, d)
        skill_count += 1

        # T10: config key stale read
        errors = check_skill_references(skill_path, skill_name, config_keys, verbose)
        all_errors.extend(errors)

        # S10: references file existence
        warnings = check_references_files(skill_path, skill_name)
        all_warnings.extend(warnings)

    print(f"\n{'=' * 60}")
    print(f"T10 Config Key Stale Check — {skill_count} skills scanned")
    print(f"{'=' * 60}")

    if all_errors:
        for e in all_errors:
            print(e)
        print(f"\nT10: FAIL ({len(all_errors)} stale keys)")
    else:
        print("T10: PASS — all config keys valid")

    print()

    if all_warnings:
        for w in all_warnings:
            print(w)
        print(f"\nS10: WARN ({len(all_warnings)} missing references)")
    else:
        print("S10: PASS — all references/ files exist")

    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
