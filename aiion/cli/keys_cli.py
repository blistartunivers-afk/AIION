#!/usr/bin/env python3
"""
aiion/cli/keys_cli.py — Gestor del pool de API Keys de Ollama Cloud para AIION
════════════════════════════════════════════════════════════════════
Administra las keys que AIION usa en modo Nube (Ollama Cloud).

Guarda en:  ~/AIION/data/ollama_keys        (formato plano, una key por línea)
Cachea en:  ~/AIION/data/ollama_keys_cache.json  (modelos detectados por key)

Este formato es 100% compatible con lo que `aiion.llm.keys` espera leer
via `load_api_keys()` — no requiere ningún cambio en el agente principal.
AIION carga este pool automáticamente al iniciar en modo Nube y rota
entre las keys disponibles.

Solo depende de la librería estándar de Python (urllib), igual que el
resto de AIION — sin paquetes externos.
"""
import os, sys, json, time
from pathlib import Path
import urllib.request, urllib.error

from aiion.config import AIION_HOME, KEYS_FILE, KEYS_CACHE, OLLAMA_CLOUD_MODELS
from aiion.cli.ui import c, PK, GR, YL, RE, OR, CY, CO, BOLD, cls


def cargar_keys():
    if KEYS_FILE.exists():
        return [k.strip() for k in KEYS_FILE.read_text().splitlines() if k.strip()]
    return []


def guardar_keys(keys):
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEYS_FILE.write_text("\n".join(keys) + "\n")


def cargar_cache():
    if KEYS_CACHE.exists():
        try:
            return json.loads(KEYS_CACHE.read_text())
        except:
            return {}
    return {}


def guardar_cache(cache):
    KEYS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    KEYS_CACHE.write_text(json.dumps(cache, indent=2))


def mostrar_key(k):
    return k[:8] + "..." + k[-4:] if len(k) > 12 else k


def fetch_modelos(key):
    """Devuelve (lista_modelos, error_str_or_None)."""
    req = urllib.request.Request(
        OLLAMA_CLOUD_MODELS,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "AIION-Keys/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        modelos = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        return modelos, None
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}"
    except Exception as e:
        return [], str(e)


def agregar_key():
    cls()
    print(f"\n{c(PU+BOLD,'── Agregar Key ────────────────────────────')}\n")
    k = input(f"  {c(CY,'Key Ollama Cloud: ')}").strip()
    if not k:
        print(f"  {c(YL,'Vacía, cancelado.')}"); time.sleep(0.5); return
    keys = cargar_keys()
    if k in keys:
        print(f"  {c(YL,'Ya existe.')}"); time.sleep(0.5); return
    print(f"  {c(CO,'Probando...')}", end="", flush=True)
    modelos, err = fetch_modelos(k)
    if err:
        print(f"\r  {c(RE,'✗')} {err}")
    else:
        keys.append(k)
        guardar_keys(keys)
        cache = cargar_cache()
        cache[k] = {"modelos": modelos, "ts": time.time()}
        guardar_cache(cache)
        print(f"\r  {c(GR,'✓')} {c(GR+BOLD,str(len(modelos)))} modelos  {c(CO,'guardada')}")
    time.sleep(1)


def eliminar_key():
    cls()
    keys = cargar_keys()
    if not keys:
        print(f"\n{c(YL,'  Sin keys.')}\n"); time.sleep(0.5); return
    print(f"\n{c(PU+BOLD,'── Eliminar Key ───────────────────────────')}\n")
    for i, k in enumerate(keys, 1):
        print(f"  {c(YL+BOLD,str(i)+'.')} {c(CY,mostrar_key(k))}")
    try:
        idx = int(input(f"\n  {c(CY,'Número (0=cancelar): ')}")) - 1
        if idx == -1: return
        k = keys.pop(idx)
        guardar_keys(keys)
        cache = cargar_cache()
        cache.pop(k, None)
        guardar_cache(cache)
        print(f"  {c(GR,'✓ Eliminada.')}")
    except:
        pass
    time.sleep(0.5)


