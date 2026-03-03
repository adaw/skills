#!/usr/bin/env python3
"""
ensure_venv.py — Lazy venv manager for Fabric projects.

Logika:
- Pokud .venv neexistuje → vytvoří + nainstaluje deps
- Pokud pyproject.toml/requirements.txt změněn (hash) → pip install
- Jinak → skip (rychlé)

Použití:
  python skills/fabric-init/tools/ensure_venv.py [--repo-root .] [--venv .venv] [--quiet]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


HASH_FILE = ".venv/.fabric_deps_hash"


def hash_files(*paths: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def find_dep_files(repo_root: Path) -> list[Path]:
    candidates = [
        repo_root / "pyproject.toml",
        repo_root / "requirements.txt",
        repo_root / "requirements-dev.txt",
        repo_root / "setup.py",
        repo_root / "setup.cfg",
    ]
    return [p for p in candidates if p.exists()]


def run(cmd: list[str], cwd: Path, quiet: bool) -> int:
    kwargs = {"cwd": cwd}
    if quiet:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs).returncode


def ensure_venv(repo_root: Path, venv_path: Path, quiet: bool) -> bool:
    """
    Returns True if venv was created/updated, False if skipped.
    """
    dep_files = find_dep_files(repo_root)
    current_hash = hash_files(*dep_files) if dep_files else "no-deps"

    venv_python = venv_path / "bin" / "python"
    hash_file = repo_root / HASH_FILE

    venv_exists = venv_python.exists()
    stored_hash = hash_file.read_text().strip() if hash_file.exists() else ""

    if venv_exists and stored_hash == current_hash:
        if not quiet:
            print(f"[ensure_venv] venv OK, deps unchanged — skip")
        return False

    # Create venv if missing
    if not venv_exists:
        if not quiet:
            print(f"[ensure_venv] Creating venv at {venv_path}...")
        rc = run([sys.executable, "-m", "venv", str(venv_path)], repo_root, quiet)
        if rc != 0:
            print(f"[ensure_venv] ERROR: venv creation failed (rc={rc})", file=sys.stderr)
            sys.exit(rc)

    pip = venv_path / "bin" / "pip"

    # Upgrade pip silently
    run([str(pip), "install", "--upgrade", "pip"], repo_root, quiet=True)

    # Install deps
    if (repo_root / "pyproject.toml").exists():
        if not quiet:
            print(f"[ensure_venv] Installing pyproject.toml deps...")
        extras = ".[dev]" if _has_dev_extras(repo_root / "pyproject.toml") else "."
        rc = run([str(pip), "install", "-e", extras], repo_root, quiet)
    elif (repo_root / "requirements.txt").exists():
        if not quiet:
            print(f"[ensure_venv] Installing requirements.txt...")
        rc = run([str(pip), "install", "-r", "requirements.txt"], repo_root, quiet)
        if rc == 0 and (repo_root / "requirements-dev.txt").exists():
            rc = run([str(pip), "install", "-r", "requirements-dev.txt"], repo_root, quiet)
    else:
        if not quiet:
            print(f"[ensure_venv] No dep files found — empty venv created")
        rc = 0

    if rc != 0:
        print(f"[ensure_venv] ERROR: pip install failed (rc={rc})", file=sys.stderr)
        sys.exit(rc)

    # Save hash
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    hash_file.write_text(current_hash)

    if not quiet:
        print(f"[ensure_venv] venv ready ✓")
    return True


def _has_dev_extras(pyproject: Path) -> bool:
    try:
        content = pyproject.read_text()
        return "[project.optional-dependencies]" in content or '[tool.poetry.dev-dependencies]' in content
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Ensure project venv is up to date")
    parser.add_argument("--repo-root", default=".", help="Path to repo root")
    parser.add_argument("--venv", default=".venv", help="Venv directory name/path")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument("--json", dest="json_out", action="store_true", help="JSON output")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    venv_path = Path(args.venv) if Path(args.venv).is_absolute() else repo_root / args.venv

    updated = ensure_venv(repo_root, venv_path, args.quiet)

    if args.json_out:
        print(json.dumps({
            "status": "updated" if updated else "ok",
            "venv": str(venv_path),
            "repo_root": str(repo_root),
        }))


if __name__ == "__main__":
    main()
