"""aiion/memory/cognitive_index.py — Rastrea archivos leídos/modificados en la sesión."""
import hashlib
from datetime import datetime
from aiion.cli.ui import c, CY, GR, PK, YL, OR, CO, BOLD

class CognitiveIndex:
    def __init__(self):
        self._read={}; self._written={}

    def mark_read(self, path, content=""):
        sha=hashlib.sha256(content.encode(errors="replace")).hexdigest()[:12]
        self._read[str(path)]={"sha":sha,"lines":content.count("\n")+1,"ts":datetime.now().isoformat()}

    def mark_written(self, path, action="write"):
        self._written[str(path)]={"action":action,"ts":datetime.now().isoformat()}

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
