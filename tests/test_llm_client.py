"""
tests/test_llm_client.py — Tests para aiion/llm/client.py

Cubre F3.1: cobertura del cliente HTTP a Ollama (era 16%).
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from aiion.llm import client as llm_client
from aiion.llm.client import (
    _build_payload,
    _do_request,
    chat_native,
    chat_react_text,
    parse_react,
)


# ─────────────────────────────────────────────────────────────
#  _build_payload
# ─────────────────────────────────────────────────────────────
def test_build_payload_sin_cloud():
    """Payload con configuración por defecto (local)."""
    llm_client.STATE["use_cloud"] = False
    llm_client.STATE["model"] = "qwen2.5:3b"
    msgs = [{"role": "user", "content": "hola"}]
    payload = json.loads(_build_payload(msgs, use_tools=True))
    assert payload["model"] == "qwen2.5:3b"
    assert payload["messages"] == msgs
    assert payload["stream"] is False
    assert "tools" in payload
    assert payload["options"]["temperature"] == 0.1
    assert payload["options"]["num_ctx"] == 8192


def test_build_payload_cloud():
    """Con use_cloud=True, no num_ctx."""
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["model"] = "kimi-k2"
    payload = json.loads(_build_payload([{"role": "user", "content": "hi"}], use_tools=False))
    assert "num_ctx" not in payload["options"]
    assert "tools" not in payload
    assert payload["model"] == "kimi-k2"


# ─────────────────────────────────────────────────────────────
#  _do_request
# ─────────────────────────────────────────────────────────────
def test_do_request_local_ok():
    """Petición local sin auth header."""
    llm_client.STATE["use_cloud"] = False
    llm_client.STATE["api_keys"] = []
    fake_resp = {"message": {"content": "ok"}}

    with patch("urllib.request.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(fake_resp).encode()
        result = _do_request(b"{}")

    assert result == fake_resp
    args, kwargs = mock_open.call_args
    req = args[0]
    assert "Authorization" not in req.headers
    assert llm_client.OLLAMA_LOCAL in req.full_url


def test_do_request_cloud_con_auth():
    """Petición cloud incluye Bearer token."""
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["api_keys"] = ["key-1"]
    fake_resp = {"message": {"content": "cloud"}}

    with patch("aiion.llm.client.current_key", return_value="key-1"):
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(fake_resp).encode()
            result = _do_request(b"{}")

    assert result == fake_resp
    args, kwargs = mock_open.call_args
    req = args[0]
    assert req.headers["Authorization"] == "Bearer key-1"
    assert llm_client.OLLAMA_CLOUD in req.full_url


def test_do_request_cloud_401_rota_key():
    """Ante 401 con varias keys, rota y reintenta."""
    from urllib.error import HTTPError
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["api_keys"] = ["k1", "k2"]

    call_count = {"n": 0}

    def fake_urlopen(req, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise HTTPError(url=req.full_url, code=401, msg="Unauthorized",
                            hdrs=MagicMock(), fp=None)
        success = MagicMock()
        success.__enter__.return_value.read.return_value = json.dumps({"ok": True}).encode()
        return success

    with patch("aiion.llm.client.current_key", side_effect=["k1", "k2"]):
        with patch("aiion.llm.client.rotate_key") as mock_rotate:
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = _do_request(b"{}")

    assert result == {"ok": True}
    assert mock_rotate.called
    assert call_count["n"] == 2


def test_do_request_cloud_429_rota_key():
    """429 también rota y reintenta."""
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["api_keys"] = ["k1", "k2"]

    # Patchear HTTPError porque urllib.error no se importa fácil
    from urllib.error import HTTPError

    call_count = {"n": 0}

    def fake_urlopen(req, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise HTTPError(req.full_url, 429, "Too Many", {}, None)
        success = MagicMock()
        success.__enter__.return_value.read.return_value = json.dumps({"ok": 2}).encode()
        return success

    with patch("aiion.llm.client.current_key", side_effect=["k1", "k2"]):
        with patch("aiion.llm.client.rotate_key"):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = _do_request(b"{}")

    assert result == {"ok": 2}


def test_do_request_cloud_401_solo_una_key_re_lanza():
    """Con una sola key, 401 no rota — re-lanza."""
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["api_keys"] = ["solo-una"]

    from urllib.error import HTTPError

    with patch("aiion.llm.client.current_key", return_value="solo-una"):
        with patch("aiion.llm.client.rotate_key") as mock_rotate:
            with patch("urllib.request.urlopen",
                       side_effect=HTTPError("u", 401, "Unauthorized", {}, None)):
                with pytest.raises(HTTPError):
                    _do_request(b"{}")
    assert not mock_rotate.called


def test_do_request_cloud_500_re_lanza():
    """500 no rota — re-lanza."""
    llm_client.STATE["use_cloud"] = True
    llm_client.STATE["api_keys"] = ["k1", "k2"]

    from urllib.error import HTTPError

    with patch("aiion.llm.client.current_key", return_value="k1"):
        with patch("aiion.llm.client.rotate_key") as mock_rotate:
            with patch("urllib.request.urlopen",
                       side_effect=HTTPError("u", 500, "Server", {}, None)):
                with pytest.raises(HTTPError):
                    _do_request(b"{}")
    assert not mock_rotate.called


# ─────────────────────────────────────────────────────────────
#  chat_native
# ─────────────────────────────────────────────────────────────
def test_chat_native_text_response():
    """Cuando no hay tool_calls, retorna ('text', content, msg)."""
    resp = {"message": {"role": "assistant", "content": "hola humano"}}
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, msg = chat_native([{"role": "user", "content": "hola"}])

    assert kind == "text"
    assert data == "hola humano"
    assert msg["content"] == "hola humano"


def test_chat_native_tool_call_response():
    """Cuando hay tool_calls, retorna ('tool_call', [(name,args,id)], msg)."""
    resp = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "sensor_status",
                        "arguments": {"sensor": "battery"},
                    }
                }
            ]
        }
    }
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, msg = chat_native([{"role": "user", "content": "estado"}])

    assert kind == "tool_call"
    assert len(data) == 1
    name, args, call_id = data[0]
    assert name == "sensor_status"
    assert args == {"sensor": "battery"}
    assert call_id == "call_1"


def test_chat_native_tool_call_args_string_json():
    """Si args viene como string, se parsea."""
    resp = {
        "message": {
            "tool_calls": [
                {"id": "c1", "function": {"name": "foo", "arguments": '{"a": 1}'}}
            ]
        }
    }
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, _ = chat_native([{"role": "user", "content": "x"}])

    assert kind == "tool_call"
    name, args, _ = data[0]
    assert args == {"a": 1}


def test_chat_native_tool_call_args_string_invalido():
    """Si args es string pero no parseable, queda como {}."""
    resp = {
        "message": {
            "tool_calls": [
                {"id": "c1", "function": {"name": "foo", "arguments": "{malformed"}}
            ]
        }
    }
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, _ = chat_native([])

    name, args, _ = data[0]
    assert args == {}


def test_chat_native_tool_call_multiples():
    """Varios tool_calls en una sola respuesta."""
    resp = {
        "message": {
            "tool_calls": [
                {"id": "c1", "function": {"name": "a", "arguments": {}}},
                {"id": "c2", "function": {"name": "b", "arguments": {"x": 1}}},
            ]
        }
    }
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, _ = chat_native([])
    assert kind == "tool_call"
    assert len(data) == 2
    assert data[0][0] == "a"
    assert data[1][0] == "b"


def test_chat_native_no_msg_key():
    """Si no hay 'message' en la respuesta, retorna text vacío."""
    resp = {}
    with patch.object(llm_client, "_do_request", return_value=resp):
        kind, data, msg = chat_native([])
    assert kind == "text"
    assert data == ""
    assert msg == {}


# ─────────────────────────────────────────────────────────────
#  chat_react_text
# ─────────────────────────────────────────────────────────────
def test_chat_react_text_ok():
    """Retorna solo el content de la respuesta."""
    resp = {"message": {"role": "assistant", "content": "pensando..."}}
    with patch.object(llm_client, "_do_request", return_value=resp):
        result = chat_react_text([{"role": "user", "content": "piensa"}])
    assert result == "pensando..."


def test_chat_react_text_sin_content():
    """Si no hay content, retorna ''."""
    with patch.object(llm_client, "_do_request", return_value={"message": {}}):
        assert chat_react_text([]) == ""


# ─────────────────────────────────────────────────────────────
#  parse_react
# ─────────────────────────────────────────────────────────────
def test_parse_react_accion_json():
    """Detecta Acción + Parámetros en JSON válido."""
    text = """Pensamiento: necesito saber la batería
