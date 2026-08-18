"""
aiion/tools/drive_ops.py — Wrapper de rclone para el agente 'drive'.
"""
from __future__ import annotations
import subprocess
import shlex

REMOTE = "gdrive"


def _run(cmd: str) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip()[:4000],
            "stderr": result.stderr.strip()[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_drive(action: str, args: dict) -> dict:
    path = args.get("path", "")
    target = f"{REMOTE}:{path}".rstrip(":")

    if action == "list":
        return _run(f"rclone lsd {shlex.quote(target)}")
    if action == "tree":
        depth = args.get("depth", 2)
        return _run(f"rclone tree {shlex.quote(target)} --max-depth {depth}")
    if action == "pull":
        local = args.get("local", "/tmp/drive_pull")
        return _run(f"rclone copy {shlex.quote(target)} {shlex.quote(local)}")
    if action == "push":
        local = args.get("local", ".")
        return _run(f"rclone copy {shlex.quote(local)} {shlex.quote(target)}")
    if action == "sync":
        local = args.get("local", ".")
        # sync = borra en destino lo que no esté en origen (cuidado)
        return _run(f"rclone sync {shlex.quote(local)} {shlex.quote(target)} --dry-run")
    return {"ok": False, "error": f"acción drive '{action}' no soportada"}
