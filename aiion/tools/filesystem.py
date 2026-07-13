"""aiion/tools/filesystem.py — Tools de sistema de archivos, shell y búsqueda."""
import os, re, subprocess, urllib.request
from pathlib import Path
from aiion.memory.cognitive_index import COGINDEX

def tool_read_file(path, start_line=None, end_line=None):
    try:
        p=Path(path).expanduser()
        if not p.exists(): return f"Error: No existe: {path}"
        content=p.read_text(errors='replace')
        lines=content.splitlines()
        if start_line or end_line:
            s=(start_line or 1)-1; e=end_line or len(lines)
            lines=lines[s:e]
        COGINDEX.mark_read(path,content)
        return f"Archivo {path} ({len(lines)} líneas):\n"+"\n".join(f"{i+1:4}│ {l}" for i,l in enumerate(lines))
    except Exception as ex: return f"Error: {ex}"

def tool_write_file(path, content):
    try:
        p=Path(path).expanduser()
        if p.exists():
            p.with_suffix(p.suffix+".bak").write_text(p.read_text(errors='replace'))
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(content); COGINDEX.mark_written(path,"write")
        return f"OK: {path} escrito ({len(content)} bytes)"
    except Exception as ex: return f"Error: {ex}"

def tool_replace(path, old_str, new_str):
    try:
        p=Path(path).expanduser(); content=p.read_text(errors='replace')
        count=content.count(old_str)
        if count==0: return f"Error: Texto no encontrado en {path}"
        if count>1:  return f"Error: Texto aparece {count} veces — debe ser único"
        p.with_suffix(p.suffix+".bak").write_text(content)
        p.write_text(content.replace(old_str,new_str,1)); COGINDEX.mark_written(path,"replace")
        return f"OK: Reemplazo exitoso en {path}"
    except Exception as ex: return f"Error: {ex}"

def tool_run_shell_command(command, timeout=60):
    try:
        r=subprocess.run(command,shell=True,capture_output=True,text=True,timeout=timeout)
        parts=[]
        if r.stdout.strip(): parts.append(f"STDOUT:\n{r.stdout.strip()}")
        if r.stderr.strip(): parts.append(f"STDERR:\n{r.stderr.strip()}")
        if r.returncode:     parts.append(f"Exit: {r.returncode}")
        return "\n".join(parts) if parts else "OK: sin salida"
    except subprocess.TimeoutExpired: return f"Error: Timeout ({timeout}s)"
    except Exception as ex: return f"Error: {ex}"

def tool_list_directory(path, show_hidden=False):
    try:
        p=Path(path).expanduser()
        if not p.exists(): return f"Error: No existe: {path}"
        entries=sorted(p.iterdir(),key=lambda x:(x.is_file(),x.name))
        lines=[]
        for e in entries:
            if not show_hidden and e.name.startswith('.'): continue
            icon="📁" if e.is_dir() else "📄"
            size=f" {e.stat().st_size}B" if e.is_file() else ""
            lines.append(f"{icon} {e.name}{size}")
        return f"Dir {path} ({len(lines)} entradas):\n"+"\n".join(lines) if lines else f"{path}: vacío"
    except Exception as ex: return f"Error: {ex}"

def tool_glob(pattern, base_path="."):
    try:
        matches=sorted(Path(base_path).expanduser().glob(pattern))
        if not matches: return f"Sin resultados: {pattern}"
        return f"{len(matches)} archivos:\n"+"\n".join(str(m) for m in matches[:100])
    except Exception as ex: return f"Error: {ex}"

def tool_grep_search(pattern, path, recursive=True):
    try:
        flag="-r" if recursive else ""
        cmd=f"grep -n {flag} -E '{pattern}' '{path}' 2>/dev/null | head -60"
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=20)
        out=r.stdout.strip()
        return f"Resultados '{pattern}':\n{out}" if out else f"Sin coincidencias: {pattern}"
    except Exception as ex: return f"Error: {ex}"

def tool_web_fetch(url, max_chars=4000):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=20) as r:
            content=r.read().decode('utf-8',errors='replace')
        content=re.sub(r'<style[^>]*>.*?</style>','',content,flags=re.DOTALL)
        content=re.sub(r'<script[^>]*>.*?</script>','',content,flags=re.DOTALL)
        content=re.sub(r'<[^>]+>','',content)
        content=re.sub(r'\n{3,}','\n\n',content).strip()
        return content[:max_chars]+("\n...[truncado]" if len(content)>max_chars else "")
    except Exception as ex: return f"Error: {ex}"

def tool_diff_files(path_a, path_b="", context_lines=3):
    try:
        pa=Path(path_a).expanduser()
        if not pa.exists(): return f"Error: No existe: {path_a}"
        pb=pa.with_suffix(pa.suffix+".bak") if not path_b else Path(path_b).expanduser()
        if not pb.exists(): return f"No hay backup de {path_a}. Pasa path_b explícito."
        r=subprocess.run(f"diff -u '{pb}' '{pa}'|head -120",
                         shell=True,capture_output=True,text=True,timeout=15)
        return f"Diff {pb}→{pa}:\n{r.stdout.strip()}" if r.stdout.strip() else "Archivos idénticos."
    except Exception as ex: return f"Error: {ex}"

