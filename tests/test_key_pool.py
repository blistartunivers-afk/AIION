"""Fuentes compartidas y rotación del pool de Ollama Cloud."""
import io
import json
import urllib.error

import pytest

from aiion.llm import client, keys


def test_aiion_does_not_load_external_keys(tmp_path, monkeypatch):
    (tmp_path / ".blist_keys").write_text(
        "gemini|ignore\nollama|first\nollama|second\nollama|first\n")
    monkeypatch.setattr(keys, "AIION_HOME", tmp_path / "aiion_data")
    monkeypatch.setattr(keys.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    assert keys.load_api_keys() == []


def test_cloud_request_rotates_key_and_model_after_quota(tmp_path, monkeypatch):
    monkeypatch.setattr(keys, "_KEY_HEALTH", {})
    monkeypatch.setitem(keys.STATE, "provider", "ollama")
    monkeypatch.setitem(keys.STATE, "use_cloud", True)
    monkeypatch.setitem(keys.STATE, "api_keys", ["first", "second"])
    monkeypatch.setitem(keys.STATE, "key_index", 0)
    monkeypatch.setitem(keys.STATE, "model", "model-a")
    monkeypatch.setattr(keys, "PREFERRED_MODELS", ["model-b"])
    seen = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return b'{"message": {"content": "ok"}}'

    def fake_open(request, timeout):
        seen.append((request.get_header("Authorization"), json.loads(request.data)["model"]))
        if len(seen) <= 2:
            raise urllib.error.HTTPError(request.full_url, 429, "quota", {}, io.BytesIO(b"{}"))
        return Response()

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_open)
    payload = json.dumps({"model": "model-a", "messages": []}).encode()
    assert client._do_request(payload)["message"]["content"] == "ok"
    assert seen == [("Bearer first", "model-a"),
                    ("Bearer second", "model-a"),
                    ("Bearer first", "model-b")]


def test_nvidia_rotates_on_transient_failure(monkeypatch):
    monkeypatch.setattr(keys, "_KEY_HEALTH", {})
    for name, value in dict(provider="nvidia", use_cloud=True, model="model-a",
                            api_keys=["first", "second"], key_index=0).items():
        monkeypatch.setitem(keys.STATE, name, value)
    seen = []

    def read_json(request):
        seen.append(request.get_header("Authorization"))
        if len(seen) == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "busy", {}, io.BytesIO(b"{}"))
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(client, "_read_json", read_json)
    assert client.chat_native([{"role": "user", "content": "hola"}])[1] == "ok"
    assert seen == ["Bearer first", "Bearer second"]


def test_react_switches_to_configured_provider_after_pool_exhaustion(monkeypatch):
    for name, value in dict(provider="gemini", use_cloud=True, model="model-a",
                            api_keys=["first"], key_index=0).items():
        monkeypatch.setitem(keys.STATE, name, value)
    monkeypatch.setenv("AIION_FALLBACK_PROVIDERS", "gemini,nvidia")
    monkeypatch.setattr(client, "load_nvidia_keys", lambda: ["other"])
    seen = []

    def react(_messages, retry=0):
        seen.append(keys.STATE["provider"])
        if keys.STATE["provider"] == "gemini":
            raise keys.PoolCooldownError("quota")
        return "ok"

    monkeypatch.setattr(client, "_chat_react_text", react)
    assert client.chat_react_text([{"role": "user", "content": "hola"}]) == "ok"
    assert seen == ["gemini", "nvidia"]
    assert keys.STATE["provider"] == "nvidia"


def test_nvidia_prioritizes_blist_keys_without_loading_other_providers(tmp_path, monkeypatch):
    (tmp_path / ".blist_keys").write_text(
        "gemini|ignored\nnvidia|shared|model-a,model-b\n"
        "nvidia|shared\n# nvidia|ignored\nnvapi-legacy\n")
    (tmp_path / "nvidia_keys").write_text("shared\nlocal\n")
    monkeypatch.setattr(keys.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(keys, "AIION_HOME", tmp_path)
    monkeypatch.setenv("NVIDIA_API_KEY", "shared,extra")
    assert keys.load_nvidia_keys() == ["shared", "nvapi-legacy", "extra", "local"]