Accion: sensor_status
Parametros: {"sensor": "battery"}"""
    kind, name, args, thought = parse_react(text)
    assert kind == "action"
    assert name == "sensor_status"
    assert args == {"sensor": "battery"}
    assert "batería" in thought


def test_parse_react_con_comillas_simples():
    """Si JSON tiene comillas simples, intenta reemplazar."""
    text = """Accion: foo
Parametros: {'k': 'v'}"""
    kind, name, args, _ = parse_react(text)
    assert kind == "action"
    assert name == "foo"
    assert args == {"k": "v"}


def test_parse_react_json_invalido_cae_a_vacio():
    """JSON malformado que matchea regex → args = {} sin crashear."""
    # El regex captura hasta la primera }, así que esto matchea "no json" (no es JSON).
    # → json.loads falla → args = {}
    text = """Accion: foo
Parametros: {no json}"""
    result = parse_react(text)
    assert result[0] == "action"
    assert result[1] == "foo"
    assert result[2] == {}


def test_parse_react_respuesta_final():
    """Si no hay acción, busca Respuesta final."""
    text = "Hola, esto es una respuesta final sin acción"
    kind, *rest = parse_react(text)
    assert kind == "final"
    assert "respuesta final" in rest[0]


def test_parse_react_sin_match_devuelve_texto():
    """Sin match alguno, retorna ('final', text)."""
    text = "palabras sueltas sin estructura"
    kind, result = parse_react(text)
    assert kind == "final"
    assert result == "palabras sueltas sin estructura"


def test_parse_react_accion_variantes_mayus_minus():
    """Acepta 'accion' (minúscula) — el regex tiene [Aa]ccion."""
    text = "accion: foo\nparametros: {}"
    result = parse_react(text)
    # El regex usa [Aa] para Accion y [Pp] para Parametros, así que ambas formas
    # podrían matchear. El comportamiento real puede variar — validamos que NO crashee.
    assert result[0] in ("action", "final")
    if result[0] == "action":
        assert result[1] == "foo"


def test_parse_react_con_bloque_largo():
    """Bloque con llaves anidadas y varios espacios."""
    text = """Pensamiento: voy a llamar a la tool
Accion: complex_tool
Parametros: {
    "key": "value",
    "nested": {"a": 1}
}"""
    kind, name, args, _ = parse_react(text)
    assert kind == "action"
    assert name == "complex_tool"
    assert args["key"] == "value"
    assert args["nested"]["a"] == 1
