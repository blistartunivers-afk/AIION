"""aiion/llm/client.py — Cliente HTTP hacia Ollama (local o cloud), tool-calling nativo y fallback ReAct."""
import json, re, time, urllib.request, urllib.error
from aiion.config import OLLAMA_LOCAL, OLLAMA_CLOUD, GEMINI_API
from aiion.llm.keys import STATE, current_key, rotate_key, record_key_failure, _key_candidates
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


def _messages_to_gemini(messages):
    system = []
    contents = []
    for message in messages:
        role = message.get("role")
        if role == "system":
            system.append(message.get("content", ""))
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": message.get("content", "")}]})
        elif role == "assistant":
            parts = []
            if message.get("content"):
                parts.append({"text": message["content"]})
            for call in message.get("tool_calls", []) or []:
                function = call.get("function", {})
                args = function.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                parts.append({"functionCall": {"name": function.get("name", ""),
                                                "args": args}})
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        elif role == "tool":
            contents.append({"role": "user", "parts": [{"functionResponse": {
                "name": message.get("name", ""),
                "response": {"result": message.get("content", "")}}}]})
    return "\n".join(system).strip(), contents


def _gemini_body(messages, use_tools):
    system, contents = _messages_to_gemini(messages)
    body = {"contents": contents, "generationConfig": {"temperature": 0.1}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if use_tools:
        body["tools"] = [{"functionDeclarations": [
            {"name": entry["function"]["name"],
             "description": entry["function"].get("description", ""),
             "parameters": entry["function"].get("parameters", {"type": "object", "properties": {}})}
            for entry in TOOLS]}]
    return body


def _do_request_gemini(messages, use_tools=True, retry=0, retry_5xx=0):
    model = STATE["model"]
    request = urllib.request.Request(
        f"{GEMINI_API}/{model}:generateContent",
        data=json.dumps(_gemini_body(messages, use_tools)).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": current_key()},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code in (401, 402, 403, 404, 410, 429):
            try:
                delay = max(0.0, float(error.headers.get("Retry-After", ""))) if error.headers else 0.0
            except (TypeError, ValueError):
                delay = 0.0
            if error.code == 429:
                body = error.read().decode("utf-8", "ignore")
                if "PerDay" in body or "limit: 0" in body:
                    delay = max(delay, 3600)
                else:
                    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)
                    if match:
                        delay = max(delay, float(match.group(1)) + 1)
            record_key_failure(error.code, delay)
            error.close()
            if retry < min(12, max(3, len(STATE["api_keys"]) * len(_key_candidates()))):
                rotate_key()
                return _do_request_gemini(messages, use_tools, retry + 1)
        if error.code in (500, 502, 503, 504) and retry_5xx < 2:
            time.sleep(1.5 * (retry_5xx + 1))
            return _do_request_gemini(messages, use_tools, retry, retry_5xx + 1)
        raise


def _gemini_parts(response):
    candidates = response.get("candidates") or []
    if not candidates:
        reason = response.get("promptFeedback", {}).get("blockReason", "vacío")
        raise RuntimeError(f"Gemini sin respuesta ({reason})")
    return candidates[0].get("content", {}).get("parts", [])

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
            if e.code in (401, 402, 403, 404, 410, 429):
                try:
                    delay = max(0.0, float(e.headers.get("Retry-After", ""))) if e.headers else 0.0
                except (TypeError, ValueError):
                    delay = 0.0
                record_key_failure(e.code, delay)
                e.close()
                if retry >= min(12, max(3, len(STATE["api_keys"]) * len(_key_candidates()))):
                    raise
                rotate_key()
                body = json.loads(payload)
                body["model"] = STATE["model"]
                return _do_request(json.dumps(body).encode(), retry=retry+1)
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
    if STATE.get("provider") == "gemini":
        parts = _gemini_parts(_do_request_gemini(messages, use_tools=True))
        calls, text = [], ""
        for part in parts:
            if "functionCall" in part:
                call = part["functionCall"]
                name = call.get("name", "")
                calls.append((name, call.get("args", {}) or {}, name))
            elif "text" in part:
                text += part["text"]
        message = {"content": text, "tool_calls": [
            {"function": {"name": name, "arguments": args}, "id": call_id}
            for name, args, call_id in calls]}
        return ("tool_call", calls, message) if calls else ("text", text, message)
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
    if STATE.get("provider") == "gemini":
        parts = _gemini_parts(_do_request_gemini(messages, use_tools=False))
        return "".join(part.get("text", "") for part in parts)
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

