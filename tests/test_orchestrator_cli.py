"""
tests/test_orchestrator_cli.py — Tests para aiion/orchestrator_cli.py

Cubre F3.1: cobertura del módulo CLI (era 0%).

Nota: este módulo imprime con códigos ANSI (colorama/lista). Validamos
sobre la versión sin códigos con una función helper.
"""
import json
import re
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from aiion.orchestrator_cli import (
    cmd_agents,
    cmd_submit,
    cmd_plan,
    cmd_stats,
    cmd_audit,
    main,
    _print_banner,
)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(s: str) -> str:
    """Quita códigos ANSI para asserts legibles."""
    return _ANSI.sub("", s)


@pytest.fixture
def fake_orch():
    """Mock del orchestrator con agencias y tasks simuladas."""
    with patch("aiion.orchestrator_cli.get_orchestrator") as mock_get:
        orch = mock_get.return_value

        # describe() devuelve spec con capabilities
        orch.list_agents.return_value = ["core", "security_audit"]
        orch.describe.side_effect = lambda n: SimpleNamespace(
            capabilities=["doctor", "sensor_status", "stats", "audit", "memory", "more"],
            description=f"Agente {n}",
        )

        ok_task = SimpleNamespace(
            id="t-001",
            status=SimpleNamespace(value="success"),
            duration_ms=42.5,
            error=None,
            result="ok",
        )
        err_task = SimpleNamespace(
            id="t-002",
            status=SimpleNamespace(value="error"),
            duration_ms=15.0,
            error="boom",
            result=None,
        )

        # submit devuelve ok en calls impares, err en pares
        orch.submit.side_effect = [ok_task, err_task]

        # audit
        orch.audit.tail.return_value = [
            {"ts": 1700000000.0, "event": "task_done", "agent": "core", "action": "doctor"},
            {"ts": 1700000001.5, "event": "denial", "agent": "x", "reason": "no_caps"},
        ]

        # stats
        orch.stats.return_value = {
            "total": 12,
            "success_rate": 91.7,
            "avg_latency_ms": 23.4,
            "by_status": {"success": 11, "error": 1},
            "by_agent": {"core": 8, "security_audit": 4},
        }

        # execute_plan
        orch.execute_plan.return_value = [ok_task, ok_task]

        yield orch


# ─────────────────────────────────────────────────────────────
#  _print_banner
# ─────────────────────────────────────────────────────────────
def test_print_banner(capsys):
    _print_banner("TEST")
    out = _clean(capsys.readouterr().out)
    assert "ORQUESTADOR AIION" in out
    assert "TEST" in out


# ─────────────────────────────────────────────────────────────
#  cmd_agents
# ─────────────────────────────────────────────────────────────
def test_cmd_agents_formato(capsys, fake_orch):
    assert cmd_agents([]) is None
    out = _clean(capsys.readouterr().out)
    assert "AGENTES REGISTRADOS" in out
    assert "core" in out
    assert "security_audit" in out
    assert "capabilities:" in out
    # Cuando hay >5 capabilities, debe mostrar "+N"
    assert "(+1)" in out


def test_cmd_agents_sin_extras_si_menos_5(capsys, fake_orch):
    fake_orch.describe.side_effect = lambda n: SimpleNamespace(
        capabilities=["a", "b", "c"], description=f"Agente {n}"
    )
    cmd_agents([])
    out = _clean(capsys.readouterr().out)
    assert "(+" not in out  # no debe haber "(+N)"


# ─────────────────────────────────────────────────────────────
#  cmd_submit
# ─────────────────────────────────────────────────────────────
def test_cmd_submit_sin_args(capsys):
    assert cmd_submit([]) == 1
    out = _clean(capsys.readouterr().out)
    assert "Uso: submit" in out


def test_cmd_submit_solo_2_args(capsys, fake_orch):
    assert cmd_submit(["core", "doctor"]) == 0
    out = _clean(capsys.readouterr().out)
    assert "EJECUTANDO  core.doctor" in out
    assert "status:" in out
    assert "success" in out
    assert "task_id:" in out
    assert "t-001" in out
    assert "latency:" in out
    assert "42.5 ms" in out


