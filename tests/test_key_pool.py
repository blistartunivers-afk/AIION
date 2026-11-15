"""Fuentes compartidas y rotación del pool de Ollama Cloud."""
import io
import json
import urllib.error

import pytest

from aiion.llm import client, keys


def test_shared_blist_keys_are_loaded_when_aiion_has_none(tmp_path, monkeypatch):
    (tmp_path / ".blist_keys").write_text(
        "gemini|ignore\nollama|first\nollama|second\nollama|first\n")
    monkeypatch.setattr(keys, "AIION_HOME", tmp_path / "aiion_data")
    monkeypatch.setattr(keys.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    assert keys.load_api_keys() == ["first", "second"]


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