def ver_modelos():
    cls()
    keys = cargar_keys()
    cache = cargar_cache()
    print(f"\n{c(PU+BOLD,'── Modelos por Key ────────────────────────')}\n")
    if not keys:
        print(c(CO, "  Sin keys."))
    else:
        for i, k in enumerate(keys, 1):
            modelos = cache.get(k, {}).get("modelos", [])
            print(f"  {c(YL+BOLD,str(i)+'.')} {c(CY,mostrar_key(k))}  {c(GR+BOLD,str(len(modelos)))} modelos")
            for m in modelos[:5]:
                print(f"      {c(CO,'•')} {m}")
            if len(modelos) > 5:
                print(f"      {c(CO,f'··· +{len(modelos)-5} más')}")
            print()
    input(c(CO, "  Enter para volver..."))


def probar_todas():
    cls()
    keys = cargar_keys()
    if not keys:
        print(f"\n{c(YL,'  No hay keys.')}\n"); input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Probar Todas las Keys ────────────────────')}\n")
    for i, k in enumerate(keys, 1):
        print(f"  {c(YL+BOLD,str(i)+'.')} {c(CY,mostrar_key(k))} → ", end="", flush=True)
        t0 = time.time()
        modelos, err = fetch_modelos(k)
        ms = int((time.time() - t0) * 1000)
        if err:
            print(c(RE, f"✗ {err}"))
        else:
            ms_col = GR if ms < 2000 else YL if ms < 5000 else OR
            print(c(GR, "✓ OK") + f"  {c(GR+BOLD,str(len(modelos)))} modelos  {c(ms_col,f'{ms}ms')}")
    print()
    input(c(CO, "  Enter para volver..."))


def actualizar_modelos():
    cls()
    keys = cargar_keys()
    cache = cargar_cache()
    if not keys:
        print(f"\n{c(YL,'  No hay keys.')}\n"); input("  Enter..."); return

    print(f"\n{c(PU+BOLD,'── Actualizar Modelos (fetch en vivo) ───────')}\n")
    cambiados = 0
    for k in keys:
        print(f"  {c(CY,mostrar_key(k))} → ", end="", flush=True)
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
            print(c(GR, f"✓ {len(modelos)} modelos") + f"  {c(CO,f'{ms}ms')}" + f"  {diff_str}")
            cambiados += 1

    guardar_cache(cache)
    print(f"\n  {c(GR,'✓')} Guardado. {cambiados}/{len(keys)} keys actualizadas.\n")
    input(c(CO, "  Enter para volver..."))


def ver_completas():
    cls()
    keys = cargar_keys()
    cache = cargar_cache()
    print(f"\n{c(RE+BOLD,'── Keys Completas ¡mantén privadas! ─────────')}\n")
    if not keys:
        print(c(CO, "  Sin keys.\n"))
    else:
        for i, k in enumerate(keys, 1):
            n_m = len(cache.get(k, {}).get("modelos", []))
            print(f"  {c(YL+BOLD,str(i)+'.')} {c(YL,k)}")
            print(f"      {c(CO,f'{n_m} modelos cacheados')}\n")
    input(c(CO, "  Enter para volver..."))


def pantalla_principal():
    cls()
    keys = cargar_keys()
    print(c(PK+BOLD, f"\n  AIION Keys Manager  v0.1  —  {len(keys)} keys cargadas\n"))
    print(c(PU, "  1") + f") {c(CY,'Agregar key')}")
    print(c(PU, "  2") + f") {c(CY,'Eliminar key')}")
    print(c(PU, "  3") + f") {c(CY,'Ver modelos cacheados')}")
    print(c(PU, "  4") + f") {c(CY,'Probar todas (latencia)')}")
    print(c(PU, "  5") + f") {c(CY,'Actualizar modelos (fetch)')}")
    print(c(PU, "  6") + f") {c(CY,'Ver keys completas (privado)')}")
    print(c(PU, "  0") + f") {c(CO,'Salir')}")
    return input(f"\n  {c(CY,'Opción: ')}").strip()


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
