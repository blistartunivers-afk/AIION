# Guía para Contribuidores del Núcleo

> Cómo extender AIION sin romper su filosofía: **100 % Python estándar, sin dependencias pesadas, seguro por diseño.**

---

## 📋 Antes de empezar

1. Lee [`ARCHITECTURE.md`](ARCHITECTURE.md) para entender el flujo de una interacción.
2. Lee [`SECURITY-MODEL.md`](SECURITY-MODEL.md) para saber qué nunca debe tocar un contribuidor externo.
3. Asegúrate de que `make test` pase en tu máquina antes de abrir un PR.
4. Si tu cambio afecta secretos, keys o permisos de Android, pide revisión de un maintainer.

---

## 🧩 Cómo añadir un nuevo sensor

Los sensores viven en `aiion/sensors/collectors.py` y son orquestados por `aiion/sensors/daemon.py`.

### 1. Define el recolector

Cada sensor es una función que devuelve un diccionario con:

```python
{
    "ts": "ISO-8601",
    "value": <dato serializable en JSON>,
    "unit": "str opcional",
    "confidence": float  # 0.0 - 1.0
}
```

Ejemplo mínimo:

```python
def collect_magnetometer() -> dict:
    """Devuelve el campo magnético en uT si termux-sensor está disponible."""
    raw = run_termux_command(["termux-sensor", "-s", "magnetometer", "-n", "1"])
    if raw is None:
        return {"ts": now_iso(), "value": None, "confidence": 0.0}
    return {
        "ts": now_iso(),
        "value": json.loads(raw),
        "unit": "uT",
        "confidence": 0.85
    }
```

### 2. Registra el intervalo

En `aiion/sensors/daemon.py`, añade tu sensor al mapa `SENSOR_INTERVALS`:

```python
SENSOR_INTERVALS = {
    ...
    "magnetometer": 10,  # segundos
}
```

### 3. Expón el dato al prompt

En `aiion/core.py`, dentro de `build_system_prompt()`, añade una línea que lea el último valor:

```python
mag = STATE.get("sensor", {}).get("magnetometer", {})
if mag:
    lines.append(f"- Magnetómetro: {mag.get('value')} {mag.get('unit', '')}")
```

### 4. Test

Añade un test en `tests/test_sensors.py` (crea el archivo si no existe) que verifique:

- El recolector devuelve el formato correcto.
- Maneja el caso de `termux-api` no disponible sin lanzar excepción.

---

## 🛠️ Cómo añadir una nueva tool

Las tools se definen en `aiion/tools/registry.py` y se implementan en:

- `aiion/tools/filesystem.py` — archivos, shell, web
- `aiion/tools/android.py` — sensores, cámara, GPS, notificaciones
- `aiion/tools/communication.py` — SMS, llamadas, voz
- `aiion/tools/github.py` — operaciones de GitHub

### 1. Implementa la función

Toda tool recibe un diccionario `args` y devuelve un diccionario con:

```python
{
    "status": "ok | error | denied",
    "result": <dato serializable>,
    "message": "str opcional"
}
```

Ejemplo:

```python
def tool_get_battery(args: dict) -> dict:
    level = args.get("level", STATE.get("sensor", {}).get("battery", {}).get("value"))
    if level is None:
        return {"status": "error", "message": "No hay datos de batería"}
    return {"status": "ok", "result": {"level": level}}
```

### 2. Declara la tool en el registro

En `aiion/tools/registry.py`, añade una entrada al diccionario `TOOLS`:

```python
{
    "type": "function",
    "function": {
        "name": "get_battery",
        "description": "Devuelve el nivel actual de batería del dispositivo.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}
```

Y mapea el nombre a la función en `TOOL_MAP`:

```python
TOOL_MAP = {
    ...
    "get_battery": filesystem.tool_get_battery,
}
```

### 3. Define permisos

Si la tool es peligrosa (escribe, borra, envía mensajes, llama, gasta dinero), añádela a `DANGEROUS_TOOLS`:

```python
DANGEROUS_TOOLS = {
    ...
    "send_sms": {"reason": "Puede generar costos de mensajería"},
}
```

Esto obliga a `ask_permission()` antes de ejecutar.

### 4. Test

Añade un test en `tests/test_tools.py` que verifique:

- La firma JSON coincide con `TOOL_MAP`.
- El resultado tiene `status`.
- Las tools peligrosas requieren permiso.

---

## 🤖 Cómo añadir un nuevo sub-agente

Los sub-agentes viven en `aiion/subagentes/`. Son módulos especializados que el core puede invocar.

### 1. Crea el módulo

```python
# aiion/subagentes/coder.py

def review_code(snippet: str) -> dict:
    """Sub-agente especialista en revisión de código Python."""
    # Lógica pura de Python stdlib
    issues = []
    if "eval(" in snippet:
        issues.append("Uso de eval() detectado — riesgo de inyección.")
    return {"status": "ok", "issues": issues}
```

### 2. Expón una función de entrada clara

Cada sub-agente debe tener una función principal con firma estable:

```python
def run(input_data: dict, context: dict | None = None) -> dict:
    ...
```

### 3. Regístralo en el core

En `aiion/core.py`, añade una ruta para invocarlo:

```python
if intent == "review_code":
    from aiion.subagentes import coder
    return coder.run({"snippet": user_input})
```

### 4. Documenta el contrato

Añade una sección en este archivo (`CONTRIBUTING-CORE.md`) explicando:

- Qué problema resuelve.
- Qué recibe (`input_data`).
- Qué devuelve.
- Qué módulos de AIION utiliza.

---

## 🧪 Convenciones de código

- **Sin dependencias externas** salvo que un maintainer lo apruebe explícitamente.
- Todo el I/O de red usa `urllib` de stdlib.
- Todo el I/O de Android usa `subprocess` + `termux-api`.
- Las funciones deben tener type hints.
- Los docstrings son obligatorios para funciones públicas.
- Los cambios en `aiion/config.py` deben ser compatibles con `config.py.example`.

---

## ✅ Checklist antes de PR

- [ ] `make test` pasa localmente.
- [ ] `make lint` no introduce errores nuevos (los preexistentes están documentados).
- [ ] No añadí keys, tokens ni datos personales.
- [ ] Actualicé `docs/` si el cambio afecta la arquitectura o el uso.
- [ ] Añadí tests para el nuevo sensor/tool/sub-agente.
- [ ] Verifiqué que el `.gitignore` sigue protegiendo `data/` y archivos de keys.

---

## 🆘 ¿Dudas?

Abre un issue con etiqueta `question` o menciona `@blistartunivers-afk` en tu PR.
