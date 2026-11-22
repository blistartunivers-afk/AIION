"""El grafo público debe arrancar y distinguir respuestas de errores."""
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from aiion.core_modules.langgraph_integration import build_aiion_graph, run_graph_sync
from aiion.core_modules.langgraph_integration import route_after_llm


class MemoryCheckpointer:
    def save(self, *_args, **_kwargs):
        pass


@pytest.mark.parametrize("native", [True, False])
@pytest.mark.parametrize("answer", ["respuesta", "", "400"])
def test_graph_handles_model_reply(native, answer):
    calls = []

    def chat_native(_messages):
        calls.append("native")
        if answer == "400":
            raise HTTPError("https://test.invalid", 400, "invalid", {}, None)
        return "text", answer, {}

    def chat_react(_messages):
        calls.append("react")
        return answer

    graph = build_aiion_graph(
        build_system_prompt_fn=lambda _text: "prompt",
        chat_native_fn=chat_native,
        chat_react_text_fn=chat_react,
        parse_react_fn=lambda text: ("final", text),
        execute_tool_fn=lambda *_args: "ok",
        tool_map={},
        tool_call_state={"native": native},
        max_iter=20,
        ram_guard=None,
        sensor_last_fn=lambda _name: None,
        memory_load_fn=lambda: "",
        history_summary_fn=lambda _text: "",
        cogindex=SimpleNamespace(context_block=lambda: ""),
        mythos=SimpleNamespace(analyze=lambda _text: None),
        state_dict={},
        voice_state={},
        speak_fn=lambda *_args, **_kwargs: None,
        notify_fn=lambda *_args, **_kwargs: None,
        history_save_fn=lambda *_args, **_kwargs: None,
        checkpointer=MemoryCheckpointer(),
    )
    state = run_graph_sync(graph, "hola", [], max_steps=10,
                           metadata={"tool_mode": "native" if native else "react"})
    assert calls == (["native", "react"] if native and answer in ("", "400")
                     else ["native" if native else "react"])
    assert state["status"] == ("completed" if answer else "error")
    assert state["final_response"] == answer
    if not answer:
        assert "respuesta vacía" in state["error"]


def test_sensitive_tool_reaches_permission_aware_executor():
    state = {"tool_calls": [{"function": {"name": "write_file"}}], "status": "running"}
    assert route_after_llm(state) == "execute_tools"


def test_public_main_reaches_prompt(monkeypatch, tmp_path):
    from aiion import core

    monkeypatch.setattr(core, "select_mode", lambda: None)
    monkeypatch.setattr(core.RAMGUARD, "start", lambda: None)
    monkeypatch.setattr(core.RAMGUARD, "stop", lambda: None)
    monkeypatch.setattr(core, "sensor_start", lambda: None)
    monkeypatch.setattr(core, "sensor_stop", lambda: None)
    monkeypatch.setattr(core, "SQLiteCheckpointer", lambda: MemoryCheckpointer())
    monkeypatch.setattr(core.subprocess, "Popen", lambda *_a, **_kw: None)
    monkeypatch.setattr(core.os, "system", lambda *_a: 0)
    monkeypatch.setattr("builtins.input", lambda *_a: "/exit")
    with pytest.raises(SystemExit) as exited:
        core.main()
    assert exited.value.code == 0
