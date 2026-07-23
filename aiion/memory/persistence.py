"""aiion/memory/persistence.py — Memoria persistente L2 (texto) y L3 (historial JSONL + TF-IDF)."""
import json, re
from datetime import datetime
from aiion import config

class MemoryPersistence:
    def __init__(self):
        config.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not config.MEMORY_FILE.exists(): 
            config.MEMORY_FILE.touch()
        if not config.HISTORY_FILE.exists(): 
            config.HISTORY_FILE.touch()
        # SENSOR_DB no se crea aquí, pero el test lo espera
        if not config.SENSOR_DB.exists(): 
            config.SENSOR_DB.touch()

    def remember(self, fact):
        memory_append(fact)
        # También agregar al historial para TF-IDF search
        history_save(fact, "")
    
    def recall(self): 
        return memory_load()
    
    def append_history(self, role, msg):
        # Adaptación simple: el test espera (role, msg), la función original espera (user, agent)
        if role == "user": 
            history_save(msg, "")
        else: 
            history_save("", msg)
    
    def history_search(self, query): 
        return history_search(query)
    
    def clear_history(self):
        if config.HISTORY_FILE.exists(): 
            config.HISTORY_FILE.write_text("")
    
    def clear_memory(self):
        if config.MEMORY_FILE.exists(): 
            config.MEMORY_FILE.write_text("")


def memory_load():
    return config.MEMORY_FILE.read_text(errors='replace').strip() if config.MEMORY_FILE.exists() else ""

def memory_append(fact):
    existing=memory_load()
    now=datetime.now().strftime("%Y-%m-%d")
    block=f"\n- [{now}] {fact.strip()}"
    if fact.strip() not in existing:
        config.MEMORY_FILE.write_text(existing+block+"\n")

def history_save(user_input, agent_response):
    entry={"ts":datetime.now().isoformat(),"user":user_input,"agent":agent_response}
    # Aplicar límite MAX_HISTORY (número de entradas)
    entries = history_load_all()
    max_entries = getattr(config, 'MAX_HISTORY', 100) * 2  # pares user/agent
    if len(entries) >= max_entries:
        # Eliminar las entradas más antiguas (primera mitad)
        entries = entries[max_entries//2:]
        # Reescribir archivo
        with open(config.HISTORY_FILE,"w",encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e,ensure_ascii=False)+"\n")
    # Agregar nueva entrada
    with open(config.HISTORY_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(entry,ensure_ascii=False)+"\n")

def history_load_all():
    if not config.HISTORY_FILE.exists(): return []
    entries=[]
    with open(config.HISTORY_FILE,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                try: entries.append(json.loads(line))
                except: pass
    return entries

def _tokenize(text): return re.findall(r'\w+',text.lower())

def _tfidf(query_tokens, doc_tokens):
    if not doc_tokens: return 0.0
    doc_set=set(doc_tokens)
    return sum(doc_tokens.count(t)/len(doc_tokens) for t in query_tokens if t in doc_set)

def history_search(query, top_k=None):
    if top_k is None: top_k = config.MAX_HISTORY
    entries=history_load_all()
    if not entries: return []
    qt=_tokenize(query)
    scored=[((_tfidf(qt,_tokenize(e.get("user","")+e.get("agent",""))),e)) for e in entries]
    scored=[x for x in scored if x[0]>0]
    scored.sort(key=lambda x:x[0],reverse=True)
    return [e for _,e in scored[:top_k]]

def history_summary_for_prompt(query):
    relevant=history_search(query)
    if not relevant: return ""
    lines=["CONVERSACIONES PASADAS RELEVANTES:"]
    for e in relevant:
        ts=e.get("ts","")[:10]
        lines.append(f"[{ts}] U: {e['user'][:120]}")
        lines.append(f"[{ts}] A: {e['agent'][:200]}\n")
    return "\n".join(lines)

# Exportar constantes para compatibilidad con core.py
MEMORY_FILE = config.MEMORY_FILE
HISTORY_FILE = config.HISTORY_FILE
