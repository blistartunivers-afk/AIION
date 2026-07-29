# 🔐 Política de Seguridad — AIION

> La seguridad de la comunidad es prioridad. Este documento explica cómo
> reportar vulnerabilidades de forma responsable.

---

## ⚠️ NO abras Issues públicos para vulnerabilidades

Si descubres una vulnerabilidad de seguridad, **NO** crees un issue
público en GitHub. En su lugar, sigue el canal privado descrito abajo.

---

## 📧 Canal de Reporte Privado

Envía un email a: **blistartunivers@gmail.com**

Asunto sugerido: `[SECURITY] AIION — <descripción breve>`

### ¿Qué incluir en el reporte?

1. **Tipo de vulnerabilidad** (ej: injection, exposición de secretos,
   privilege escalation)
2. **Ubicación**: archivo, línea, función o URL
3. **Pasos para reproducir** (mínimo, idealmente un PoC)
4. **Impacto potencial**: qué puede lograr un atacante
5. **Entorno**: versión de AIION, Termux, Android, Python
6. **Sugerencia de fix** (si tienes)
7. **Tu nombre/crédito** (opcional — para agradecimientos)

### Ejemplo de reporte mínimo

```
Tipo: Exposición de API key en logs
Archivo: aiion/llm/client.py:142
Pasos: 1. Iniciar AIION sin variables de entorno
       2. Revisar /tmp/aiion.log
       3. Observar key hardcodeada en línea de debug
Impacto: Cualquier proceso local con acceso a /tmp puede robar la key
Entorno: AIION v0.2.0, Termux 0.118, Android 14, Python 3.11
Fix sugerido: Enmascarar keys en logs con función mask_secret()
```

---

## ⏱️ Nuestro Compromiso

| Etapa | Tiempo |
|-------|--------|
| Acuse de recibo | < 48 horas |
| Evaluación inicial | < 7 días |
| Plan de mitigación | < 30 días |
| Release de fix | según severidad |

### Severidad (CVSS v3.1 simplificado)

| Nivel | Descripción | SLA de fix |
|-------|-------------|------------|
| 🔴 **Crítica** | RCE, exposición masiva de keys | < 7 días |
| 🟠 **Alta** | Escalada de privilegios, bypass de auth | < 30 días |
| 🟡 **Media** | DoS local, info disclosure menor | < 90 días |
| 🟢 **Baja** | Mejoras de hardening, mejores prácticas | próximo release |

---

## 🎖️ Programa de Reconocimiento

Los investigadores que reporten vulnerabilidades de forma responsable
serán:

- ✨ **Reconocidos** en `CONTRIBUTORS.md` (con su permiso)
- 🚀 **Mencionados** en el release notes del fix (si lo desean)
- 🎁 **Priorizados** para futuras betas y features experimentales

---

## 🔒 Versiones Soportadas

| Versión | Soporte |
|---------|---------|
| `master` (última) | ✅ Activo |
| Última release tag | ✅ Activo |
| Versiones anteriores | ❌ Sin soporte (favor actualizar) |

---

## 🛡️ Hardening Incluido en AIION

Como referencia, AIION ya implementa estas medidas:

- ✅ `.gitignore` estricto para `.env`, `*.db`, `*.key`, `secrets/`
- ✅ `aiion_keys.py` con sanitización de logs
- ✅ Variables de entorno para todas las credenciales
- ✅ Sin telemetría remota
- ✅ Datos de usuario almacenados solo localmente
- ✅ Pool de keys con rotación opcional
- ✅ Validación de entrada en sub-agentes

---

## 📜 Divulgación Coordinada

Seguimos prácticas de **divulgación coordinada**:

1. Reporte privado → 2. Investigación → 3. Fix desarrollado →
4. Notificación al reporter → 5. Release → 6. Disclosure pública

Damos crédito al reporter cuando se publica el advisory.

---

## 🌊 Filosofía de Seguridad

AIION cree que la seguridad es una conversación, no un escudo.
Construimos con transparencia: nuestro código es auditable, nuestros
procesos son públicos, y nuestras equivocaciones se documentan para
aprender.

> "El agua más fuerte erosiona la roca más dura" — y la roca más
> segura es la que acepta ser erosionada por buenas prácticas.
