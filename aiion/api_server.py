"""
aiion/api_server.py — Entry point del servidor HTTP AIION.

Uso:
    AIION_API_TOKEN=secreto python -m aiion.api_server
    AIION_API_TOKEN=secreto python -m aiion.api_server --host 127.0.0.1 --port 8765

Por defecto:
    host: 127.0.0.1 (loopback, NO exponer a LAN)
    port: 8765
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from aiohttp import web

from aiion.api import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="AIION API server")
    parser.add_argument("--host", default=os.environ.get("AIION_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("AIION_API_PORT", "8765")))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    token = os.environ.get("AIION_API_TOKEN", "").strip()
    if not token:
        print("⚠️  AIION_API_TOKEN no definido. Endpoints protegidos devolverán 503.",
              file=sys.stderr)
    else:
        print(f"🔐 API token cargado ({len(token)} chars)")

    app = create_app()
    print(f"🎼 AIION API escuchando en http://{args.host}:{args.port}")
    print("   Rutas públicas:  /health /status /agents")
    print("   Rutas protegidas: /memory /plan /audit /stats /ws")
    web.run_app(app, host=args.host, port=args.port, print=lambda *a, **k: None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
