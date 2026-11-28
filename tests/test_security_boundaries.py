"""Security boundary regressions; no real provider, Android, or agent startup."""
import ast
import hmac
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def definitions(file, names, ns):
    source = file.read_text()
    nodes = [n for n in ast.parse(source).body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(file), 'exec'), ns)


class Boundaries(unittest.TestCase):
    def test_honeypot_payload_is_a_literal_argument(self):
        paths = [p for p in ROOT.rglob('*honeypot.py') if not p.is_symlink()]
        if not paths: self.skipTest('No honeypot in this repository')
        for path in paths:
            calls = []
            class Socket:
                used = False
                def setsockopt(self, *a): pass
                def bind(self, *a): pass
                def listen(self, *a): pass
                def close(self): pass
                def accept(self):
                    if self.used: raise RuntimeError('end of fixture')
                    self.used = True
                    return SimpleNamespace(send=lambda x: None, recv=lambda n: b'$(printf MARKER)',
                                           settimeout=lambda n: None, close=lambda: None), ('192.0.2.1', 1)
            ns = dict(socket=SimpleNamespace(socket=lambda *a: Socket(), AF_INET=1, SOCK_STREAM=1,
                      SOL_SOCKET=1, SO_REUSEADDR=1), HONEY_PORT=2222,
                      logging=SimpleNamespace(info=lambda *a: None), log_to_db=lambda *a: None,
                      subprocess=SimpleNamespace(run=lambda args, **kw: calls.append((args, kw))), print=lambda *a: None)
            definitions(path, {'start_stealth_honeypot'}, ns)
            ns['start_stealth_honeypot']()
            self.assertEqual(len(calls), 1)
            self.assertIsInstance(calls[0][0], list)
            self.assertIn('$(printf MARKER)', calls[0][0][4])
            self.assertFalse(calls[0][1].get('shell', False))

    def test_bridge_rejects_before_dispatch(self):
        path = ROOT / 'plugins/github_mcp_bridge_v2.py'
        if not path.exists(): self.skipTest('No GitHub bridge')
        class Base: pass
        calls = []
        ns = dict(BaseHTTPRequestHandler=Base, hmac=hmac, json=json, MCP_AUTH_TOKEN='synthetic-token',
                  MCP_ALLOWED_ORIGIN='', run_tool=lambda *args: calls.append(args) or 'ok')
        definitions(path, {'MCPHandler'}, ns)
        payload = json.dumps({'jsonrpc':'2.0', 'id':1, 'method':'tools/call',
                              'params':{'name':'create_repo','arguments':{'name':'synthetic'}}}).encode()
        for header, origin, status in [('', None, 401), ('Bearer wrong', None, 401),
                                       ('Bearer synthetic-token', 'https://untrusted.invalid', 403),
                                       ('Bearer synthetic-token', None, 200)]:
            responses = []
            headers = {'Content-Length':str(len(payload)), 'Authorization':header}
            if origin: headers['Origin'] = origin
            fake = SimpleNamespace(headers=headers, rfile=io.BytesIO(payload),
                 send_json=lambda data, code=200: responses.append((data, code)), send_sse=lambda data: None)
            fake._authorized = ns['MCPHandler']._authorized.__get__(fake)
            ns['MCPHandler'].do_POST(fake)
            self.assertEqual(responses[-1][1], status)
        self.assertEqual(calls, [('create_repo', {'name':'synthetic'})])
        ns['MCP_AUTH_TOKEN'] = ''
        responses = []
        fake.send_json = lambda data, code=200: responses.append(code)
        ns['MCPHandler'].do_POST(fake)
        self.assertEqual(responses, [503])
        self.assertEqual(len(calls), 1)

    def test_structured_arguments_cannot_become_shell(self):
        paths = [ROOT/'aiion/tools/android.py', ROOT/'bridges/aiion_core.py']
        paths = [p for p in paths if p.exists()]
        if not paths: self.skipTest('No structured Android tools')
        for path in paths:
            calls = []
            ns = {'subprocess':SimpleNamespace(run=lambda args, **kw: calls.append((args, kw)) or
                                               SimpleNamespace(returncode=0, stderr=''))}
            definitions(path, {'tool_notificacion'}, ns)
            marker = "' ; printf MARKER ; #"
            ns['tool_notificacion'](marker, marker)
            args, kw = calls[0]
            self.assertIsInstance(args, list)
            self.assertEqual(args[2], marker)
            self.assertEqual(args[4], marker)
            self.assertFalse(kw.get('shell', False))

    def test_named_cron_deletion_preserves_similar_and_unrelated_tasks(self):
        path = ROOT/'aiion/tools/android.py'
        if not path.exists(): path = ROOT/'bridges/aiion_core.py'
        calls = []
        before = '# report\n0 * * * * run-report\n# report-extra\n1 * * * * run-extra\n'
        def run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=before, stderr='')
        ns = {'subprocess':SimpleNamespace(run=run)}
        definitions(path, {'tool_eliminar_tarea'}, ns)
        self.assertTrue(ns['tool_eliminar_tarea']('report').startswith('OK'))
        self.assertEqual(calls[-1][1]['input'], '# report-extra\n1 * * * * run-extra\n')
        calls.clear()
        self.assertTrue(ns['tool_eliminar_tarea']('repo').startswith('Error'))
        self.assertEqual(len(calls),1)  # no write for partial matches


if __name__ == '__main__': unittest.main()
