# 🚀 Pull Request

> Por favor completa este template antes de enviar tu PR. Ayudas a los
> mantenedores y aceleras la revisión. ¡Gracias por contribuir! 💚

---

## 📋 Descripción

<!-- Describe brevemente qué hace este PR y por qué es necesario -->

**¿Qué cambia?**

**¿Por qué es necesario?**

---

## 🔗 Issue Relacionado

<!-- Vincula el issue que resuelve este PR -->

- Closes #
- Fixes #
- Refs #

---

## 🧪 Tipo de Cambio

<!-- Marca con [x] lo que aplique -->

- [ ] 🐛 Bug fix (cambio que arregla un problema)
- [ ] ✨ Nueva feature (cambio que añade funcionalidad)
- [ ] 💥 Breaking change (fix o feature que rompe compatibilidad)
- [ ] 📚 Documentación (solo cambios en docs)
- [ ] 🎨 Estilo (formato, sin cambio de lógica)
- [ ] ♻️ Refactor (cambio de código sin nueva funcionalidad)
- [ ] ⚡ Performance (mejora de rendimiento)
- [ ] 🧪 Tests (añadir o corregir tests)
- [ ] 🔧 Chore (mantenimiento, deps, build)

---

## 🧪 ¿Cómo se probó?

<!-- Describe las pruebas que realizaste -->

- [ ] Tests unitarios añadidos/actualizados
- [ ] Probado manualmente en Termux (Android 14)
- [ ] Probado manualmente en Linux
- [ ] Probado en macOS
- [ ] Otros: __________________

**Comandos ejecutados:**

```bash
# Ejemplo:
pytest tests/test_memory.py -v
python main.py --test sensor
```

---

## 📸 Capturas / Logs

<!-- Si aplica, añade capturas de pantalla, logs, GIFs -->

```
[Pega aquí los logs relevantes]
```

⚠️ **IMPORTANTE**: NO incluyas API keys, tokens, ni información
sensible en los logs. Usa `[REDACTED]` o enmascara con `***`.

---

## 📝 Checklist del Contribuyente

<!-- Marca con [x] lo que hayas completado -->

### Código

- [ ] Mi código sigue el estilo del proyecto (`black`, `flake8`)
- [ ] He añadido type hints en funciones nuevas
- [ ] He añadido docstrings (formato Google)
- [ ] No introduzco nuevas dependencias sin discutirlo
- [ ] He revisado que no hay imports innecesarios

### Tests

- [ ] He añadido tests que prueban mi cambio
- [ ] Los tests nuevos pasan localmente
- [ ] He mantenido o mejorado la cobertura

### Documentación

- [ ] He actualizado el README si es necesario
- [ ] He actualizado docs/ si añado features
- [ ] He actualizado CHANGELOG.md (sección "Unreleased")

### Seguridad

- [ ] No expongo secretos en logs o comentarios
- [ ] No commiteo archivos `.env`, `.db`, `*.key`
- [ ] Las variables de entorno están documentadas
- [ ] Si arreglo una vulnerabilidad, sigo SECURITY.md

---

## 🌊 Filosofía del Proyecto

<!-- Confirma que tu cambio respeta los principios de AIION -->

- [ ] 🔐 Privacidad: datos del usuario siguen en su dispositivo
- [ ] 🪶 Ligero: sin frameworks pesados innecesarios
- [ ] 🌱 Sin root: funciona en cualquier Android sin rootear
- [ ] 🧩 Modular: cambio aislado, no rompe otros módulos
- [ ] 💧 Fluye como el agua: código claro, ético, mantenible

---

## 📚 Notas Adicionales

<!-- Cualquier contexto extra que ayude a los revisores -->

---

## 🙏 Agradecimientos

<!-- Si tu trabajo se inspiró en otro proyecto o contribuidor, dales crédito -->

