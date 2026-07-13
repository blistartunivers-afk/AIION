#!/usr/bin/env python3
"""
aiion_keys.py — Gestor del pool de API Keys de Ollama Cloud para AIION
════════════════════════════════════════════════════════════════════
Administra las keys que AIION usa en modo Nube (Ollama Cloud).

Guarda en:  ~/AIION/data/ollama_keys        (formato plano, una key por línea)
Cachea en:  ~/AIION/data/ollama_keys_cache.json  (modelos detectados por key)

Este formato es 100% compatible con lo que `aiion_core.py` espera leer
via `load_api_keys()` — no requiere ningún cambio en el agente principal.
AIION carga este pool automáticamente al iniciar en modo Nube y rota
entre las keys disponibles.

Solo depende de la librería estándar de Python (urllib), igual que el
resto de AIION — sin paquetes externos.
"""
import os, sys, json, time
from pathlib import Path
import urllib.request, urllib.error

# ══════════════════════════════════════════════════════════════════════════════
# PALETA DRÁCULA (misma que aiion_core.py, para consistencia visual)
# ══════════════════════════════════════════════════════════════════════════════
R       = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

D_CYAN    = "\033[38;2;139;233;253m"    # #8BE9FD
D_GREEN   = "\033[38;2;80;250;123m"     # #50FA7B
D_YELLOW  = "\033[38;2;241;250;140m"    # #F1FA8C
D_ORANGE  = "\033[38;2;255;184;108m"    # #FFB86C
D_RED     = "\033[38;2;255;85;85m"      # #FF5555
D_PINK    = "\033[38;2;255;121;198m"    # #FF79C6
D_PURPLE  = "\033[38;2;189;147;249m"    # #BD93F9
D_COMMENT = "\033[38;2;98;114;164m"     # #6272A4

CY = D_CYAN; GR = D_GREEN; YL = D_YELLOW
OR = D_ORANGE; RE = D_RED; PK = D_PINK
PU = D_PURPLE; CO = D_COMMENT

def c(col, txt): return f"{col}{txt}{R}"
def cls(): os.system("clear")
def hr(n=52, col=CO): return c(col, "─" * n)

BANNER = f"""
{c(PU+BOLD,'╔══════════════════════════════════════════════════╗')}
{c(PU+BOLD,'║')}  {c(PK+BOLD,'AIION')} — {c(CY+BOLD,'Gestor de Keys · Ollama Cloud')}          {c(PU+BOLD,'║')}
{c(PU+BOLD,'╚══════════════════════════════════════════════════╝')}
"""

# ══════════════════════════════════════════════════════════════════════════════
# RUTAS — mismas que usa aiion_core.py
# ══════════════════════════════════════════════════════════════════════════════
from aiion.config import AIION_HOME

KEYS_FILE  = AIION_HOME / "ollama_keys"        # leído directamente por aiion_core.py
CACHE_FILE = AIION_HOME / "ollama_keys_cache.json"  # solo lo usa este gestor

OLLAMA_CLOUD  = "https://ollama.com"
CODE_HINTS    = ["coder","code","deepseek","qwen3","starcoder"]

# ══════════════════════════════════════════════════════════════════════════════
# HTTP (stdlib puro, igual que aiion_core.py)
# ══════════════════════════════════════════════════════════════════════════════
def http_get(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), r.status

def fetch_modelos(key: str):
    """Retorna (lista_modelos, error_str) consultando Ollama Cloud."""
    try:
        data, status = http_get(
            f"{OLLAMA_CLOUD}/api/tags",
            headers={"Authorization": f"Bearer {key}"},
        )
        if status != 200:
            return [], f"HTTP {status}"
        modelos = [m.get("name", "") for m in data.get("models", [])]
        return modelos, None
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}"
    except Exception as e:
        return [], str(e)[:80]

# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCIA — keys en texto plano (compatible con aiion_core.load_api_keys)
# ══════════════════════════════════════════════════════════════════════════════
def cargar_keys() -> list:
    if not KEYS_FILE.exists():
        return []
    return [l.strip() for l in KEYS_FILE.read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]

def guardar_keys(keys: list):
    KEYS_FILE.write_text("\n".join(keys) + ("\n" if keys else ""))

def cargar_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except Exception:
        return {}

def guardar_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

def mostrar_key(key: str) -> str:
    if len(key) > 16:
        return f"{key[:10]}...{key[-4:]}"
    return key[:4] + "***"

