"""
tests/test_subagentes_main.py — Tests para aiion/subagentes/__main__.py

Cubre F3.1: cobertura del CLI unificado de subagentes (era 0%).
"""
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

from aiion.subagentes import __main__ as sub_main


# ─────────────────────────────────────────────────────────────
#  help / sin args
# ─────────────────────────────────────────────────────────────
def test_main_sin_args_imprime_doc(capsys):
    with patch.object(sys, "argv", ["subagentes"]):
        assert sub_main.main(None) == 0
    out = capsys.readouterr().out
    assert "python -m aiion.subagentes" in out
    assert "list" in out
    assert "describe" in out
    assert "call" in out


def test_main_help_flag(capsys):
    assert sub_main.main(["-h"]) == 0
    assert "Uso:" in capsys.readouterr().out or "list" in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["-h", "--help", "help"])
def test_main_variants_help(flag, capsys):
    assert sub_main.main([flag]) == 0


# ─────────────────────────────────────────────────────────────
#  list
# ─────────────────────────────────────────────────────────────
def test_main_list(capsys):
    """`list` itera sobre REGISTRY."""
    fake_sara = MagicMock()
    fake_sara.name = "sara"
    fake_sara.version = "0.1"
    fake_sara.description = "SARA digital"
    fake_sara.capabilities = ["sensor_status", "voice"]

    fake_other = MagicMock()
    fake_other.name = "memory_keeper"
    fake_other.version = "0.2"
    fake_other.description = "memory desc"
    fake_other.capabilities = ["stats"]

    with patch.object(sub_main, "list_subagentes", return_value=[fake_sara, fake_other]):
        assert sub_main.main(["list"]) == 0

    out = capsys.readouterr().out
    assert "subagente(s)" in out
    assert "sara" in out
    assert "v0.1" in out
    assert "memory_keeper" in out
    assert "caps: sensor_status, voice" in out


# ─────────────────────────────────────────────────────────────
#  describe
# ─────────────────────────────────────────────────────────────
def test_main_describe_sin_nombre(capsys):
    assert sub_main.main(["describe"]) == 2
    out = capsys.readouterr().out
    assert "Falta nombre" in out


def test_main_describe_ok(capsys):
    fake = MagicMock()
    fake.describe.return_value = {"name": "sara", "caps": ["a", "b"]}
    with patch.object(sub_main, "get_subagente", return_value=fake):
        assert sub_main.main(["describe", "sara"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["name"] == "sara"


def test_main_describe_no_existe(capsys):
    from aiion.subagentes.base import SubagenteError
    with patch.object(sub_main, "get_subagente",
                       side_effect=SubagenteError("no existe 'xxx'")):
        assert sub_main.main(["describe", "xxx"]) == 1
    out = capsys.readouterr().out
    assert "no existe" in out


# ─────────────────────────────────────────────────────────────
#  call
# ─────────────────────────────────────────────────────────────
def test_main_call_sin_args(capsys):
    assert sub_main.main(["call"]) == 2
    assert "Uso: call" in capsys.readouterr().out


def test_main_call_solo_un_arg(capsys):
    assert sub_main.main(["call", "sara"]) == 2
    assert "Uso: call" in capsys.readouterr().out


def test_main_call_json_invalido(capsys):
    assert sub_main.main(["call", "sara", "info", "{malformed"]) == 2
    out = capsys.readouterr().out
    assert "Args inválidos" in out


def test_main_call_subagente_no_existe(capsys):
    from aiion.subagentes.base import SubagenteError
    with patch.object(sub_main, "get_subagente",
                       side_effect=SubagenteError("missing 'xxx'")):
        assert sub_main.main(["call", "xxx", "info"]) == 1
    out = capsys.readouterr().out
    assert "missing" in out


def test_main_call_ok(capsys):
    fake = MagicMock()
    fake.dispatch.return_value = {"ok": True, "result": 42}
    with patch.object(sub_main, "get_subagente", return_value=fake):
        assert sub_main.main(["call", "sara", "info"]) == 0
    fake.dispatch.assert_called_with("info", {})
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["ok"] is True
    assert parsed["result"] == 42


def test_main_call_con_args_json(capsys):
    fake = MagicMock()
    fake.dispatch.return_value = {"ok": True}
    with patch.object(sub_main, "get_subagente", return_value=fake):
        assert sub_main.main(["call", "sara", "act", '{"foo": "bar"}']) == 0
    fake.dispatch.assert_called_with("act", {"foo": "bar"})


def test_main_call_resultado_no_ok(capsys):
    """Cuando dispatch devuelve ok=False, retorna 1."""
    fake = MagicMock()
    fake.dispatch.return_value = {"ok": False, "error": "boom"}
    with patch.object(sub_main, "get_subagente", return_value=fake):
        assert sub_main.main(["call", "sara", "act"]) == 1
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["ok"] is False


# ─────────────────────────────────────────────────────────────
#  comando no reconocido
# ─────────────────────────────────────────────────────────────
def test_main_comando_no_reconocido(capsys):
    assert sub_main.main(["foobar"]) == 2
    out = capsys.readouterr().out
    assert "no reconocido" in out
    assert "list" in out and "describe" in out and "call" in out


# ─────────────────────────────────────────────────────────────
#  argv fallback sys.argv
# ─────────────────────────────────────────────────────────────
def test_main_usa_sys_argv_si_paso_none(capsys):
    with patch.object(sys, "argv", ["subagentes", "list"]):
        with patch.object(sub_main, "list_subagentes", return_value=[]):
            assert sub_main.main(None) == 0
    out = capsys.readouterr().out
    # El REGISTRY tiene 3 subagentes del bridge, así que validamos que salga la lista
    assert "subagente(s)" in out
