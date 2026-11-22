"""aiion/llm/client.py — Cliente HTTP hacia Ollama (local o cloud), tool-calling nativo y fallback ReAct."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime

from aiion.config import (
    GEMINI_API, GEMINI_MODELS, NVIDIA_API, NVIDIA_MODEL, OLLAMA_CLOUD,
    OLLAMA_LOCAL, PREFERRED_MODELS,
)
from aiion.llm.keys import (
    STATE, PoolCooldownError, _key_candidates, current_key, current_route_available,
    load_api_keys, load_gemini_keys, load_nvidia_keys, record_key_failure, rotate_key,
)
from aiion.tools.registry import TOOLS

# Se detecta automáticamente; se puede forzar con /toolmode on|off
TOOL_CALL_STATE = {"native": True}  # True=intentar nativo, False=forzar ReAct

def _build_payload(messages, use_tools=True):
    messages = [{key: value for key, value in message.items()
                 if key not in ("gemini_parts", "gemini_model")} for message in messages]
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
            if message.get("gemini_parts") and message.get("gemini_model") == STATE["model"]:
                contents.append({"role": "model", "parts": message["gemini_parts"]})
                continue
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
            part = {"functionResponse": {"name": message.get("name", ""),
                                         "response": {"result": message.get("content", "")}}}
            if contents and "functionResponse" in contents[-1]["parts"][0]:
                contents[-1]["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})
    return "\n".join(system).strip(), contents


def _gemini_body(messages, use_tools):
    system, contents = _messages_to_gemini(messages)
    body = {"contents": contents, "generationConfig": {"temperature": 0.1}}
    level = STATE.get("thinking_level", "medium")
    model = STATE["model"]
    if level not in ("default", "off") and model.startswith("gemini-3"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": level.upper()}
    elif model.startswith("gemini-2.5"):
        budget = {"off": 0, "minimal": 128, "low": 1024, "medium": 4096, "high": 8192}.get(level)
        if budget is not None:
            body["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": max(128, budget) if "pro" in model else budget}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if use_tools:
        body["tools"] = [{"functionDeclarations": [
            {"name": entry["function"]["name"],
             "description": entry["function"].get("description", ""),
             "parameters": entry["function"].get("parameters", {"type": "object", "properties": {}})}
            for entry in TOOLS]}]
    return body

def _read_json(request):
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def _with_pool(send, retry=0):
    cloud = STATE["use_cloud"] or STATE["provider"] in ("gemini", "nvidia")
    limit = min(12, max(3, len(STATE["api_keys"]) * len(_key_candidates()))) if cloud else 3
    if cloud and not current_route_available():
        rotate_key()
    while True:
        try:
            return send()
        except urllib.error.HTTPError as error:
            status = error.code
            with error:
                body = error.read(16384).decode("utf-8", "replace") if error.fp else ""
            retry_after = error.headers.get("Retry-After", "0") if error.headers else "0"
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                try:
                    delay = parsedate_to_datetime(retry_after).timestamp() - time.time()
                except (TypeError, ValueError, OverflowError):
                    delay = 0
            if status == 429:
                match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)
                if match:
                    delay = max(delay, float(match.group(1)) + 1)
                if "PerDay" in body or "limit: 0" in body:
                    delay = max(delay, 3600)
            failure = error
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            status, delay = 0, 0
            failure = RuntimeError(f"Fallo de conexión · {STATE['provider']} · {STATE['model']}")

        transient = status in (0, 500, 502, 503, 504, 529)
        if cloud and (transient or status in (401, 402, 403, 404, 410, 429)):
            record_key_failure(status, delay)
            if retry + 1 >= limit:
                raise PoolCooldownError(
                    f"Reintentos agotados · {STATE['provider']} · {failure}") from None
            else:
                try:
                    rotate_key()
                except PoolCooldownError as error:
                    if not transient:
                        raise PoolCooldownError(f"HTTP {status} · {error}") from None
                else:
                    retry += 1
                    continue
        if transient and retry + 1 < limit and retry < 2:
            retry += 1
            print(f"  {failure} · reintento {retry}/{limit - 1}", flush=True)
            time.sleep(0.5 * retry)
            continue
        if cloud and transient:
            raise PoolCooldownError(f"Reintentos agotados · {STATE['provider']} · {failure}") from None
        raise failure


def _nvidia_request(messages, use_tools):
    def send():
        body = {"model": STATE["model"], "messages": messages, "stream": False, "temperature": 0.1}
        if use_tools:
            body["tools"] = TOOLS
        return _read_json(urllib.request.Request(
            NVIDIA_API, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {current_key()}"},
            method="POST"))

    return _with_pool(send)["choices"][0]["message"]


def _do_request_gemini(messages, use_tools=True, retry=0):
    def send():
        body = _gemini_body(messages, use_tools)
        def request():
            return _read_json(urllib.request.Request(
                f"{GEMINI_API}/{STATE['model']}:generateContent",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "x-goog-api-key": current_key()},
                method="POST"))
        try:
            return request()
        except urllib.error.HTTPError as error:
            if error.code != 400 or "thinkingConfig" not in body["generationConfig"]:
                raise
            error.close()
            print("  Gemini HTTP 400 · reintentando con el razonamiento predeterminado", flush=True)
            del body["generationConfig"]["thinkingConfig"]
            return request()

    return _with_pool(send, retry)


def _gemini_parts(response):
    candidates = response.get("candidates") or []
    if not candidates:
        reason = response.get("promptFeedback", {}).get("blockReason", "vacío")
        raise RuntimeError(f"Gemini sin respuesta ({reason})")
    return candidates[0].get("content", {}).get("parts", [])

def _do_request(payload, retry=0):
    body = json.loads(payload)

    def send():
        headers = {"Content-Type": "application/json"}
        endpoint = OLLAMA_CLOUD if STATE["use_cloud"] else OLLAMA_LOCAL
        if STATE["use_cloud"]:
            headers["Authorization"] = f"Bearer {current_key()}"
        body["model"] = STATE["model"]
        return _read_json(urllib.request.Request(
            f"{endpoint}/api/chat", data=json.dumps(body).encode(),
            headers=headers, method="POST"))

    return _with_pool(send, retry)


def chat_native(messages, retry=0):
    """Llama con tool calling nativo. Retorna (tipo, datos).
       tipo='tool_call' → datos=[(name,args,id), ...]
       tipo='text'      → datos=str
    """
    if STATE.get("provider") == "nvidia":
        msg = _nvidia_request(messages, True)
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            calls.append((fn.get("name", ""), args, tc.get("id", "")))
        return ("tool_call", calls, msg) if calls else ("text", msg.get("content") or "", msg)
    if STATE.get("provider") == "gemini":
        parts = _gemini_parts(_do_request_gemini(messages, use_tools=True))
        calls, text = [], ""
        for part in parts:
            if "functionCall" in part:
                call = part["functionCall"]
                name = call.get("name", "")
                calls.append((name, call.get("args", {}) or {}, name))
            elif "text" in part and not part.get("thought"):
                text += part["text"]
        message = {"content": text, "tool_calls": [
            {"function": {"name": name, "arguments": args}, "id": call_id}
            for name, args, call_id in calls],
            "gemini_parts": parts, "gemini_model": STATE["model"]}
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

def _chat_react_text(messages, retry=0):
    """Convierte el historial nativo a texto antes de pedir una respuesta ReAct."""
    messages = [
        {"role": "user", "content": f"Observación ({m.get('name', 'herramienta')}): {m.get('content', '')}"}
        if m["role"] == "tool" else
        {"role": m["role"], "content": m.get("content") or ", ".join(
            call["function"]["name"] for call in (m.get("tool_calls") or []))}
        for m in messages
    ]
    if STATE.get("provider") == "nvidia":
        return _nvidia_request(messages, False).get("content") or ""
    if STATE.get("provider") == "gemini":
        parts = _gemini_parts(_do_request_gemini(messages, use_tools=False))
        return "".join(part.get("text", "") for part in parts if not part.get("thought"))
    payload = _build_payload(messages, use_tools=False)
    resp    = _do_request(payload, retry=retry)
    return resp.get("message",{}).get("content","")

def chat_react_text(messages, retry=0):
    try:
        return _chat_react_text(messages, retry)
    except PoolCooldownError:
        if not STATE["use_cloud"]:
            raise
        configured = os.environ.get("AIION_FALLBACK_PROVIDERS", "")
        routes = {
            "ollama": (load_api_keys, PREFERRED_MODELS[0]),
            "gemini": (load_gemini_keys, GEMINI_MODELS[0]),
            "nvidia": (load_nvidia_keys, NVIDIA_MODEL),
        }
        fields = ("provider", "model", "api_keys", "key_index")
        previous = {field: STATE[field] for field in fields}
        for provider in dict.fromkeys(name.strip().lower() for name in configured.split(",")):
            if provider == previous["provider"] or provider not in routes:
                continue
            load_keys, model = routes[provider]
            keys = load_keys()
            if not keys:
                continue
            STATE.update(provider=provider, model=model, api_keys=keys, key_index=0)
            success = False
            try:
                print(f"  Pool agotado · probando {provider} en ReAct")
                answer = _chat_react_text(messages)
                success = bool((answer or "").strip())
                if success:
                    return answer
            except (urllib.error.HTTPError, RuntimeError):
                continue
            finally:
                if not success:
                    STATE.update(previous)
        raise


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

