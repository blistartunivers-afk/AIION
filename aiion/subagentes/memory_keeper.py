"""
aiion/subagentes/memory_keeper.py — Subagente guardián de memoria L2/L3.

Operaciones de mantenimiento sobre la memoria persistente:
  - stats          → tamaño, número de entradas, distribución por tipo
  - top            → top N entradas por score TF-IDF
  - search         → búsqueda semántica (delegada a memory)
  - prune          → elimina entradas duplicadas / más viejas que N días
  - export         → exporta memoria a JSON (backup legible)
  - snapshot       → snapshot timestamped en data/backups/
  - self_check     → verifica integridad (ficheros legibles, schema OK)

Capabilities:
  - stats
  - top
  - search
  - prune
  - export
  - snapshot
  - self_check
"""
from __future__ import annotations
import json
import time
import shutil
from pathlib import Path
import sys

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiion.subagentes.base import Subagente, subagente


@subagente
class MemoryKeeper(Subagente):
    name = "memory_keeper"
    description = "Guardián de memoria: stats, búsqueda, poda, export, snapshot"
    version = "0.1"
    capabilities = [
        "stats",
        "top",
        "search",
        "prune",
        "export",
        "snapshot",
        "self_check",
    ]

    def handle(self, capability: str, args: dict) -> dict:
        if capability == "stats":
            return self._stats()
        if capability == "top":
            return self._top(int(args.get("n", 5)))
        if capability == "search":
            return self._search(args.get("query", ""),
                                int(args.get("limit", 10)))
        if capability == "prune":
            return self._prune(int(args.get("older_than_days", 365)))
        if capability == "export":
            return self._export(args.get("path"))
        if capability == "snapshot":
            return self._snapshot()
        if capability == "self_check":
            return self._self_check()
        raise ValueError(f"capability '{capability}' no implementada")

    # --------- implementations ---------
    def _data_dir(self) -> Path:
        try:
            from aiion.config import DATA_DIR  # type: ignore
            return Path(DATA_DIR)
        except Exception:
            return _ROOT / "data"

    def _stats(self) -> dict:
        """Lee aiion_memory.md + aiion_history.jsonl y da métricas."""
        data = self._data_dir()
        out = {"data_dir": str(data), "memory_md": None, "history": None}

        mem = data / "aiion_memory.md"
        if mem.exists():
            txt = mem.read_text(encoding="utf-8", errors="ignore")
            lines = [l for l in txt.splitlines() if l.strip()]
            entries = sum(1 for l in lines if l.lstrip().startswith("- "))
            out["memory_md"] = {
                "size_bytes": mem.stat().st_size,
                "lines": len(lines),
                "entries": entries,
            }

        hist = data / "aiion_history.jsonl"
        if hist.exists():
            n = 0
            last_ts = None
            try:
                with open(hist, "r", encoding="utf-8") as f:
                    for line in f:
                        n += 1
                        try:
                            obj = json.loads(line)
                            ts = obj.get("ts")
                            if ts and (last_ts is None or ts > last_ts):
                                last_ts = ts
                        except Exception:
                            pass
            except Exception as e:
                out["history_error"] = str(e)
            out["history"] = {
                "size_bytes": hist.stat().st_size,
                "entries": n,
                "last_ts": last_ts,
            }

        out["checked_at"] = time.time()
        return out

    def _top(self, n: int) -> dict:
        try:
            from aiion.memory.persistence import top_facts  # type: ignore
            return {"items": top_facts(n)}
        except Exception as e:
            return {"items": [], "error": str(e)}

    def _search(self, query: str, limit: int) -> dict:
        if not query.strip():
            raise ValueError("query vacío")
        try:
            from aiion.memory.persistence import search_history  # type: ignore
            return {"query": query, "results": search_history(query, limit)}
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    def _prune(self, older_than_days: int) -> dict:
        """Marca entradas con timestamp > N días (no borra, solo reporta)."""
        cutoff = time.time() - older_than_days * 86400
        hist = self._data_dir() / "aiion_history.jsonl"
        if not hist.exists():
            return {"pruned": 0, "cutoff_ts": cutoff, "reason": "history vacío"}
        old_count = 0
        new_count = 0
        with open(hist, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get("ts", 0) < cutoff:
                        old_count += 1
                    else:
                        new_count += 1
                except Exception:
                    old_count += 1
        return {
            "would_prune": old_count,
            "would_keep": new_count,
            "cutoff_ts": cutoff,
            "older_than_days": older_than_days,
            "note": "dry-run (no borra)",
        }

    def _export(self, path: str | None) -> dict:
        data = self._data_dir()
        dest = Path(path) if path else (data / f"export_{int(time.time())}.json")
        export = {"exported_at": time.time(), "items": []}
        mem = data / "aiion_memory.md"
        if mem.exists():
            export["memory_md"] = mem.read_text(encoding="utf-8", errors="ignore")
        hist = data / "aiion_history.jsonl"
        if hist.exists():
            with open(hist, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        export["items"].append(json.loads(line))
                    except Exception:
                        pass
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
            return {"path": str(dest), "size_bytes": dest.stat().st_size,
                    "items": len(export["items"])}
        except Exception as e:
            return {"error": str(e)}

    def _snapshot(self) -> dict:
        """Copia memoria y history a data/backups/snapshot_YYYYMMDD_HHMMSS/."""
        data = self._data_dir()
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = data / "backups" / f"snapshot_{ts}"
        try:
            dest.mkdir(parents=True, exist_ok=True)
            copied = []
            for fname in ("aiion_memory.md", "aiion_history.jsonl",
                          "cognito_index.json"):
                src = data / fname
                if src.exists():
                    shutil.copy2(src, dest / fname)
                    copied.append(fname)
            return {"path": str(dest), "copied": copied, "ts": ts}
        except Exception as e:
            return {"error": str(e)}

    def _self_check(self) -> dict:
        out = {"ok": True, "checks": []}
        data = self._data_dir()
        for fname in ("aiion_memory.md", "aiion_history.jsonl"):
            p = data / fname
            check = {"file": fname, "exists": p.exists()}
            if p.exists():
                try:
                    if fname.endswith(".jsonl"):
                        with open(p, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        valid = sum(1 for l in lines
                                    if l.strip() and (l.strip().startswith("{")
                                                      or l.strip().startswith("gA")))
                        check["lines"] = len(lines)
                        check["valid_jsonl"] = valid
                    else:
                        txt = p.read_text(encoding="utf-8")
                        check["lines"] = len(txt.splitlines())
                except Exception as e:
                    check["error"] = str(e)
                    out["ok"] = False
            else:
                out["ok"] = False
            out["checks"].append(check)
        out["ts"] = time.time()
        return out
