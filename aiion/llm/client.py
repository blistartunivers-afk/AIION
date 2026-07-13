"""aiion/llm/client.py — Cliente HTTP hacia Ollama (local o cloud), tool-calling nativo y fallback ReAct."""
import json, re, urllib.request, urllib.error
from aiion.config import OLLAMA_LOCAL, OLLAMA_CLOUD
from aiion.llm.keys import STATE, current_key, rotate_key
from aiion.tools.registry import TOOLS

# Se detecta automáticamente; se puede forzar con /toolmode on|off
TOOL_CALL_STATE = {"native": True}  # True=intentar nativo, False=forzar ReAct

def _build_payload(messages, use_tools=True):
    base = {"model": STATE["model"], "messages": messages, "stream": False}
    if use_tools:
        base["tools"] = TOOLS
    if STATE["use_cloud"]:
        base["options"] = {"temperature": 0.1}
    else:
        base["options"] = {"temperature": 0.1, "num_ctx": 8192}
    return json.dumps(base).encode()

def _do_request(payload, retry=0):
    if STATE["use_cloud"]:
        req = urllib.request.Request(
            f"{OLLAMA_CLOUD}/api/chat", data=payload,
            headers={"Content-Type":"application/json",
                     "Authorization":f"Bearer {current_key()}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401,429) and len(STATE["api_keys"])>1 and retry<len(STATE["api_keys"]):
                rotate_key()
                return _do_request(payload, retry=retry+1)
            raise
    else:
        req = urllib.request.Request(
            f"{OLLAMA_LOCAL}/api/chat", data=payload,
            headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())

def chat_native(messages, retry=0):
    """Llama con tool calling nativo. Retorna (tipo, datos).
       tipo='tool_call' → datos=[(name,args,id), ...]
       tipo='text'      → datos=str
    """
    payload = _build_payload(messages, use_tools=True)
    resp    = _do_request(payload, retry=retry)
    msg     = resp.get("message", {})
    calls   = msg.get("tool_calls") or []
    if calls:
        parsed = []
        for tc in calls:
            fn   = tc.get("function", {})
            name = fn.get("name","")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except: args = {}
            parsed.append((name, args, tc.get("id","")))
        return ("tool_call", parsed, msg)
    return ("text", msg.get("content",""), msg)

def chat_react_text(messages, retry=0):
    """Llama SIN tools (ReAct texto plano). Retorna string."""
    payload = _build_payload(messages, use_tools=False)
    resp    = _do_request(payload, retry=retry)
    return resp.get("message",{}).get("content","")

def parse_react(text):
    """Parser ReAct de fallback."""
    m = re.search(
        r'[Aa]ccion\s*:\s*(\w+)\s*\n[Pp]arametros\s*:\s*(\{.*?\})\s*(?=\n[A-ZÁÉÍÓÚ]|\Z)',
        text, re.DOTALL)
    if not m:
        m = re.search(r'[Aa]ccion\s*:\s*(\w+)\s*\n[Pp]arametros\s*:\s*(\{[^}]*\})',
                      text, re.DOTALL)
    if m:
        name = m.group(1).strip(); raw = m.group(2).strip()
        try: args = json.loads(raw)
        except:
            try: args = json.loads(raw.replace("'",'"'))
            except: args = {}
        th = re.search(r'[Pp]ensamiento\s*:\s*(.+?)(?=\n[Aa]ccion)', text, re.DOTALL)
        return ("action", name, args, th.group(1).strip() if th else "")
    resp = re.search(r'[Rr]espuesta\s*:\s*(.+)', text, re.DOTALL)
    if resp: return ("final", resp.group(1).strip())
    return ("final", text.strip())

