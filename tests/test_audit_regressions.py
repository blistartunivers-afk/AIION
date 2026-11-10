from aiion import db
from aiion.tools.filesystem import tool_grep_search, tool_diff_files

def test_connection_reused(tmp_path):
    p = tmp_path / 'db.sqlite'
    try:
        assert db.get_conn(p) is db.get_conn(str(p))
    finally:
        db.close_all()

def test_search_treats_pattern_as_data(tmp_path):
    marker = tmp_path / 'injected'
    pattern = "'; touch " + str(marker) + "; #"
    p = tmp_path / 'text'; p.write_text(pattern)
    assert pattern in tool_grep_search(pattern, str(p))
    assert not marker.exists()

def test_diff_handles_quotes(tmp_path):
    a=tmp_path / "a'quoted"; b=tmp_path / "b'quoted"
    a.write_text('before\n'); b.write_text('after\n')
    result=tool_diff_files(str(a),str(b))
    assert 'before' in result and 'after' in result

def test_restore_preserves_backup(tmp_path):
    import ast, shutil
    from datetime import datetime
    from pathlib import Path
    source=Path(__file__).parents[1]/'aiion/core.py'
    node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='do_backup')
    env=dict(Path=Path,datetime=datetime,AIION_HOME=tmp_path/'data',c=lambda *a:str(a[-1]),shutil=shutil)
    env.update({name:'' for name in ['CY','BOLD','PU','CO','GR','YL','D_FG']})
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),env)
    backup=tmp_path/'data/backups/2026-01-01/data';backup.mkdir(parents=True)
    (backup/'memory.txt').write_text('saved')
    (tmp_path/'data/memory.txt').write_text('changed')
    env['do_backup']('restore')
    assert (tmp_path/'data/memory.txt').read_text()=='saved'
    assert (backup/'memory.txt').read_text()=='saved'
