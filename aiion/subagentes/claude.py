# ============================================================
# 🤖 SUBAGENTE: CLAUDE
# Agente de planificación y ejecución de proyectos reales
# Usa /plan, /doctor, /backup de AIION v0.2
# ============================================================
import sys, os, io, contextlib, time, json, subprocess
from pathlib import Path

# Integración con AIION
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from aiion.config import *
from aiion.llm.keys import STATE
from aiion.llm.client import TOOL_CALL_STATE
from aiion.cli.ui import *
from aiion.core import create_plan, do_backup, system_doctor

HOME = Path.home()
PLANS_DIR = HOME / "AIION" / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Definición de proyectos reales de la casa
# ============================================================
PROYECTOS = {
    "blistv12": {
        "titulo": "blistv12 — Versión modular nueva",
        "fases": {
            "F1": ["Auditar core actual blistv11.py (CodeInvestigator)",
                   "Listar funciones críticas a migrar",
                   "Diseñar arquitectura modular v12"],
            "F2": ["Extraer módulos: tools/, security/, llm/",
                   "Crear interfaces entre módulos",
                   "Implementar sistema de plugins"],
            "F3": ["Tests unitarios por módulo",
                   "Migrar skills, doctor, backup",
                   "Mantener blistv11 estable"],
            "F4": ["Sandbox de pruebas",
                   "Validar equivalencia con v11",
                   "Documentar migración"]
        }
    },
    "aiion_produccion": {
        "titulo": "AIION v0.2 — Paso a producción",
        "fases": {
            "F1": ["Planificación PHVA implementada (✓)",
                   "Sistema /plan operativo (✓)",
                   "Integración con Ollama Cloud (✓)"],
            "F2": ["Pulir CLI: colores, prompts, errores",
                   "Conectar con blistv11 vía MCP",
                   "Persistencia de planes en disco"],
            "F3": ["Tests de carga (28 keys pool)",
                   "Métricas de latencia y éxito",
                   "Auto-cura con circuit_breaker"],
            "F4": ["Documentación README completa",
                   "Empaquetar como ejecutable Termux",
                   "Distribuir a equipo"]
        }
    },
    "sara_cerebro": {
        "titulo": "SARA — Sistema nervioso digital",
        "fases": {
            "F1": ["nervio.py local activo (✓)",
                   "Sensores termux-api en tiempo real",
                   "Memoria persistente"],
            "F2": ["Conectar con blistv11 + AIION",
                   "Validación por palabra clave",
                   "Protocolo de permisos por usuario"],
            "F3": ["Auto-mejora continua (kaizen)",
                   "Reflexión épica (self_reflect)",
                   "Aprendizaje de errores"],
            "F4": ["Voz TTS natural",
                   "Visión nativa (sara_get_screen)",
                   "Control domótico básico"]
        }
    },
    "ecosistema_seguridad": {
        "titulo": "BLIST Security Shield",
        "fases": {
            "F1": ["Mapeo de superficie de ataque",
                   "Hardening de Termux sin root",
                   "Firewall de apps (netstat)"],
            "F2": ["Agente ciberseguridad (tech brain)",
                   "Detección de intrusiones",
                   "Auditoría de permisos por tool"],
            "F3": ["Protocolo de verificación con dialog",
                   "Encriptación de memoria persistente",
                   "Backup cifrado en Drive"],
            "F4": ["Pentesting controlado del propio sistema",
                   "Actualizaciones OTA seguras",
                   "Respuesta automática a amenazas"]
        }
    }
}

