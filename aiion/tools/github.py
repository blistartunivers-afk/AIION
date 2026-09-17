"""aiion/tools/github.py — 12 tools nativas de GitHub (sin MCP server necesario).
Requiere: GITHUB_TOKEN en variables de entorno o ~/.github_token"""
import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse

GITHUB_API = "https://api.github.com"

def _get_token() -> str:
    """Obtiene el token de GitHub desde env o archivo."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    # Fallback: archivo en home
    token_file = os.path.expanduser("~/.github_token")
    if os.path.exists(token_file):
        return open(token_file).read().strip()
    return ""

def _gh_request(path: str, method="GET", body=None) -> dict:
    """Llama a la API REST de GitHub."""
    token = _get_token()
    if not token:
        return {"error": "GITHUB_TOKEN no configurado. Exporta GITHUB_TOKEN o crea ~/.github_token"}
    
    url = f"{GITHUB_API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════════════════════
# 12 TOOLS DE GITHUB
# ═══════════════════════════════════════════════════════════════════════════════

def tool_gh_whoami() -> str:
    """Retorna el usuario autenticado de GitHub."""
    d = _gh_request("/user")
    if "error" in d:
        return f"Error: {d['error']}"
    return f"Usuario: {d.get('login')} | Nombre: {d.get('name','—')} | Repos públicos: {d.get('public_repos')} | Seguidores: {d.get('followers')}"

def tool_gh_list_repos(limit: int = 10) -> str:
    """Lista los repositorios del usuario autenticado."""
    d = _gh_request(f"/user/repos?per_page={limit}&sort=updated")
    if "error" in d:
        return f"Error: {d['error']}"
    if not isinstance(d, list):
        return str(d)
    if not d:
        return "Sin repositorios"
    lines = []
    for r in d:
        vis = "🔒" if r['private'] else "🌐"
        desc = r.get('description') or "—"
        lines.append(f"{vis} {r['full_name']} — {desc[:60]}")
    return "\n".join(lines)

def tool_gh_get_repo(repo: str) -> str:
    """Obtiene detalles de un repositorio (owner/repo)."""
    d = _gh_request(f"/repos/{repo}")
    if "error" in d:
        return f"Error: {d['error']}"
    return (f"{d.get('full_name')}: {d.get('description','—')}\n"
            f"  ⭐ {d.get('stargazers_count')} | 🍴 {d.get('forks_count')} | "
            f"Lenguaje: {d.get('language','—')} | {'Privado' if d.get('private') else 'Público'}")

def tool_gh_create_repo(name: str, description: str = "", private: bool = False) -> str:
    """Crea un nuevo repositorio."""
    d = _gh_request("/user/repos", method="POST", body={
        "name": name,
        "description": description,
        "private": private
    })
    if "error" in d:
        return f"Error: {d['error']}"
    return f"✅ Repo creado: {d.get('html_url')}"

def tool_gh_get_file(repo: str, path: str) -> str:
    """Lee el contenido de un archivo en un repo."""
    d = _gh_request(f"/repos/{repo}/contents/{path}")
    if "error" in d:
        return f"Error: {d['error']}"
    if "content" in d:
        content = base64.b64decode(d["content"]).decode("utf-8", errors="replace")
        return content[:5000]
    return str(d)

def tool_gh_list_files(repo: str, path: str = "") -> str:
    """Lista archivos de un directorio en un repo."""
    d = _gh_request(f"/repos/{repo}/contents/{path}")
    if "error" in d:
        return f"Error: {d['error']}"
    if not isinstance(d, list):
        return str(d)
    if not d:
        return "Directorio vacío"
    lines = []
    for f in d:
        icon = "📁" if f['type'] == 'dir' else "📄"
        lines.append(f"{icon} {f['name']}")
    return "\n".join(lines)

def tool_gh_search_repos(query: str, limit: int = 5) -> str:
    """Busca repositorios públicos en GitHub."""
    q = urllib.parse.quote(query)
    d = _gh_request(f"/search/repositories?q={q}&per_page={limit}")
    if "error" in d:
        return f"Error: {d['error']}"
    items = d.get("items", [])
    if not items:
        return f"Sin resultados para: {query}"
    lines = []
    for r in items:
        lines.append(f"⭐{r['stargazers_count']} {r['full_name']} — {r.get('description','—')[:60]}")
    return "\n".join(lines)

def tool_gh_search_code(query: str, limit: int = 5) -> str:
    """Busca código en GitHub."""
    q = urllib.parse.quote(query)
    d = _gh_request(f"/search/code?q={q}&per_page={limit}")
    if "error" in d:
        return f"Error: {d['error']}"
    items = d.get("items", [])
    if not items:
        return f"Sin resultados de código para: {query}"
    lines = []
    for i in items:
        lines.append(f"📄 {i['repository']['full_name']}: {i['path']}")
    return "\n".join(lines)

def tool_gh_list_issues(repo: str, state: str = "open") -> str:
    """Lista issues de un repositorio (open|closed|all)."""
    d = _gh_request(f"/repos/{repo}/issues?state={state}&per_page=20")
    if "error" in d:
        return f"Error: {d['error']}"
    if not isinstance(d, list):
        return str(d)
    if not d:
        return f"Sin issues ({state})"
    lines = []
    for i in d:
        if 'pull_request' in i:
            continue  # Saltar PRs
        lines.append(f"#{i['number']} [{i['state']}] {i['title']}")
    return "\n".join(lines) if lines else "Sin issues (solo PRs)"

def tool_gh_create_issue(repo: str, title: str, body: str = "") -> str:
    """Crea un issue en un repositorio."""
    d = _gh_request(f"/repos/{repo}/issues", method="POST", body={
        "title": title,
        "body": body
    })
    if "error" in d:
        return f"Error: {d['error']}"
    return f"✅ Issue creado: #{d.get('number')} {d.get('html_url')}"

def tool_gh_list_commits(repo: str, limit: int = 10) -> str:
    """Lista commits de un repositorio."""
    d = _gh_request(f"/repos/{repo}/commits?per_page={limit}")
    if "error" in d:
        return f"Error: {d['error']}"
    if not isinstance(d, list):
        return str(d)
    if not d:
        return "Sin commits"
    lines = []
    for c in d:
        msg = c['commit']['message'].split('\n')[0][:60]
        lines.append(f"🔹 {c['sha'][:7]} {msg}")
    return "\n".join(lines)

def tool_gh_list_branches(repo: str) -> str:
    """Lista ramas de un repositorio."""
    d = _gh_request(f"/repos/{repo}/branches")
    if "error" in d:
        return f"Error: {d['error']}"
    if not isinstance(d, list):
        return str(d)
    if not d:
        return "Sin ramas"
    return "\n".join([f"🌿 {b['name']}" for b in d])

# ═══════════════════════════════════════════════════════════════════════════════
# MAPA PARA REGISTRO
# ═══════════════════════════════════════════════════════════════════════════════

GITHUB_TOOLS = [
    {"type":"function","function":{"name":"gh_whoami","description":"Retorna el usuario autenticado de GitHub","parameters":{"type":"object","properties":{},"required":[]}}},
    {"type":"function","function":{"name":"gh_list_repos","description":"Lista los repositorios del usuario autenticado","parameters":{"type":"object","properties":{"limit":{"type":"integer","description":"Máximo de repos (default 10)"}},"required":[]}}},
    {"type":"function","function":{"name":"gh_get_repo","description":"Obtiene detalles de un repositorio","parameters":{"type":"object","properties":{"repo":{"type":"string","description":"owner/repo"}},"required":["repo"]}}},
    {"type":"function","function":{"name":"gh_create_repo","description":"Crea un nuevo repositorio","parameters":{"type":"object","properties":{"name":{"type":"string"},"description":{"type":"string"},"private":{"type":"boolean"}},"required":["name"]}}},
    {"type":"function","function":{"name":"gh_get_file","description":"Lee el contenido de un archivo en un repo","parameters":{"type":"object","properties":{"repo":{"type":"string","description":"owner/repo"},"path":{"type":"string","description":"Ruta del archivo"}},"required":["repo","path"]}}},
    {"type":"function","function":{"name":"gh_list_files","description":"Lista archivos de un directorio en un repo","parameters":{"type":"object","properties":{"repo":{"type":"string"},"path":{"type":"string","description":"Directorio (default raíz)"}},"required":["repo"]}}},
    {"type":"function","function":{"name":"gh_search_repos","description":"Busca repositorios públicos en GitHub","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
    {"type":"function","function":{"name":"gh_search_code","description":"Busca código en GitHub","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
    {"type":"function","function":{"name":"gh_list_issues","description":"Lista issues de un repositorio","parameters":{"type":"object","properties":{"repo":{"type":"string"},"state":{"type":"string","description":"open|closed|all"}},"required":["repo"]}}},
    {"type":"function","function":{"name":"gh_create_issue","description":"Crea un issue en un repositorio","parameters":{"type":"object","properties":{"repo":{"type":"string"},"title":{"type":"string"},"body":{"type":"string"}},"required":["repo","title"]}}},
    {"type":"function","function":{"name":"gh_list_commits","description":"Lista commits de un repositorio","parameters":{"type":"object","properties":{"repo":{"type":"string"},"limit":{"type":"integer"}},"required":["repo"]}}},
    {"type":"function","function":{"name":"gh_list_branches","description":"Lista ramas de un repositorio","parameters":{"type":"object","properties":{"repo":{"type":"string"}},"required":["repo"]}}},
]

GITHUB_TOOL_MAP = {
    "gh_whoami": tool_gh_whoami,
    "gh_list_repos": tool_gh_list_repos,
    "gh_get_repo": tool_gh_get_repo,
    "gh_create_repo": tool_gh_create_repo,
    "gh_get_file": tool_gh_get_file,
    "gh_list_files": tool_gh_list_files,
    "gh_search_repos": tool_gh_search_repos,
    "gh_search_code": tool_gh_search_code,
    "gh_list_issues": tool_gh_list_issues,
    "gh_create_issue": tool_gh_create_issue,
    "gh_list_commits": tool_gh_list_commits,
    "gh_list_branches": tool_gh_list_branches,
}