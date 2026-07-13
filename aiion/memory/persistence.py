"""aiion/memory/persistence.py — Memoria persistente L2 (texto) y L3 (historial JSONL + TF-IDF)."""
import json, re
from datetime import datetime
from aiion.config import MEMORY_FILE, HISTORY_FILE, MAX_HISTORY

def memory_load():
    return MEMORY_FILE.read_text(errors='replace').strip() if MEMORY_FILE.exists() else ""

def memory_append(fact):
    existing=memory_load(); now=datetime.now().strftime("%Y-%m-%d")
    block=f"\n- [{now}] {fact.strip()}"
    if fact.strip() not in existing:
        MEMORY_FILE.write_text(existing+block+"\n")

def history_save(user_input, agent_response):
    entry={"ts":datetime.now().isoformat(),"user":user_input,"agent":agent_response}
    with open(HISTORY_FILE,"a",encoding="utf-8") as f:
        f.write(json.dumps(entry,ensure_ascii=False)+"\n")

def history_load_all():
    if not HISTORY_FILE.exists(): return []
    entries=[]
    with open(HISTORY_FILE,"r",encoding="utf-8") as f:
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

def history_search(query, top_k=MAX_HISTORY):
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