# ============================================================
# Lógica del subagente
# ============================================================
def generar_plan(nombre):
    if nombre not in PROYECTOS:
        disponibles = ", ".join(PROYECTOS.keys())
        print(c(YL, f"  ✗ Proyecto '{nombre}' no existe."))
        print(c(CO, f"  Disponibles: {disponibles}"))
        return False

    p = PROYECTOS[nombre]
    print(c(CY+BOLD, f"\n  🚀 Generando plan: {p['titulo']}"))
    print(c(CO, f"     Proyecto: {nombre}\n"))

    # 1) Backup antes de crear plan
    print(c(YL, "  ▸ Backup preventivo..."))
    do_backup("create")
    print()

    # 2) Crear plan en AIION
    create_plan(nombre)

    # 3) Marcar lo que ya está hecho en F1
    print(c(CY, f"\n  ▸ Análisis de avance previo..."))
    plan_file = PLANS_DIR / f"{nombre}.md"
    if plan_file.exists():
        content = plan_file.read_text(encoding='utf-8')
        # Cuenta fases con emojis de la plantilla
        import re
        done_matches = re.findall(r'- (✅|\[x\])', content)
        partial_matches = re.findall(r'- (🔄|\[~\]|\[partial\])', content)
        pending_matches = re.findall(r'- (⏳|\[ \])', content)
        total = len(done_matches) + len(partial_matches) + len(pending_matches)
        pct = (len(done_matches) * 100 // total) if total else 0
        print(c(GR, f"     ✓ {len(done_matches)} tareas hechas"))
        print(c(YL, f"     🔄 {len(partial_matches)} en progreso"))
        print(c(CO, f"     ⏳ {len(pending_matches)} pendientes"))
        # Gráfico ASCII de progreso
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(c(CY, f"\n     [{bar}] {pct}%"))

    return True

def reporte_completo():
    print(c(CY+BOLD, "\n  ╔════════════════════════════════════════════════════════╗"))
    print(c(CY+BOLD, "  ║  🤖 SUBAGENTE CLAUDE — REPORTE COMPLETO              ║"))
    print(c(CY+BOLD, "  ╚════════════════════════════════════════════════════════╝\n"))

    # 1) Estado del sistema
    print(c(PU+BOLD, "  📊 1. SALUD DEL SISTEMA"))
    print(c(CO, "  " + "─" * 50))
    system_doctor()

    # 2) Estado de los planes
    print(c(PU+BOLD, "\n  📋 2. ESTADO DE PLANES"))
    print(c(CO, "  " + "─" * 50))
    create_plan("list")

    # 3) Progreso por proyecto
    print(c(PU+BOLD, "\n  🎯 3. PROGRESO POR PROYECTO"))
    print(c(CO, "  " + "─" * 50))
    import re
    for nombre, info in PROYECTOS.items():
        plan_file = PLANS_DIR / f"{nombre}.md"
        if plan_file.exists():
            content = plan_file.read_text(encoding='utf-8')
            done = len(re.findall(r'- (✅|\[x\])', content))
            partial = len(re.findall(r'- (🔄|\[~\]|\[partial\])', content))
            pending = len(re.findall(r'- (⏳|\[ \])', content))
            total = done + partial + pending
            pct = (done * 100 // total) if total else 0
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            color = GR if pct == 100 else YL if pct > 30 else CO
            print(f"  {color}[{bar}] {pct:3d}%  {nombre:25s} ({done}/{total})")
        else:
            print(f"  {CO}[{'░'*20}]   0%  {nombre:25s} (sin plan)")

    # 4) Recomendaciones
    print(c(PU+BOLD, "\n  💡 4. RECOMENDACIONES"))
    print(c(CO, "  " + "─" * 50))
    planes = list(PLANS_DIR.glob("*.md"))
    if not planes:
        print(c(YL, "  ▸ No hay planes. Genera uno con: claude generar <proyecto>"))
    else:
        # Encontrar tareas pendientes más antiguas
        for plan_file in planes[:3]:
            content = plan_file.read_text(encoding='utf-8')
            mtime = plan_file.stat().st_mtime
            age_days = (time.time() - mtime) / 86400
            print(f"  ▸ {plan_file.stem}: creado hace {age_days:.1f} días")

    print(c(CY+BOLD, "\n  ════════════════════════════════════════════════════════"))
    print(c(GR, "  ✓ Reporte generado por Subagente Claude"))
    print(c(CY+BOLD, "  ════════════════════════════════════════════════════════\n"))

def ejecutar(proyecto=None, accion="generar"):
    """Comando principal del subagente."""
    if accion == "reporte" or proyecto is None:
        reporte_completo()
        return

    if accion == "generar":
        generar_plan(proyecto)
    elif accion == "show":
        create_plan(f"show {proyecto}")
    elif accion == "check":
        # claude check plan tarea estado
        # argumentos vienen como "plan F#.# estado"
        args = proyecto.split(maxsplit=2)
        if len(args) >= 3:
            create_plan(f"check {args[0]} {args[1]} {args[2]}")
        else:
            print(c(YL, "  ✗ Uso: claude check <plan> F#.# done|partial|pending"))
    else:
        print(c(YL, f"  ✗ Acción '{accion}' no reconocida"))

# ============================================================
# CLI del subagente
# ============================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Subagente Claude — Planificador AIION")
    parser.add_argument("comando", nargs="?", default="reporte",
                       help="reporte | generar | show | check")
    parser.add_argument("args", nargs=argparse.REMAINDER,
                       help="Argumentos adicionales")
    args = parser.parse_args()

    if args.comando == "generar" and args.args:
        ejecutar(args.args[0], "generar")
    elif args.comando == "show" and args.args:
        ejecutar(args.args[0], "show")
    elif args.comando == "check" and len(args.args) >= 1:
        ejecutar(" ".join(args.args), "check")
    else:
        reporte_completo()

if __name__ == "__main__":
    main()
