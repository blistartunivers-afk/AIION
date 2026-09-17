#!/usr/bin/env python3
"""
main.py — Punto de entrada de AIION.

Uso:
    python main.py

Este archivo reemplaza al antiguo `aiion_core.py` como entrypoint.
Debe quedar en 3-5 líneas: importar aiion.core y llamar a main().
"""
import sys, os; sys.path.append(os.path.join(os.path.dirname(__file__), 'aiion')); from aiion.core import main

if __name__ == "__main__":
    main()
