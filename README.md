# AIION — Agente Autónomo de Ecosistema

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Termux/Android](https://img.shields.io/badge/platform-Termux%2FAndroid-green.svg)](https://termux.dev/)
[![Status: v0.2](https://img.shields.io/badge/status-v0.2-orange.svg)](CHANGELOG.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> Agente autónomo modular para Android/Termux con sensores nativos, memoria cognitiva y arquitectura de sub-agentes.

---

## 🎯 ¿Qué es AIION?

AIION es un **agente autónomo CLI** diseñado para correr de forma nativa en **Termux (Android sin root)**. Integra sensores del dispositivo, memoria persistente, herramientas de ejecución y un sistema de sub-agentes especializados para construir un ecosistema inteligente y modular.

Inspirado en la filosofía de **"fluir como el agua"**: arquitectura liviana, sin dependencias pesadas, 100% Python estándar + librerías mínimas.

---

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| 📱 **Nativo Android** | Corre en Termux sin root, accede a sensores via `termux-api` |
| 🧠 **Memoria Cognitiva** | Sistema de 4 capas: short-term, long-term, episodic y vectorial |
| 🏗️ **Modular** | Sub-agentes especializados: voz, memoria, herramientas, seguridad |
| 🔐 **Seguro** | `.gitignore` blindado, separación de secretos, sin telemetría externa |
| ⚡ **Ligero** | Solo `urllib` de stdlib — sin requests, sin frameworks pesados |
| 🌐 **Modo Nube** | Compatible con Ollama Cloud y Google Gemini (API keys rotativas) |
| 📊 **PHVA + Kaizen** | Ciclos de mejora continua, métricas y retrospectivas |
| 🎤 **Voz TTS** | Síntesis de voz opcional vía Groq PlayAI |

---

## 🏗️ Arquitectura

```
AIION/
├── aiion/
│   ├── core.py              # 🧠 Núcleo de orquestación
│   ├── db.py                # 💾 Base de datos SQLite (migraciones idempotentes)
│   ├── config.py.example    # ⚙️  Plantilla de configuración
│   ├── memory/              # 🧬 Gestión de memoria (4 capas)
│   │   ├── short_term.py    #     └─ Buffer RAM con TTL
│   │   ├── long_term.py     #     └─ Persistencia en SQLite
│   │   ├── episodic.py      #     └─ Índice semántico TF-IDF
│   │   └── vector.py        #     └─ Embeddings locales
│   ├── sensors/             # 📡 Ingesta de sensores Android
│   │   ├── gps.py
│   │   ├── battery.py
│   │   ├── light.py
│   │   ├── proximity.py
│   │   └── ...
│   ├── tools/               # 🛠️  Herramientas de ejecución
│   │   ├── shell.py         #     └─ Bash en Termux
│   │   ├── dialog.py        #     └─ Interacción con usuario
│   │   ├── notify.py        #     └─ Notificaciones Android
│   │   └── ...
│   ├── voice/               # 🎤 Síntesis de voz
│   ├── llm/                 # 🤖 Clientes LLM (Ollama + Gemini)
│   └── subagentes/          # 🤝 Sub-agentes especializados
│       ├── memory_manager.py
│       ├── security_agent.py
│       └── ...
├── plans/                   # 📋 Templates PHVA (Planear-Hacer-Verificar-Actuar)
├── tests/                   # ✅ Suite de tests públicos
├── data/                    # 🚫 Datos locales (ignorado por git)
├── main.py                  # 🚀 Entry point
├── aiion_keys.py            # 🔑 Gestor de keys Ollama Cloud
├── pyproject.toml           # 📦 Configuración del paquete
└── .gitignore               # 🛡️  Blindaje de secretos
```

---

## 🚀 Instalación Rápida

### Requisitos
- **Termux** (F-Droid) instalado en Android
- **Termux:API** (F-Droid) para acceso a sensores
- Python 3.8+

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/blistartunivers-afk/AIION.git
cd AIION

# 2. Configurar Termux API (dar permisos)
termux-setup-storage

# 3. Instalar dependencias mínimas
pip install -e .

# 4. Copiar plantilla de configuración
cp aiion/config.py.example aiion/config.py
# Editar aiion/config.py con tus rutas

# 5. (Opcional) Configurar API keys de Ollama Cloud
python aiion_keys.py

# 6. Ejecutar
python main.py
```

---

## 📚 Documentación

| Recurso | Descripción |
|---------|-------------|
| [plans/](plans/) | Templates PHVA para proyectos derivados |
| [docs/](docs/) | Documentación técnica extendida |
| [CHANGELOG.md](CHANGELOG.md) | Historial de versiones |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Guía para contribuidores |
| [LICENSE](LICENSE) | Licencia MIT |

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repo
2. Crea tu branch (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'feat: add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

---

## 🔐 Seguridad

Este repositorio **NO contiene** secretos ni datos personales:
- 🔒 Las API keys se cargan desde archivos locales **ignorados por git**
- 📂 Los datos de sensores, logs y BD local están excluidos
- 🧪 Los tests usan mocks, nunca datos reales

Si encuentras una vulnerabilidad, por favor abre un **issue** con la etiqueta `security`.

---

## 📜 Licencia

Distribuido bajo la licencia **MIT**. Ver [LICENSE](LICENSE) para más detalles.

---

## 🌊 Filosofía

> *"Fluye como el agua: adapta, persiste, evoluciona."*

AIION no es solo código, es un enfoque modular, ético y evolutivo de construir agentes autónomos que respetan la privacidad del usuario y la soberanía de sus datos.

---

## 📊 Estado del Proyecto

| Fase | Estado |
|------|--------|
| F1 — Planear | ✅ Completada |
| F2 — Hacer | ✅ Completada (v0.2) |
| F3 — Verificar | 🔄 En progreso |
| F4 — Actuar | ⏳ Pendiente |

Ver [plans/](plans/) para detalles.

---

<p align="center">
  Hecho con 🔥 y 🧊 por el ecosistema BLIST
</p>
