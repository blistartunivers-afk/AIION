"""
aiion/api.py — API REST + WebSocket para AIION (F2.5).

Expone el orquestador y los recursos principales (memoria, audit, agentes)
vía HTTP/JSON. Diseñado para correr en localhost (`127.0.0.1` por defecto).

NO requiere root. NO expone nada fuera de loopback salvo configuración.

Stack: aiohttp (ligero, async, ya instalado).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from aiohttp import web

from aiion.orchestrator import get_orchestrator, CapabilityError, Task
from aiion import config

log = logging.getLogger("aiion.api")

# ──────────────────────────────────────────────────────────────────────
# Configuración de seguridad
# ──────────────────────────────────────────────────────────────────────

API_TOKEN: str = os.environ.get("AIION_API_TOKEN", "").strip()

# Rate limit simple: {ip: [timestamps]}
_rate_buckets: Dict[str, list] = {}
RATE_LIMIT_PER_MIN = int(os.environ.get("AIION_API_RATELIMIT", "120"))


def _client_ip(req: web.Request) -> str:
    return req.remote or "unknown"


def _check_rate_limit(req: web.Request) -> bool:
    """Token bucket por minuto por IP. Devuelve True si está OK."""
    now = time.time()
    ip = _client_ip(req)
    bucket = _rate_buckets.setdefault(ip, [])
    # purga > 60s
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= RATE_LIMIT_PER_MIN:
        return False
    bucket.append(now)
    return True


# ──────────────────────────────────────────────────────────────────────
# Middleware de autenticación
# ──────────────────────────────────────────────────────────────────────

@web.middleware
async def auth_middleware(req: web.Request, handler):
    """Si la ruta requiere auth, valida Bearer token."""
    # Rutas públicas
    public = {"/health", "/status", "/agents", "/ws"}  # /ws hace su propia auth
    if req.path in public:
        return await handler(req)

    # Sin token configurado en el entorno → denegar todo lo protegido
    if not API_TOKEN:
        return web.json_response(
            {"error": "API token no configurado (AIION_API_TOKEN)"},
            status=503,
        )

    # Rate limit
    if not _check_rate_limit(req):
        return web.json_response(
            {"error": "rate limit exceeded"},
            status=429,
        )

    # Bearer token
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return web.json_response(
            {"error": "missing Authorization: Bearer <token>"},
            status=401,
        )
    token = auth[7:].strip()
    if token != API_TOKEN:
        log.warning("auth.fail ip=%s path=%s", _client_ip(req), req.path)
        return web.json_response({"error": "invalid token"}, status=401)

    return await handler(req)


# ──────────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────────

async def handle_health(req: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "service": "aiion-api",
        "version": config.VERSION,
        "ts": time.time(),
    })


async def handle_status(req: web.Request) -> web.Response:
    """Estado global del agente (sistema + orquestador)."""
    orch = get_orchestrator()
    return web.json_response({
        "version": config.VERSION,
        "uptime": orch.stats(),
        "agents": [orch.describe(n) and {
            "name": n,
            "description": orch.describe(n).description,
            "capabilities": orch.describe(n).capabilities,
            "enabled": orch.describe(n).enabled,
        } for n in orch.list_agents()],
    })


async def handle_agents(req: web.Request) -> web.Response:
    orch = get_orchestrator()
    out = []
    for name in orch.list_agents():
        spec = orch.describe(name)
        out.append({
            "name": name,
            "description": spec.description,
            "capabilities": spec.capabilities,
            "required_tools": spec.required_tools,
        })
    return web.json_response({"agents": out, "total": len(out)})


async def handle_memory(req: web.Request) -> web.Response:
    """GET /memory — listar últimas N entradas."""
    from aiion.memory.persistence import memory_load
    limit = int(req.query.get("limit", "50"))
    raw = memory_load() or ""
    lines = [ln for ln in raw.splitlines() if ln.strip()][-limit:]
    return web.json_response({"lines": lines, "count": len(lines)})


async def handle_memory_search(req: web.Request) -> web.Response:
    """GET /memory/search?q=...&limit=20"""
    from aiion.memory.persistence import history_search
    q = req.query.get("q", "").strip()
    if not q:
        return web.json_response({"error": "missing q"}, status=400)
    limit = int(req.query.get("limit", "20"))
    hits = history_search(q) or []
    hits = hits[:limit]
    return web.json_response({"query": q, "hits": hits, "count": len(hits)})


async def handle_plan(req: web.Request) -> web.Response:
    """POST /plan — ejecutar una tarea puntual (agent+action+args).
    Body: {"agent":"core","action":"memory_recall","args":{...}}
    """
    try:
        body = await req.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON"}, status=400)

    agent = body.get("agent")
    action = body.get("action")
    args = body.get("args") or {}

    if not agent or not action:
        return web.json_response(
            {"error": "agent and action required"},
            status=400,
        )

    orch = get_orchestrator()
    try:
        task = await asyncio.get_event_loop().run_in_executor(
            None, orch.submit, agent, action, args
        )
    except CapabilityError as e:
        return web.json_response({"error": str(e)}, status=403)

    status_code = 200 if task.status.value == "success" else 400
    if task.status.value == "denied":
        status_code = 403
    return web.json_response(task.to_dict(), status=status_code)


async def handle_plan_get(req: web.Request) -> web.Response:
    """GET /plan/{id} — buscar task en historial."""
    task_id = req.match_info["id"]
    orch = get_orchestrator()
    for t in orch.history:
        if t.id == task_id:
            return web.json_response(t.to_dict())
    return web.json_response({"error": "task not found"}, status=404)


async def handle_audit(req: web.Request) -> web.Response:
    """GET /audit?tail=50 — últimos eventos."""
    orch = get_orchestrator()
    n = int(req.query.get("tail", "20"))
    n = max(1, min(n, 500))  # clamp
    events = orch.audit.tail(n)
    return web.json_response({"events": events, "count": len(events)})


async def handle_stats(req: web.Request) -> web.Response:
    """GET /stats — métricas del orquestador."""
    orch = get_orchestrator()
    return web.json_response(orch.stats())


# ──────────────────────────────────────────────────────────────────────
# WebSocket — stream simple de audit
# ──────────────────────────────────────────────────────────────────────

async def handle_ws(req: web.Request) -> web.WebSocketResponse:
    """WS /ws — envía eventos del audit log en vivo (polling)."""
    if API_TOKEN:
        # token en query (?token=) o header (no soportado en ws desde browser)
        token = req.query.get("token", "")
        if token != API_TOKEN:
            return web.json_response({"error": "invalid token"}, status=401)

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(req)
    log.info("ws.open ip=%s", _client_ip(req))

    orch = get_orchestrator()
    last_size = 0
    last_ping = time.time()

    try:
        while not ws.closed:
            # Poll audit log cada 1.5s
            await asyncio.sleep(1.5)

            try:
                size = orch.audit.path.stat().st_size
            except FileNotFoundError:
                size = 0

            if size > last_size:
                with orch.audit.path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(last_size)
                    new_data = f.read()
                last_size = size
                for ln in new_data.splitlines():
                    if not ln.strip():
                        continue
                    try:
                        ev = json.loads(ln)
                    except json.JSONDecodeError:
                        continue
                    await ws.send_json({"type": "audit", "data": ev})

            # Heartbeat
            if time.time() - last_ping > 25:
                await ws.send_json({"type": "ping", "ts": time.time()})
                last_ping = time.time()
    finally:
        log.info("ws.close ip=%s", _client_ip(req))
    return ws


# ──────────────────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware])

    # Públicas
    app.router.add_get("/health",  handle_health)
    app.router.add_get("/status",  handle_status)
    app.router.add_get("/agents",  handle_agents)

    # Protegidas (Bearer token)
    app.router.add_get("/memory",            handle_memory)
    app.router.add_get("/memory/search",     handle_memory_search)
    app.router.add_post("/plan",             handle_plan)
    app.router.add_get("/plan/{id}",         handle_plan_get)
    app.router.add_get("/audit",             handle_audit)
    app.router.add_get("/stats",             handle_stats)
    app.router.add_get("/ws",                handle_ws)

    return app


# ──────────────────────────────────────────────────────────────────────
# Test helpers (exportables)
# ──────────────────────────────────────────────────────────────────────

def reset_for_tests() -> None:
    """Limpia el rate limit (entre tests)."""
    _rate_buckets.clear()


def set_token_for_tests(token: str) -> None:
    """Permite que test_api.py inyecte token sin tocar env."""
    global API_TOKEN
    API_TOKEN = token
