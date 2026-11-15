"""La selección de modelos debe migrar su propia base al arrancar."""
import sqlite3

import pytest

from aiion import db
from aiion.llm import keys, kalman


@pytest.mark.parametrize("module", [keys, kalman])
@pytest.mark.parametrize("existing", [False, True])
def test_selector_migrates_evolution_db(tmp_path, monkeypatch, module, existing):
    db_path = tmp_path / "evolution.db"
    if existing:
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE preserved(value TEXT)")
            conn.execute("INSERT INTO preserved VALUES ('keep')")
    monkeypatch.setattr(module, "EVOLUTION_DB", db_path)
    try:
        selector = module.KalmanModelSelector()
        selector.update("ollama", "sample", True, 10.0)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute("SELECT prov_id, model FROM model_performance").fetchone()
            assert row == ("ollama", "sample")
            if existing:
                assert conn.execute("SELECT value FROM preserved").fetchone()[0] == "keep"
    finally:
        db.close_all()
