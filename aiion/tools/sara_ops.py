"""
aiion/tools/sara_ops.py — Wrapper Sara OS (WebSocket :7773, MCP HTTP).
"""
from __future__ import annotations
import asyncio
import json
import socket
import subprocess


SARA_WS = "ws://127.0.0.1:7773"


async def _ws_send(msg: str, timeout: float = 90.0) -> str:
    import websockets
    try:
        async with websockets.connect(SARA_WS, open_timeout=5, ping_interval=None) as ws:
            await ws.send(msg)
            resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
            return resp[:8000]
    except Exception as e:
        return f"[ERROR {type(e).__name__}] {e}"


def run_sara(action: str, args: dict) -> dict:
    if action == "ping":
        # Ping TCP al puerto WS
        try:
            s = socket.create_connection(("127.0.0.1", 7773), timeout=3)
            s.close()
            return {"ok": True, "online": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    if action == "send":
        msg = args.get("message", "ping")
        try:
            resp = asyncio.run(_ws_send(msg))
            return {"ok": True, "response": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    if action == "history":
        # lee WS_HISTORY vía el endpoint MCP si existe
        try:
            r = subprocess.run(
                ["curl", "-s", "http://127.0.0.1:7337/health"],
                capture_output=True, text=True, timeout=5
            )
            return {"ok": True, "health": r.stdout[:1000]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"acción sara '{action}' no soportada"}