# ══════════════════════════════════════════════════════════════════════════════
# PANTALLAS
# ══════════════════════════════════════════════════════════════════════════════
def pantalla_principal():
    cls()
    keys  = cargar_keys()
    cache = cargar_cache()
    print(BANNER)

    if not keys:
        print(c(DIM, "  Sin keys configuradas todavía.\n"))
    else:
        for i, k in enumerate(keys, 1):
            meta   = cache.get(k, {})
            n_mods = len(meta.get("modelos", []))
            mods_str = c(GR, f"{n_mods} modelos") if n_mods else c(CO, "sin modelos cacheados")
            print(f"  {c(YL, str(i)+'.')} {c(CY, mostrar_key(k))}  {mods_str}")
        print(f"\n  {c(CO, hr(30))} {c(BOLD, f'Total: {len(keys)} keys')}\n")

    print(f"  {c(BOLD,'1.')} Agregar key")
    print(f"  {c(BOLD,'2.')} Eliminar key")
    print(f"  {c(BOLD,'3.')} Ver modelos de una key")
    print(f"  {c(BOLD,'4.')} Probar todas las keys")
    print(f"  {c(BOLD,'5.')} Actualizar modelos (fetch en vivo)")
    print(f"  {c(BOLD,'6.')} Ver keys completas")
    print(f"  {c(BOLD,'0.')} Salir\n")

    try:
        return input(c(PU+BOLD, "  Elige: ")).strip()
    except (KeyboardInterrupt, EOFError):
        return "0"

def agregar_key():
    cls()
    print(f"""
{c(PU+BOLD,'── Agregar Key de Ollama Cloud ──────────────')}

  {c(CY,'Obtén tu key en:')} {c(CO,'ollama.com/settings/api-keys')}

  {c(CO,'Escribe 0 para cancelar.')}
""")
    keys  = cargar_keys()
    cache = cargar_cache()

    while True:
        try:
            nueva = input(c(PU+BOLD, "  Pega tu key: ")).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if nueva == "0":
            return
        if len(nueva) < 8:
            print(c(RE, "  Key demasiado corta.")); continue
        if nueva in keys:
            print(c(YL, "  Esa key ya está en el pool.")); continue

        print(f"  {c(CO,'Verificando y obteniendo modelos...')}", flush=True)
        t0 = time.time()
        modelos, err = fetch_modelos(nueva)
        ms = int((time.time() - t0) * 1000)

        if err:
            print(f"  {c(RE,'✗')} Error: {c(CO, err)}")
            modelos = []
        else:
            print(f"  {c(GR,'✓')} {c(BOLD, str(len(modelos)))} modelos en {c(CO, f'{ms}ms')}\n")
            for i, m in enumerate(modelos, 1):
                tag = c(GR, "[codigo]") if any(k in m.lower() for k in CODE_HINTS) else c(CY, "[general]")
                print(f"    {c(YL, str(i)+'.')} {c(GR, m)}  {tag}")
            print()

        try:
            ok = input(c(GR+BOLD, "  ¿Agregar al pool? [S/n]: ")).strip().lower()
        except (KeyboardInterrupt, EOFError):
            return

        if ok in ("", "s", "y"):
            keys.append(nueva)
            guardar_keys(keys)
            cache[nueva] = {"modelos": modelos, "ts": time.time()}
            guardar_cache(cache)
            print(c(GR, f"\n  ✓ Key agregada. Pool total: {len(keys)} keys.\n"))

        try:
            otra = input(c(CO, "  ¿Agregar otra? [s/N]: ")).strip().lower()
        except (KeyboardInterrupt, EOFError):
            return
        if otra not in ("s", "y"):
            return

def eliminar_key():
    cls()
    keys  = cargar_keys()
    cache = cargar_cache()
    if not keys:
        print(c(YL, "\n  No hay keys para eliminar.\n"))
        input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Eliminar Key ─────────────────────────────')}\n")
    for i, k in enumerate(keys, 1):
        n_m = len(cache.get(k, {}).get("modelos", []))
        print(f"  {c(YL+BOLD, str(i)+'.')} {c(CY, mostrar_key(k))}  {c(CO, f'{n_m} modelos')}")

    print(f"\n  {c(CO,'0. Cancelar')}")
    try:
        op = input(c(PU+BOLD, "\n  ¿Cuál eliminar? [número]: ")).strip()
    except (KeyboardInterrupt, EOFError):
        return

    if op == "0":
        return
    try:
        idx = int(op) - 1
        if 0 <= idx < len(keys):
            k = keys.pop(idx)
            guardar_keys(keys)
            cache.pop(k, None)
            guardar_cache(cache)
            print(c(GR, f"\n  ✓ Key eliminada. Pool: {len(keys)} keys.\n"))
        else:
            print(c(RE, "  Número inválido."))
    except ValueError:
        print(c(RE, "  Escribe un número."))
    input(c(CO, "  Enter para volver..."))

