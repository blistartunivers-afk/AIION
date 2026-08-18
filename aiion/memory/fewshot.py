"""aiion/memory/fewshot.py — Few-shot bank desde sara_brain/dataset_v1_dedup.jsonl
Permite a AIION consultar ejemplos reales pasados (instrucción+contexto+respuesta)
para mejorar respuestas en herramientas específicas.
AIION v1 - Estiven - 2026-07-24
"""
import json
import re
import random
from pathlib import Path
from typing import List, Dict, Optional

DEFAULT_DATASET = Path("/data/data/com.termux/files/home/sara_brain/dataset_v1_dedup.jsonl")

# Banco en memoria (lazy load)
_BANK: Optional[List[Dict]] = None
_INDEX: Dict[str, List[int]] = {}  # instrucción -> [índices]


def _tokenize(text: str) -> List[str]:
    return re.findall(r'\w+', text.lower())


def _load_bank(path: Path = DEFAULT_DATASET) -> List[Dict]:
    """Carga perezosa del dataset limpio deduplicado."""
    global _BANK, _INDEX
    if _BANK is not None:
        return _BANK
    if not path.exists():
        return []
    _BANK = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                entry = json.loads(line)
                _BANK.append(entry)
                instr = entry.get('instruction', 'UNKNOWN')
                _INDEX.setdefault(instr, []).append(i)
            except (json.JSONDecodeError, KeyError):
                continue
    return _BANK


def _score(query_tokens: List[str], doc: Dict) -> float:
    """Scoring simple: TF-IDF aproximado entre query y response del ejemplo."""
    resp = doc.get('response', '') or ''
    ctx = doc.get('context', {})
    if isinstance(ctx, dict):
        ctx_str = ' '.join(str(v) for v in ctx.values())
    else:
        ctx_str = str(ctx)
    text = (resp + ' ' + ctx_str).lower()
    if not text:
        return 0.0
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    matches = sum(1 for t in query_tokens if t in tokens)
    # Bonus por éxito
    if doc.get('_meta', {}).get('success'):
        matches += 0.5
    return matches / max(len(tokens), 1)


def get_few_shot(
    instruction: str,
    query: str = "",
    n: int = 3,
    only_success: bool = True,
    path: Path = DEFAULT_DATASET
) -> List[Dict]:
    """
    Devuelve hasta N ejemplos similares para una instrucción dada.
    Args:
        instruction: nombre de la herramienta (e.g. "run_shell_command")
        query: texto adicional para mejorar el ranking
        n: número de ejemplos a devolver
        only_success: si True, solo ejemplos con _meta.success=True
    """
    bank = _load_bank(path)
    if not bank or instruction not in _INDEX:
        return []

    candidates = []
    for idx in _INDEX[instruction]:
        doc = bank[idx]
        if only_success and not doc.get('_meta', {}).get('success'):
            continue
        candidates.append(doc)

    if not candidates and not only_success:
        # Relajar el filtro
        for idx in _INDEX[instruction]:
            candidates.append(bank[idx])

    if not query:
        # Sin query, tomar muestra aleatoria de los exitosos
        random.shuffle(candidates)
        return candidates[:n]

    # Ranking por relevancia
    q_tokens = _tokenize(query)
    scored = [(_score(q_tokens, c), c) for c in candidates]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:n]]


def format_few_shot_block(examples: List[Dict], max_resp_chars: int = 200) -> str:
    """Formatea ejemplos para inyectar en el prompt."""
    if not examples:
        return ""
    lines = ["## EJEMPLOS PASADOS REALES (few-shot):"]
    for i, ex in enumerate(examples, 1):
        instr = ex.get('instruction', '?')
        ctx = ex.get('context', {})
        resp = ex.get('response', '')[:max_resp_chars]
        ctx_str = json.dumps(ctx, ensure_ascii=False) if isinstance(ctx, dict) else str(ctx)
        if len(ctx_str) > 120:
            ctx_str = ctx_str[:120] + '...'
        lines.append(f"  {i}. [{instr}] ctx={ctx_str}")
        lines.append(f"     → {resp}")
    return '\n'.join(lines)


def get_stats(path: Path = DEFAULT_DATASET) -> Dict:
    """Estadísticas del banco."""
    bank = _load_bank(path)
    if not bank:
        return {"loaded": False, "path": str(path)}
    success = sum(1 for e in bank if e.get('_meta', {}).get('success'))
    return {
        "loaded": True,
        "path": str(path),
        "total": len(bank),
        "success": success,
        "fail": len(bank) - success,
        "instructions": len(_INDEX),
        "size_mb": round(path.stat().st_size / 1e6, 2)
    }


# CLI
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: fewshot.py <instruccion> [query]")
        print("     fewshot.py --stats")
        sys.exit(1)
    if sys.argv[1] == '--stats':
        print(json.dumps(get_stats(), indent=2))
    else:
        instr = sys.argv[1]
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        examples = get_few_shot(instr, query, n=3)
        print(format_few_shot_block(examples))
