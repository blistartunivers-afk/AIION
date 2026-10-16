# Modelo de Seguridad de AIION

> Cómo AIION protege tus datos, tus keys y tu dispositivo.

---

## 🛡️ Principios de diseño

1. **Local-first**: la mayoría del estado y la memoria viven en el dispositivo.
2. **Zero-trust de secretos**: nunca se hardcodean keys en el código fuente.
3. **Permiso explícito**: las acciones peligrosas requieren confirmación del usuario.
4. **Mínimo privilegio**: cada tool solo accede a lo que necesita.
5. **Sin telemetría oculta**: no hay analytics, tracking ni logs enviados a terceros.

---

## 🔐 Qué protege `.gitignore`

El archivo `.gitignore` es la primera línea de defensa. Nunca debe relajarse sin revisión de un maintainer.

```gitignore
# Datos locales
data/
*.db
*.db-journal
*.db-wal
*.db-shm

# Keys y configuración personal
aiion_keys_real.py
.env
.env.*
secrets/

# Logs y caché
*.log
__pycache__/
.pytest_cache/

# Termux / Android
.termux/
```

### Reglas críticas

| Patrón | Por qué importa |
|--------|-----------------|
| `data/` | Aquí vive la base de datos SQLite con memoria e historial del usuario. |
| `*.db*` | Archivos de SQLite, WAL y SHM pueden contener datos personales. |
| `aiion_keys_real.py` | El gestor de keys puede generar un archivo con keys reales del usuario. |
| `.env*` | Variables de entorno con endpoints o keys. |

---

## 🔑 Cómo funciona `aiion_keys.py`

`aiion_keys.py` es un **gestor interactivo** que vive en la raíz del repo.

### Qué hace

- Carga un pool de keys de Ollama Cloud desde una variable de entorno o un archivo externo.
- Rota las keys automáticamente para distribuir carga.
- Nunca guarda keys en el código fuente.

### Qué NO hace

- No incluye keys por defecto.
- No envía keys a ningún servidor aparte del endpoint configurado.
- No aparece en commits si sigues `.gitignore`.

### Formato esperado

```bash
export AIION_OLLAMA_KEYS="key1,key2,key3"
```

O, en un archivo fuera del repo:

```bash
~/.config/aiion/keys
```

> ⚠️ Nunca subas un archivo con keys a GitHub. Si lo haces, revoca las keys inmediatamente.

---

## ⚠️ Threat model

### Actores

| Actor | Capacidad asumida |
|-------|-------------------|
| Usuario final | Controla el dispositivo Android. |
| Contribuidor externo | Puede abrir PRs; no tiene acceso a secrets del repo. |
| Maintainer | Puede mergear PRs y publicar releases. |
| Atacante remoto | Puede enviar inputs al LLM si el usuario expone el servicio. |
| Atacante con acceso al repo | Puede leer el código fuente, pero no keys ni datos de usuarios. |

### Escenarios de amenaza

#### 1. Prompt injection

Un input malicioso intenta convencer al LLM para que ejecute una tool peligrosa.

Mitigación:

- Las tools peligrosas pasan por `ask_permission()`.
- El system prompt incluye instrucciones de seguridad.
- El historial se sanitiza antes de enviarse al LLM.

#### 2. Exfiltración de datos locales

Una tool lee archivos del dispositivo y los envía fuera.

Mitigación:

- Las tools de filesystem tienen lista blanca de rutas permitidas.
- `data/` está fuera de los paths accesibles por tools genéricas.
- No hay tool de "enviar a servidor remoto arbitrario".

#### 3. Ejecución de comandos destructivos

Una tool de shell ejecuta `rm -rf /` o similar.

Mitigación:

- Las tools de shell requieren confirmación explícita.
- Se recomienda usar `shlex` y evitar `shell=True`.
- El usuario puede deshabilitar tools peligrosas en `aiion/config.py`.

#### 4. Fuga de keys en commits

Un contribuidor accidentalmente commitea un archivo con keys.

Mitigación:

- `.gitignore` bloquea archivos comunes de keys.
- `gitleaks` corre en CI en cada push/PR.
- Revisión manual obligatoria para cambios en `.gitignore`.

#### 5. Dependencia comprometida

Un paquete de PyPI malicioso se instala como dependencia.

Mitigación:

- AIION no tiene dependencias de pip.
- `pip-audit` corre en CI por si se añaden dependencias en el futuro.
- `requirements.txt` está documentado como intencionalmente vacío.

---

## 🔒 Configuraciones de seguridad

En `aiion/config.py` puedes ajustar:

```python
# Límites de seguridad
MAX_SHELL_OUTPUT = 50_000        # bytes
DANGEROUS_TOOLS_REQUIRE_CONFIRM = True
ALLOWED_READ_PATHS = [AIION_HOME / "docs", AIION_HOME / "plans"]
```

No modifiques estos valores en el repo público; hazlo en tu copia local.

---

## 🚨 Reportar vulnerabilidades

Si encuentras una vulnerabilidad, sigue la política de [`.github/SECURITY.md`](../.github/SECURITY.md):

1. No abras un issue público.
2. Envía un email al maintainer.
3. Espera el SLA según severidad.

---

## 📚 Referencias

- [`.github/SECURITY.md`](../.github/SECURITY.md) — Política oficial de reporte.
- [`.gitignore`](../.gitignore) — Reglas de exclusión.
- [`CONTRIBUTING-CORE.md`](CONTRIBUTING-CORE.md) — Guía para contribuidores.
