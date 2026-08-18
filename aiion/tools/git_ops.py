"""
aiion/tools/git_ops.py — Wrapper de Git para el agente 'github'.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

REPOS = {
    "aiion": "/data/data/com.termux/files/home/AIION",
    "agentes": "/data/data/com.termux/files/home/work_repos/agentes",
    "blist": "/data/data/com.termux/files/home",
}


def _run(cmd: str, cwd: str | None = None) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip()[:4000],
            "stderr": result.stderr.strip()[:2000],
            "code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_git(action: str, args: dict) -> dict:
    repo_name = args.get("repo", "aiion")
    cwd = REPOS.get(repo_name)
    if cwd is None:
        return {"ok": False, "error": f"repositorio '{repo_name}' desconocido"}

    if action == "status":
        return _run("git status --short", cwd=cwd)
    if action == "log":
        n = args.get("n", 5)
        return _run(f"git log --oneline -{n}", cwd=cwd)
    if action == "branch":
        return _run("git branch -a", cwd=cwd)
    if action == "diff":
        return _run("git diff --stat", cwd=cwd)
    if action == "commit":
        msg = args.get("message", "AIION: auto-commit")
        # add + commit en uno
        return _run(f'git add -A && git commit -m "{msg}"', cwd=cwd)
    if action == "push":
        branch = args.get("branch", "")
        if branch:
            return _run(f"git push origin {branch}", cwd=cwd)
        return _run("git push", cwd=cwd)
    return {"ok": False, "error": f"acción git '{action}' no soportada"}
