"""Gemini usa las claves de Google y conserva llamadas a herramientas."""
import io
import json
import urllib.error

from aiion import core
from aiion.llm import client, keys


def test_load_gemini_keys_from_env_and_file(tmp_path, monkeypatch):
    (tmp_path / "gemini_keys").write_text("file-one\nfile-two\n")
    monkeypatch.setattr(keys, "AIION_HOME", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "env-one,file-one")
    assert keys.load_gemini_keys() == ["env-one", "file-one", "file-two"]


def test_load_gemini_keys_from_shared_pool(tmp_path, monkeypatch):
    (tmp_path / ".blist_keys").write_text(
        "ollama|ignore\ngemini|google-one\ngoogle|google-two\n")
    monkeypatch.setattr(keys, "AIION_HOME", tmp_path / "empty")
    monkeypatch.setattr(keys.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert keys.load_gemini_keys() == ["google-one", "google-two"]


def test_select_gemini_uses_google_keys(monkeypatch):
    monkeypatch.setattr(core, "load_gemini_keys", lambda: ["google-one", "google-two"])
    monkeypatch.setattr("builtins.input", lambda *_args: "")
    core._setup_gemini()
    assert core.STATE["provider"] == "gemini"
    assert core.STATE["api_keys"] == ["google-one", "google-two"]
    assert core.STATE["model"] == core.GEMINI_MODELS[0]


def test_enter_selects_gemini_when_google_keys_exist(monkeypatch):
    monkeypatch.setattr(core, "load_gemini_keys", lambda: ["google-one"])
    monkeypatch.setattr(core.os, "system", lambda *_args: 0)
    monkeypatch.setattr("builtins.input", lambda *_args: "")
    core.select_mode()
    assert core.STATE["provider"] == "gemini"


def test_gemini_request_rotates_after_quota(monkeypatch):
    monkeypatch.setattr(keys, "_KEY_HEALTH", {})
    monkeypatch.setitem(keys.STATE, "provider", "gemini")
    monkeypatch.setitem(keys.STATE, "use_cloud", True)
    monkeypatch.setitem(keys.STATE, "api_keys", ["first", "second"])
    monkeypatch.setitem(keys.STATE, "key_index", 0)
    monkeypatch.setitem(keys.STATE, "model", "gemini-test")
    monkeypatch.setattr(keys, "GEMINI_MODELS", ["gemini-other"])
    seen = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"respuesta"}]}}]}'

    def fake_open(request, timeout):
        seen.append((request.get_header("X-goog-api-key"), request.full_url))
        if len(seen) == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO(b"{}"))
        return Response()

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_open)
    assert client.chat_native([{"role": "user", "content": "hola"}])[1] == "respuesta"
    assert [item[0] for item in seen] == ["first", "second"]
    assert all("first" not in url and "second" not in url for _, url in seen)


def test_gemini_tool_result_is_sent_back(monkeypatch):
    monkeypatch.setitem(keys.STATE, "provider", "gemini")
    monkeypatch.setattr(client, "_do_request_gemini", lambda *_args, **_kwargs: {
        "candidates": [{"content": {"parts": [
            {"functionCall": {"name": "read_file", "args": {"path": "sample.txt"}}}
        ]}}]})
    kind, calls, message = client.chat_native([{"role": "user", "content": "lee"}])
    assert kind == "tool_call"
    assert calls[0][:2] == ("read_file", {"path": "sample.txt"})
    system, contents = client._messages_to_gemini([
        {"role": "system", "content": "instrucciones"},
        {"role": "assistant", "content": "", "tool_calls": message["tool_calls"]},
        {"role": "tool", "name": "read_file", "content": "contenido"},
    ])
    assert system == "instrucciones"
    assert contents[0]["parts"][0]["functionCall"]["name"] == "read_file"
    assert contents[1]["parts"][0]["functionResponse"]["response"]["result"] == "contenido"