def ver_modelos():
    cls()
    keys  = cargar_keys()
    cache = cargar_cache()
    if not keys:
        print(c(YL, "\n  No hay keys.\n")); input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Modelos por Key ──────────────────────────')}\n")
    for i, k in enumerate(keys, 1):
        mods = cache.get(k, {}).get("modelos", [])
        print(f"  {c(YL+BOLD, str(i)+'.')} {c(CY, mostrar_key(k))}  "
              f"{c(GR, str(len(mods))+' modelos') if mods else c(RE,'sin modelos')}")
        for m in mods[:20]:
            tag = c(GR, "●") if any(x in m.lower() for x in CODE_HINTS) else c(CY, "○")
            print(f"      {tag} {c(GR, m)}")
        if len(mods) > 20:
            print(f"      {c(CO, f'··· +{len(mods)-20} más')}")
        print()

    input(c(CO, "  Enter para volver..."))

def probar_todas():
    cls()
    keys = cargar_keys()
    if not keys:
        print(c(YL, "\n  No hay keys.\n")); input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Probar Todas las Keys ────────────────────')}\n")
    for i, k in enumerate(keys, 1):
        print(f"  {c(YL+BOLD, str(i)+'.')} {c(CY, mostrar_key(k))} → ", end="", flush=True)
        t0 = time.time()
        modelos, err = fetch_modelos(k)
        ms = int((time.time() - t0) * 1000)
        if err:
            print(c(RE, f"✗ {err}"))
        else:
            ms_col = GR if ms < 2000 else YL if ms < 5000 else OR
            print(c(GR, "✓ OK") + f"  {c(GR+BOLD, str(len(modelos)))} modelos  {c(ms_col, f'{ms}ms')}")
    print()
    input(c(CO, "  Enter para volver..."))

def actualizar_modelos():
    cls()
    keys  = cargar_keys()
    cache = cargar_cache()
    if not keys:
        print(c(YL, "\n  No hay keys.\n")); input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Actualizar Modelos (fetch en vivo) ───────')}\n")
    cambiados = 0
    for k in keys:
        print(f"  {c(CY, mostrar_key(k))} → ", end="", flush=True)
        t0 = time.time()
        modelos, err = fetch_modelos(k)
        ms = int((time.time() - t0) * 1000)
        if err:
            print(c(RE, f"✗ {err}"))
        else:
            antes = len(cache.get(k, {}).get("modelos", []))
            cache[k] = {"modelos": modelos, "ts": time.time()}
            diff = len(modelos) - antes
            diff_str = c(GR, f"+{diff}") if diff > 0 else c(CO, str(diff)) if diff < 0 else c(CO, "=")
            print(c(GR, f"✓ {len(modelos)} modelos") + f"  {c(CO, f'{ms}ms')}  {diff_str}")
            cambiados += 1

    guardar_cache(cache)
    print(f"\n  {c(GR,'✓')} Guardado. {cambiados}/{len(keys)} keys actualizadas.\n")
    input(c(CO, "  Enter para volver..."))

def ver_completas():
    cls()
    keys  = cargar_keys()
    cache = cargar_cache()
    print(f"\n{c(RE+BOLD,'── Keys Completas ¡mantén privadas! ─────────')}\n")
    if not keys:
        print(c(CO, "  Sin keys.\n"))
    else:
        for i, k in enumerate(keys, 1):
            n_m = len(cache.get(k, {}).get("modelos", []))
            print(f"  {c(YL+BOLD, str(i)+'.')} {c(YL, k)}")
            print(f"      {c(CO, f'{n_m} modelos cacheados')}\n")
    input(c(CO, "  Enter para volver..."))

# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Migrar formato antiguo de key única, si existiera (~/AIION/data/ollama_key)
    old = AIION_HOME / "ollama_key"
    if old.exists() and not KEYS_FILE.exists():
        print(c(YL, "\n  Migrando ollama_key → ollama_keys..."))
        guardar_keys([old.read_text().strip()])
        time.sleep(1)

    while True:
        op = pantalla_principal()
        if   op == "1": agregar_key()
        elif op == "2": eliminar_key()
        elif op == "3": ver_modelos()
        elif op == "4": probar_todas()
        elif op == "5": actualizar_modelos()
        elif op == "6": ver_completas()
        elif op == "0":
            cls()
            print(c(GR, f"\n  ✓ Keys guardadas en {KEYS_FILE}"))
            print(c(CO,  "  AIION las carga automáticamente en modo Nube al iniciar.\n"))
            sys.exit(0)

if __name__ == "__main__":
    main()