def test_cmd_submit_con_params_json(capsys, fake_orch):
    assert cmd_submit(["core", "doctor", '{"sensor":', '"battery"}']) == 0
    out = _clean(capsys.readouterr().out)
    assert "EJECUTANDO  core.doctor" in out
    # Verifica que se enviaron los params parseados
    args, kwargs = fake_orch.submit.call_args
    assert args[0] == "core"
    assert args[1] == "doctor"
    assert args[2] == {"sensor": "battery"}


def test_cmd_submit_json_invalido(capsys):
    assert cmd_submit(["core", "doctor", "{malformed"]) == 1
    out = _clean(capsys.readouterr().out)
    assert "JSON inválido" in out


def test_cmd_submit_task_con_error(capsys, fake_orch):
    """La 2da llamada devuelve err_task → rc=1 + imprime error."""
    cmd_submit(["core", "doctor"])  # 1era: ok
    rc = cmd_submit(["core", "doctor"])  # 2da: err
    assert rc == 1
    out = _clean(capsys.readouterr().out)
    assert "error:" in out
    assert "boom" in out


def test_cmd_submit_result_no_dict(capsys, fake_orch):
    """Cuando result es string, se imprime."""
    cmd_submit(["core", "doctor"])
    out = _clean(capsys.readouterr().out)
    assert "result:" in out
    assert "ok" in out


def test_cmd_submit_result_dict_no_se_imprime(capsys, fake_orch):
    """Cuando result es dict, NO se imprime (lo raro es que es la convención)."""
    err_dict = SimpleNamespace(
        id="t-3",
        status=SimpleNamespace(value="success"),
        duration_ms=10,
        error=None,
        result={"foo": "bar"},
    )
    fake_orch.submit.side_effect = [err_dict]
    cmd_submit(["core", "doctor"])
    out = _clean(capsys.readouterr().out)
    assert "result:" not in out


# ─────────────────────────────────────────────────────────────
#  cmd_plan
# ─────────────────────────────────────────────────────────────
def test_cmd_plan_sin_args(capsys):
    assert cmd_plan([]) == 1
    out = _clean(capsys.readouterr().out)
    assert "Uso: plan" in out


def test_cmd_plan_archivo_inexistente(capsys):
    assert cmd_plan(["/no/existe.json"]) == 1
    out = _clean(capsys.readouterr().out)
    assert "No existe" in out


def test_cmd_plan_json_invalido(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{no es json valido")
    assert cmd_plan([str(bad)]) == 1
    out = _clean(capsys.readouterr().out)
    assert "JSON inválido" in out


def test_cmd_plan_ok(tmp_path, capsys, fake_orch):
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps([
        {"agent": "core", "action": "doctor"},
        {"agent": "core", "action": "stats"},
    ]))
    cmd_plan([str(plan_file)])
    out = _clean(capsys.readouterr().out)
    assert "EJECUTANDO PLAN (2 pasos)" in out
    assert "2/2 tareas exitosas" in out


def test_cmd_plan_parcial(tmp_path, capsys, fake_orch):
    """Plan con 1 éxito + 1 error → imprime '1/2'."""
    ok = SimpleNamespace(status=SimpleNamespace(value="success"))
    err = SimpleNamespace(status=SimpleNamespace(value="error"))
    fake_orch.execute_plan.return_value = [ok, err]

    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps([{"a": 1}, {"b": 2}]))
    cmd_plan([str(plan_file)])
    out = _clean(capsys.readouterr().out)
    assert "1/2 tareas exitosas" in out


