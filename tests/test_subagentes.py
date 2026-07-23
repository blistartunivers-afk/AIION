"""
tests/test_subagentes.py — Tests del framework de sub-agentes AIION.

14 tests que cubren:
  - Base: registry, dispatch, capability-check, error handling
  - SARA: info, sensor_status integration
  - Security audit: risk score range, recommendations shape
  - Memory keeper: stats shape, self_check ok
"""
import json
import sys
import pytest

from aiion.subagentes.base import (
    REGISTRY,
    Subagente,
    SubagenteError,
    get_subagente,
    list_subagentes,
    reset_registry,
    subagente,
)


def _reload_subagentes():
    """Fuerza re-import de los 3 sub-módulos para que el decorator corra
    y los registre en REGISTRY. Útil después de reset_registry() en tests."""
    for mod_name in [
        "aiion.subagentes.sara_cerebro",
        "aiion.subagentes.security_audit",
        "aiion.subagentes.memory_keeper",
    ]:
        sys.modules.pop(mod_name, None)
    import aiion.subagentes.sara_cerebro  # noqa: F401
    import aiion.subagentes.security_audit  # noqa: F401
    import aiion.subagentes.memory_keeper  # noqa: F401


# ─────────────────────── Base ───────────────────────

class DummyAgent(Subagente):
    name = "dummy_test"
    capabilities = ["ping", "echo"]
    def handle(self, capability, args):
        if capability == "ping":
            return {"pong": True, "ts": 1.0}
        if capability == "echo":
            return {"echoed": args.get("text", "")}


class FailingAgent(Subagente):
    name = "failing_test"
    capabilities = ["boom"]
    def handle(self, capability, args):
        raise RuntimeError("intentional")


class DisabledAgent(Subagente):
    name = "disabled_test"
    capabilities = ["x"]
    enabled = False
    def handle(self, capability, args):
        return {"x": 1}


@pytest.fixture(autouse=True)
def _clean_registry():
    """Limpia el registry antes y después de cada test."""
    reset_registry()
    yield
    reset_registry()


def test_registry_creates_instance():
    @subagente
    class TmpAgent(Subagente):
        name = "tmp_create"
        capabilities = ["do"]
        def handle(self, capability, args):
            return {}

    assert "tmp_create" in REGISTRY
    assert isinstance(REGISTRY["tmp_create"], TmpAgent)
    assert hasattr(TmpAgent, "instance")


def test_registry_duplicate_name_allowed():
    """Re-decorar con mismo name no lanza, solo sobreescribe."""
    @subagente
    class A(Subagente):
        name = "dup"
        capabilities = ["x"]
        def handle(self, capability, args): return {"v": 1}

    @subagente
    class B(Subagente):
        name = "dup"
        capabilities = ["y"]
        def handle(self, capability, args): return {"v": 2}

    # última registrada gana
    assert "y" in REGISTRY["dup"].capabilities


def test_get_subagente_not_found():
    with pytest.raises(SubagenteError, match="no registrado"):
        get_subagente("does_not_exist")


def test_dispatch_capability_not_allowed():
    @subagente
    class T(Subagente):
        name = "perm_test"
        capabilities = ["allowed"]
        def handle(self, capability, args): return {"ok": 1}

    res = get_subagente("perm_test").dispatch("blocked", {})
    assert res["ok"] is False
    assert "no permitida" in res["error"]


def test_dispatch_handler_exception():
    @subagente
    class T(Subagente):
        name = "err_test"
        capabilities = ["run"]
        def handle(self, capability, args):
            raise ValueError("fail")
    res = get_subagente("err_test").dispatch("run", {})
    assert res["ok"] is False
    assert "fail" in res["error"]


def test_dispatch_ok():
    @subagente
    class T(Subagente):
        name = "ok_test"
        capabilities = ["hello"]
        def handle(self, capability, args):
            return {"greet": f"hi {args.get('who', 'world')}"}
    res = get_subagente("ok_test").dispatch("hello", {"who": "estiven"})
    assert res["ok"] is True
    assert res["result"]["greet"] == "hi estiven"


def test_subagente_disabled():
    @subagente
    class T(Subagente):
        name = "off_test"
        capabilities = ["x"]
        enabled = False
        def handle(self, capability, args): return {"x": 1}
    res = get_subagente("off_test").dispatch("x", {})
    assert res["ok"] is False
    assert "deshabilitado" in res["error"]


def test_describe_format():
    @subagente
    class T(Subagente):
        name = "desc_test"
        capabilities = ["a", "b"]
        def handle(self, capability, args): return {}
    d = get_subagente("desc_test").describe()
    assert d["name"] == "desc_test"
    assert set(d["capabilities"]) == {"a", "b"}
    assert d["enabled"] is True
    assert "version" in d


def test_list_subagentes_only_enabled():
    @subagente
    class A(Subagente):
        name = "l1"; capabilities = ["x"]; enabled = True
        def handle(self, c, a): return {}
    @subagente
    class B(Subagente):
        name = "l2"; capabilities = ["x"]; enabled = False
        def handle(self, c, a): return {}

    all_ = list_subagentes(only_enabled=False)
    enabled = list_subagentes(only_enabled=True)
    assert len(all_) == 2
    assert len(enabled) == 1
    assert enabled[0].name == "l1"


# ─────────────────────── SARA ───────────────────────

def test_sara_info_capability():
    """SARA responde a 'info' con metadata estructurada."""
    _reload_subagentes()
    sub = get_subagente("sara")
    res = sub.dispatch("info", {})
    assert res["ok"] is True
    assert res["result"]["name"] == "sara"
    assert "sensor_status" in res["result"]["capabilities"]
    assert isinstance(res["result"]["tools"], list)


def test_sara_sensor_status_calls_tool():
    """SARA.sensor_status delega a get_android_status (degradación segura)."""
    _reload_subagentes()
    sub = get_subagente("sara")
    res = sub.dispatch("sensor_status", {"sensor": "battery"})
    # Puede devolver data real o warning si tools.system no está
    assert res["ok"] is True
    assert "sensor" in res["result"]
    assert res["result"]["sensor"] == "battery"


# ─────────────────────── Security Audit ───────────────────────

def test_security_audit_risk_score_in_range():
    """risk_scan devuelve score 0-100 + rating A-F."""
    _reload_subagentes()
    sub = get_subagente("security_audit")
    res = sub.dispatch("risk_scan", {})
    assert res["ok"] is True
    assert 0 <= res["result"]["score"] <= 100
    assert res["result"]["rating"] in {"A", "B", "C", "D", "F"}
    assert "high_risk" in res["result"]
    assert "medium_risk" in res["result"]
    assert "low_risk" in res["result"]


# ─────────────────────── Memory Keeper ───────────────────────

def test_memory_keeper_stats_shape():
    """stats devuelve métricas de memoria+history."""
    _reload_subagentes()
    sub = get_subagente("memory_keeper")
    res = sub.dispatch("stats", {})
    assert res["ok"] is True
    assert "data_dir" in res["result"]
    assert "checked_at" in res["result"]
    # al menos uno de los dos puede existir
    assert "memory_md" in res["result"] or "history" in res["result"]


def test_memory_keeper_self_check_ok():
    """self_check no debe fallar en el entorno actual."""
    _reload_subagentes()
    sub = get_subagente("memory_keeper")
    res = sub.dispatch("self_check", {})
    assert res["ok"] is True
    assert res["result"]["ok"] is True
    assert isinstance(res["result"]["checks"], list)
    assert len(res["result"]["checks"]) >= 1
