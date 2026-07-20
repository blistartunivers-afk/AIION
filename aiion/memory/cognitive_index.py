"""aiion/memory/cognitive_index.py — Rastrea archivos leídos/modificados en la sesión."""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from aiion.cli.ui import c, CY, GR, PK, YL, OR, CO, BOLD

INDEX_FILE = Path("~/.aiion/cognitive_index.json").expanduser()

class CognitiveIndex:
    def __init__(self):
        self._read={}; self._written={}
        self._load()

    def _load(self):
        if INDEX_FILE.exists():
            try:
                data = json.loads(INDEX_FILE.read_text())
                self._read = data.get('read', {})
                self._written = data.get('written', {})
            except: pass

    def _save(self):
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps({'read': self._read, 'written': self._written}))

    def record_read(self, path, content=""):
        self.mark_read(path, content)

    def record_write(self, path, action="write"):
        self.mark_written(path, action)

    def get_indexed_files(self):
        result = {}
        all_paths = set(self._read.keys()) | set(self._written.keys())
        for p in all_paths:
            reads = self._read.get(p, {}).get('count', 0)
            writes = self._written.get(p, {}).get('count', 0)
            result[p] = {'reads': reads, 'writes': writes}
        return result

    def clear(self):
        self._read = {}; self._written = {}
        self._save()

    def get_recent_files(self, limit=10):
        all_files = []
        for p, m in self._read.items():
            all_files.append((p, m.get('ts', '')))
        all_files.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in all_files[:limit]]

    def mark_read(self, path, content=""):
        p = str(path)
        if p in self._read:
            self._read[p]['count'] = self._read[p].get('count', 1) + 1
        else:
            sha=hashlib.sha256(content.encode(errors="replace")).hexdigest()[:12]
            self._read[p]={"sha":sha,"lines":content.count("\n")+1,"ts":datetime.now().isoformat(),"count":1}
        self._save()

    def mark_written(self, path, action="write"):
        p = str(path)
        if p in self._written:
            self._written[p]['count'] = self._written[p].get('count', 1) + 1
        else:
            self._written[p]={"action":action,"ts":datetime.now().isoformat(),"count":1}
        self._save()

    def was_read(self,path): return str(path) in self._read

    def summary(self):
        lines=[f"{c(CY+BOLD,'📂 Índice cognitivo:')}"]
        if self._read:
            lines.append(f"  {c(GR,'Leídos')} ({len(self._read)}):")
            for p,m in self._read.items():
                tag = f"[{m['lines']}L sha:{m['sha']}]"
                lines.append(f"    {c(CO,p)}  {c(YL,tag)}")
        if self._written:
            lines.append(f"  {c(PK,'Modificados')} ({len(self._written)}):")
            for p,m in self._written.items():
                tag = f"[{m['action']} @ {m['ts'][:16]}]"
                lines.append(f"    {c(CO,p)}  {c(OR,tag)}")
        if not self._read and not self._written:
            lines.append(f"  {c(CO,'(vacío)')}")
        return "\n".join(lines)

    def context_block(self):
        if not self._read and not self._written: return ""
        parts=[]
        if self._read:
            parts.append("ARCHIVOS YA LEÍDOS:\n"+"\n".join(f"  - {p}" for p in self._read))
        if self._written:
            parts.append("ARCHIVOS MODIFICADOS:\n"+"\n".join(f"  - {p}" for p in self._written))
        return "\n".join(parts)

COGINDEX = CognitiveIndex()
