# Contribuir a AIION

¡Gracias por tu interés en contribuir a AIION! 🎉
Este documento te guiará para hacerlo de forma efectiva y respetuosa.

---

## 📜 Código de Conducta

Al participar, te comprometes a mantener un ambiente respetuoso y colaborativo.
- Sé amable y empático
- Acepta críticas constructivas
- Enfócate en lo que es mejor para la comunidad

---

## 🚀 ¿Cómo Contribuir?

### 🐛 Reportar Bugs

1. Verifica que el bug **no haya sido reportado** en [Issues](https://github.com/blistartunivers-afk/AIION/issues)
2. Si no existe, abre un nuevo issue con:
   - **Título claro y descriptivo**
   - **Pasos para reproducir** el problema
   - **Comportamiento esperado vs observado**
   - **Entorno**: versión de Termux, Android, Python
   - **Logs relevantes** (con `termux-info`)

### 💡 Sugerir Mejoras

1. Abre un issue con la etiqueta `enhancement`
2. Describe:
   - El **problema** que resuelve
   - La **solución propuesta**
   - **Alternativas consideradas**
   - Impacto en el ecosistema (memoria, RAM, dependencias)

### 🔧 Enviar Pull Requests

1. **Fork** el repositorio
2. Crea una rama desde `develop`:
   ```bash
   git checkout -b feature/mi-mejora develop
   ```
3. Haz commits con mensajes descriptivos:
   ```
   feat: añadir sensor de presión barométrica
   fix: corregir leak de memoria en long_term.py
   docs: actualizar guía de instalación
   ```
4. Asegúrate de que pasan los tests:
   ```bash
   make test
   make lint
   ```
5. Push a tu fork y abre un PR contra `develop`
6. En la descripción del PR incluye:
   - **Qué cambia** y **por qué**
   - **Capturas** si hay cambios visuales
   - **Issues relacionados** (`Closes #123`)

---

## 🏗️ Estructura del Proyecto

Familiarízate con la arquitectura antes de contribuir:

```
aiion/
├── core.py          # Orquestador principal
├── db.py            # Capa de persistencia
├── memory/          # Sistema de memoria (4 capas)
├── sensors/         # Adaptadores de termux-api
├── tools/           # Herramientas expuestas al agente
├── llm/             # Clientes LLM (Ollama, Gemini)
└── subagentes/      # Sub-agentes especializados
```

---

## 📏 Estilo de Código

- **Python 3.8+** — sin syntax nueva
- **PEP 8** — usar `black` y `flake8` (ya configurados en pre-commit)
- **Type hints** — obligatorio en funciones nuevas
- **Docstrings** — formato Google para todas las funciones públicas
- **Tests** —覆盖率 mínima 70% para código nuevo
- **Sin dependencias pesadas** — preferir stdlib de Python

### Ejemplo de función bien documentada:

```python
def get_sensor_data(sensor_name: str, minutes: int = 5) -> List[dict]:
    """Obtiene datos de un sensor en un rango temporal.

    Args:
        sensor_name: Nombre del sensor (ej: 'battery', 'gps')
        minutes: Ventana temporal hacia atrás en minutos

    Returns:
        Lista de lecturas con timestamp y valores

    Raises:
        SensorNotFoundError: Si el sensor no existe en termux-api
    """
```

---

## 🧪 Tests

Antes de enviar un PR:

```bash
# Suite completa
make test

# Con cobertura
make test-coverage

# Linting
make lint

# Verificación de tipos
make type-check
```

Los tests usan **mocks** para `termux-api`, así que puedes correrlos sin un dispositivo Android real.

---

## 📋 Convención de Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

| Prefijo | Uso |
|---------|-----|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de bug |
| `docs:` | Solo documentación |
| `style:` | Formato (sin cambio de lógica) |
| `refactor:` | Cambio de código sin nueva funcionalidad |
| `test:` | Añadir o corregir tests |
| `chore:` | Mantenimiento (deps, build, etc.) |

---

## 🔐 Reportar Vulnerabilidades

⚠️ **NO abras issues públicos para vulnerabilidades de seguridad.**

Envía un email directo a: **blistartunivers@gmail.com** con:
- Descripción técnica del problema
- Pasos para reproducir
- Impacto potencial
- Sugerencia de fix (si tienes)

Responderemos en menos de 48h.

---

## 🌊 Filosofía del Proyecto

AIION se guía por estos principios:
1. **Privacidad primero** — datos del usuario NUNCA salen de su dispositivo
2. **Ligero y modular** — sin frameworks pesados
3. **Funciona sin root** — accesible para todos
4. **Ecosistema, no monolito** — sub-agentes especializados
5. **Fluye como el agua** — adaptativo, evolutivo, ético

---

## 📞 Comunidad

- **Issues**: Para bugs y features
- **Discussions**: Para preguntas generales y compartir casos de uso
- **Email**: Para colaboraciones privadas

---

## 🙏 Reconocimientos

Cada contribuidor será añadido al archivo `CONTRIBUTORS.md` (próximamente).

¡Gracias por hacer de AIION un mejor proyecto! 🔥