# ─────────────────────────────────────────────────────────────
#  cmd_stats
# ─────────────────────────────────────────────────────────────
def test_cmd_stats(capsys, fake_orch):
    cmd_stats([])
    out = _clean(capsys.readouterr().out)
    assert "MÉTRICAS" in out
    assert "total:" in out
    assert "12" in out
    assert "success_rate:" in out
    assert "91.7%" in out
    assert "avg_latency:" in out
    assert "23.4 ms" in out
    assert "by_status:" in out
    assert "success" in out
    assert "11" in out
    assert "by_agent:" in out
    assert "core" in out
    assert "8" in out


def test_cmd_stats_sin_avg_latency(capsys, fake_orch):
    fake_orch.stats.return_value = {
        "total": 0, "success_rate": "—", "by_status": {}, "by_agent": {}
    }
    cmd_stats([])
    out = _clean(capsys.readouterr().out)
    assert "MÉTRICAS" in out
    assert "avg_latency" not in out


# ─────────────────────────────────────────────────────────────
#  cmd_audit
# ─────────────────────────────────────────────────────────────
def test_cmd_audit_default(capsys, fake_orch):
    cmd_audit([])
    fake_orch.audit.tail.assert_called_with(10)
    out = _clean(capsys.readouterr().out)
    assert "ÚLTIMOS 10 EVENTOS" in out
    assert "task_done" in out
    assert "denial" in out


def test_cmd_audit_con_n(capsys, fake_orch):
    cmd_audit(["25"])
    fake_orch.audit.tail.assert_called_with(25)
    out = _clean(capsys.readouterr().out)
    assert "ÚLTIMOS 25 EVENTOS" in out


def test_cmd_audit_filtra_valores_no_escalares(capsys, fake_orch):
    fake_orch.audit.tail.return_value = [
        {"ts": 1.0, "event": "x", "meta": {"k": 1}, "list": [1, 2]},
    ]
    cmd_audit([])
    out = _clean(capsys.readouterr().out)
    # dicts y lists NO deben imprimirse
    assert "meta" not in out
    assert "list" not in out


# ─────────────────────────────────────────────────────────────
#  main
# ─────────────────────────────────────────────────────────────
def test_main_sin_args_imprime_doc(capsys):
    with patch("sys.argv", ["orchestrator_cli"]):  # sin args extra
        assert main() == 1
    out = _clean(capsys.readouterr().out)
    assert "Uso:" in out or "python -m aiion.orchestrator_cli" in out


def test_main_comando_inexistente(capsys):
    with patch("sys.argv", ["orchestrator_cli", "noexiste"]):
        assert main() == 1
    out = _clean(capsys.readouterr().out)
    assert "no existe" in out
    assert "Opciones:" in out


def test_main_dispatch_agents(capsys, fake_orch):
    with patch("sys.argv", ["orchestrator_cli", "agents"]):
        main()
    out = _clean(capsys.readouterr().out)
    assert "AGENTES REGISTRADOS" in out


def test_main_dispatch_stats(capsys, fake_orch):
    with patch("sys.argv", ["orchestrator_cli", "stats"]):
        main()
    out = _clean(capsys.readouterr().out)
    assert "MÉTRICAS" in out


def test_main_dispatch_audit(capsys, fake_orch):
    with patch("sys.argv", ["orchestrator_cli", "audit", "5"]):
        main()
    fake_orch.audit.tail.assert_called_with(5)


def test_main_keyboard_interrupt(capsys, fake_orch):
    with patch("aiion.orchestrator_cli.cmd_agents", side_effect=KeyboardInterrupt):
        with patch("sys.argv", ["orchestrator_cli", "agents"]):
            assert main() == 130
    out = _clean(capsys.readouterr().out)
    assert "Interrumpido" in out


def test_main_excepcion_inesperada(capsys, fake_orch):
    with patch("aiion.orchestrator_cli.cmd_agents", side_effect=RuntimeError("pepinillo")):
        with patch("sys.argv", ["orchestrator_cli", "agents"]):
            assert main() == 1
    captured = capsys.readouterr()
    out = _clean(captured.out)
    err = _clean(captured.err)
    assert "Error: pepinillo" in out
    assert "Traceback" in err  # traceback.print_exc() va a stderr
