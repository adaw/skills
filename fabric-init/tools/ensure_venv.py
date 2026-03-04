#!/usr/bin/env python3
"""
ensure_venv.py — Lazy venv manager for Fabric projects.

Logika:
- Pokud .venv neexistuje → vytvoří + nainstaluje deps
- Pokud pyproject.toml/requirements.txt změněn (hash) → pip install
- Jinak → skip (rychlé)

Použití:
  python skills/fabric-init/tools/ensure_venv.py [--repo-root .] [--dep-root <path>] [--venv .venv] [--quiet]
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# --- Platform helpers ---

_IS_WIN = sys.platform == "win32"


def _venv_bin(venv_path: Path, name: str) -> Path:
    if _IS_WIN:
        return venv_path / "Scripts" / (name + ".exe")
    return venv_path / "bin" / name


# --- File locking ---

@contextlib.contextmanager
def _lock(lock_path: Path):
    if _IS_WIN:
        yield
        return
    import fcntl
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


# --- TOML dev-extras detection ---

def _has_dev_extras(pyproject: Path) -> bool:
    """Return True if pyproject defines a PEP 621 optional-dependency group named 'dev'.

    Note: Poetry dev-dependencies are NOT installable via pip extras. We handle baseline tooling
    separately after the main install to keep ensure_venv portable (no poetry dependency).
    """
    try:
        data = _parse_toml(pyproject)
    except Exception:
        return False
    opt_deps = data.get("project", {}).get("optional-dependencies", {})
    return isinstance(opt_deps, dict) and ("dev" in opt_deps)



def _parse_toml(path: Path) -> dict:
    text = path.read_bytes()
    try:
        import tomllib
        return tomllib.loads(text.decode())
    except ImportError:
        pass
    import tomli
    return tomli.loads(text.decode())


# --- Core logic ---

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
    kwargs: dict = {"cwd": cwd}
    if quiet:
        kwargs["capture_output"] = True
    return subprocess.run(cmd, **kwargs).returncode
def _ensure_baseline_tools(repo_root: Path, venv_path: Path, pip: Path, quiet: bool) -> None:
    """Best-effort install of baseline dev tools used by Fabric commands.

    Keeps COMMANDS like `pytest` / `ruff` usable even when the project doesn't declare them
    as pip-installable extras (common with Poetry projects). Non-fatal by design.
    """
    baseline_tools = ["pytest", "ruff"]
    missing = [t for t in baseline_tools if not _venv_bin(venv_path, t).exists()]
    if not missing:
        return
    log("[ensure_venv] Installing baseline tools: " + ", ".join(missing) + "...")
    tools_rc = run([str(pip), "install", *missing], repo_root, quiet)
    if tools_rc != 0:
        print(
            f"[ensure_venv] WARNING: baseline tools install failed (rc={tools_rc}): {', '.join(missing)}",
            file=sys.stderr,
        )
    else:
        log("[ensure_venv] Baseline tools ready ✓")




def _log(msg: str, quiet: bool, *, force_stderr: bool = False) -> None:
    if not quiet:
        dest = sys.stderr if force_stderr else sys.stdout
        print(msg, file=dest)


def ensure_venv(
    repo_root: Path,
    venv_path: Path,
    quiet: bool,
    *,
    dep_root: Path | None = None,
    stderr_progress: bool = False,
) -> bool:
    def log(msg: str) -> None:
        _log(msg, quiet, force_stderr=stderr_progress)

    dep_root = dep_root or repo_root
    dep_files = find_dep_files(dep_root)
    current_hash = hash_files(*dep_files) if dep_files else "no-deps"

    venv_python = _venv_bin(venv_path, "python")
    hash_file = venv_path / ".fabric_deps_hash"

    broken_symlink = venv_python.is_symlink() and not venv_python.exists()
    venv_exists = venv_python.exists()
    stored_hash = hash_file.read_text().strip() if hash_file.exists() else ""

    if venv_exists and stored_hash == current_hash:
        log("[ensure_venv] venv OK, deps unchanged — skip")
        # Still ensure baseline tools (best-effort).
        pip = _venv_bin(venv_path, "pip")
        _ensure_baseline_tools(repo_root, venv_path, pip, quiet)
        return False

    need_create = not venv_exists or broken_symlink

    if need_create:
        if broken_symlink:
            log("[ensure_venv] Broken python symlink detected, recreating with --clear...")
            venv_cmd = [sys.executable, "-m", "venv", "--clear", str(venv_path)]
        else:
            log(f"[ensure_venv] Creating venv at {venv_path}...")
            venv_cmd = [sys.executable, "-m", "venv", str(venv_path)]
        rc = run(venv_cmd, repo_root, quiet)
        if rc != 0:
            raise RuntimeError(f"[ensure_venv] ERROR: venv creation failed (rc={rc})")

    pip = _venv_bin(venv_path, "pip")

    # pip upgrade — warn on failure
    pip_up_rc = run([str(pip), "install", "--upgrade", "pip"], repo_root, quiet=True)
    if pip_up_rc != 0:
        print(f"[ensure_venv] WARNING: pip upgrade failed (rc={pip_up_rc})", file=sys.stderr)

    rc = 0
    has_pyproject = (repo_root / "pyproject.toml").exists()
    has_requirements = (repo_root / "requirements.txt").exists()
    has_setup = (repo_root / "setup.py").exists() or (repo_root / "setup.cfg").exists()

    if has_pyproject:
        log("[ensure_venv] Installing pyproject.toml deps...")
        extras = ".[dev]" if _has_dev_extras(repo_root / "pyproject.toml") else "."
        rc = run([str(pip), "install", "-e", extras], dep_root, quiet)
    elif has_requirements:
        log("[ensure_venv] Installing requirements.txt...")
        rc = run([str(pip), "install", "-r", "requirements.txt"], dep_root, quiet)
        if rc == 0 and (repo_root / "requirements-dev.txt").exists():
            rc = run([str(pip), "install", "-r", "requirements-dev.txt"], dep_root, quiet)
    elif has_setup:
        log("[ensure_venv] Installing setup.py/setup.cfg via pip install -e ...")
        rc = run([str(pip), "install", "-e", "."], dep_root, quiet)
    else:
        log("[ensure_venv] No dep files found — empty venv created")
        rc = 0

    if rc != 0:
        raise RuntimeError(f"[ensure_venv] ERROR: pip install failed (rc={rc})")

    _ensure_baseline_tools(repo_root, venv_path, pip, quiet)

    hash_file.parent.mkdir(parents=True, exist_ok=True)
    hash_file.write_text(current_hash)

    log("[ensure_venv] venv ready ✓")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure project venv is up to date")
    parser.add_argument("--repo-root", default=".", help="Path to repo root (base for venv path)")
    parser.add_argument("--dep-root", default=None, help="Dependency root (pyproject/requirements). Defaults to repo-root.")
    parser.add_argument("--venv", default=".venv", help="Venv directory name/path (relative to repo-root unless absolute)")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument("--json", dest="json_out", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.json_out:
        args.quiet = True

    repo_root = Path(args.repo_root).resolve()
    dep_root = Path(args.dep_root).resolve() if args.dep_root else repo_root
    venv_path = Path(args.venv) if Path(args.venv).is_absolute() else repo_root / args.venv

    lock_path = venv_path.parent / (venv_path.name + ".lock")

    try:
        with _lock(lock_path):
            updated = ensure_venv(
                repo_root,
                venv_path,
                args.quiet,
                dep_root=dep_root,
                stderr_progress=args.json_out,
            )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if args.json_out:
        print(json.dumps({
            "status": "updated" if updated else "ok",
            "venv": str(venv_path),
            "dep_root": str(dep_root),
            "repo_root": str(repo_root),
        }))


if __name__ == "__main__":
    main()