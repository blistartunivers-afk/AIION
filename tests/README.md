# Tests

Estructura sugerida (1 archivo de test por módulo, mismo nombre):

```
tests/
├── test_memory.py       # RamGuard, CognitiveIndex, persistence
├── test_sensors.py      # collectors (mock de termux-api)
├── test_tools.py        # tool_read_file, tool_write_file, permisos
└── test_llm_client.py   # parse_react, get_model_type
```

Prioriza los que NO dependen de Termux (parse_react, get_model_type,
_tfidf) — esos corren en CI sin emulador Android.
