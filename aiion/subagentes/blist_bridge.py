"""
aiion/subagentes/blist_bridge.py — Subagente que conecta AIION con blistv11 vía MCP.

Uso:
  python aiion/subagentes/blist_bridge.py status
  python aiion/subagentes/blist_bridge.py tools [filtro]
  python aiion/subagentes/blist_bridge.py call <tool> [json_args]
  python aiion/subagentes/blist_bridge.py connect [url] [api_key]
  python aiion/subagentes/blint_bridge.py demo
  python aiion/subagentes/blist_bridge.py health
  python aiion/subagentes/blist_bridge.py sync    # sincroniza planes entre AIION y blist
"""
import sys, json
from pathlib import Path

# Permitir import relativo
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aiion.cli.ui import c, CY, GR, YL, RE, PU, CO, BOLD, DIM
from aiion.mcp.client import get_client, cmd_mcp

BANNER = """
╔════════════════════════════════════════════════════════╗
║  🌉 SUBAGENTE BLIST-BRIDGE — AIION ↔ blistv11 (MCP)    ║
╚════════════════════════════════════════════════════════╝
"""

def _hr():
    print(c(CO, "  " + "─" * 56))


def main():
    args = sys.argv[1:]
    action = args[0] if args else "status"
    rest   = args[1:]

    print(c(CY + BOLD, BANNER))
    cli = get_client()

    if action == "status":
        print(c(PU + BOLD, "  📊 1. ESTADO DE CONEXIÓN"))
        _hr()
        print(cli.report())

    elif action == "ping":
        print(c(PU + BOLD, "  🏓  PING"))
        _hr()
        r = cli.ping()
        if "error" in r:
            print(c(RE, f"  ✗ {r['error']}"))
        else:
            print(c(GR, f"  ✓ {r}"))

    elif action == "tools":
        filtro = rest[0] if rest else ""
        print(c(PU + BOLD, "  🔧 TOOLS DISPONIBLES" + (f" (filtro: {filtro})" if filtro else "")))
        _hr()
        tools = cli.list_tools(use_cache=False)
        if not tools:
            print(c(RE, "  ✗ No se pudieron obtener tools"))
            return
        for t in tools:
            n = t.get("name", "?")
            if filtro and filtro.lower() not in n.lower():
                continue
            d = (t.get("description", "") or "")[:80]
            schema = t.get("inputSchema", {}).get("properties", {})
            params = ", ".join(schema.keys()) if schema else "(sin params)"
            print(c(CY, f"  • {n:30s} ") + c(CO, f"— {d}"))
            if schema:
                print(c(DIM, f"      params: {params}"))

    elif action == "call":
        if not rest:
            print(c(RE, "  ✗ Uso: call <tool> [json_args]"))
            return
        tool_name = rest[0]
        tool_args = {}
        if len(rest) >= 2:
            try:
                tool_args = json.loads(" ".join(rest[1:]))
            except json.JSONDecodeError as e:
                print(c(RE, f"  ✗ Args inválidos: {e}"))
                return
        print(c(PU + BOLD, f"  📞 EJECUTANDO: {tool_name}"))
        _hr()
        r = cli.call_tool(tool_name, tool_args)
        if "error" in r:
            print(c(RE, f"  ✗ {r['error']}"))
        else:
            content = r.get("content", r)
            if isinstance(content, list):
                text = "\n".join(c2.get("text", str(c2)) for c2 in content)
                print(text)
            else:
                print(json.dumps(content, indent=2, ensure_ascii=False)
                      if isinstance(content, (dict, list)) else str(content))

    elif action == "connect":
        url = rest[0] if rest else "http://127.0.0.1:7337/mcp"
        key = rest[1] if len(rest) > 1 else ""
        print(c(PU + BOLD, "  🔌 CONFIGURANDO CONEXIÓN"))
        _hr()
        print(cli.set("url", url))
        if key:
            print(cli.set("api_key", key))
        print()
        print(cli.refresh())

    elif action == "health":
        print(c(PU + BOLD, "  🩺 SALUD DE BLISTv11"))
        _hr()
        if not cli.is_online():
            print(c(RE, "  ✗ blistv11 no está online en " + cli.config["url"]))
            return
        info = cli.info()
        if "error" not in info:
            print(c(GR, "  ✓ Handshake MCP exitoso"))
            print(json.dumps(info, indent=2, ensure_ascii=False))
        status = cli.status(use_cache=False)
        if "error" not in status:
            print()
            print(c(CY + BOLD, "  Estado del agente:"))
            for k, v in status.items():
                print(f"    {k:12s} : {v}")

    elif action == "demo":
        print(c(PU + BOLD, "  🎬 DEMO — Conectando AIION con blistv11"))
        _hr()
        print(c(CY, "  1) Ping..."))
        r = cli.ping()
        print(c(GR if "error" not in r else RE, f"     {r}"))
        if "error" in r:
            print(c(YL, "  ⚠ Inicia blistv11 con: blistv11.py → /mcp_server start"))
            return

        print(c(CY, "  2) Info del servidor..."))
        info = cli.info()
        if "error" not in info:
            si = info.get("serverInfo", {})
            print(c(GR, f"     {si.get('name','?')} v{si.get('version','?')}"))

        print(c(CY, "  3) Status..."))
        status = cli.status(use_cache=False)
        if "error" not in status:
            print(c(GR, f"     Tools: {status.get('tools','?')}, "
                        f"Health: {status.get('health','?')}, "
                        f"Batería: {status.get('battery','?')}%"))

        print(c(CY, "  4) Listando primeras 10 tools..."))
        tools = cli.list_tools(use_cache=False)
        for t in tools[:10]:
            print(c(CO, f"     • {t.get('name','?')}"))
        rest = len(tools) - 10
        if rest > 0:
            print(c(DIM, f"     ... y {rest} más"))

        print()
        print(c(GR + BOLD, "  ✓ Integración AIION ↔ blistv11 operativa"))

    elif action == "sync":
        print(c(PU + BOLD, "  🔄 SYNC — Sincronizando planes con blist"))
        _hr()
        # Empuja el reporte AIION a blist usando call write_note
        try:
            from aiion.subagentes.claude import reporte as _reporte
            txt = _reporte()
        except Exception as e:
            txt = f"Reporte AIION no disponible: {e}"
        r = cli.call_tool("write_note", {
            "title":   "AIION sync",
            "content": txt[:4000],
            "category": "aiion"
        })
        if "error" in r:
            print(c(RE, f"  ✗ {r['error']}"))
        else:
            print(c(GR, "  ✓ Plan/reporte sincronizado con blistv11"))

    else:
        print(c(YL, f"  Acción '{action}' no reconocida."))
        print(c(CY, "  Comandos: status, ping, tools [filtro], call <tool> <json>,"))
        print(c(CY, "            connect [url] [key], health, demo, sync"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c(YL, "\n  Interrumpido"))
    except Exception as e:
        print(c(RE, f"\n  ✗ Error: {e}"))
        import traceback
        traceback.print_exc()
