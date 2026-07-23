import asyncio
from aiohttp.test_utils import TestClient, TestServer
from aiion.api import create_app, set_token_for_tests, reset_for_tests


def create_test_client():
    """Crea un TestClient para la app AIION con token de prueba."""
    app = create_app()
    set_token_for_tests("test-token")
    server = TestServer(app)
    client = TestClient(server)
    return client


def test_health_endpoint():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["ok"] is True
            assert data["service"] == "aiion-api"
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_auth_required_endpoints():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            # Sin token
            resp = await client.get("/memory")
            assert resp.status == 401
            
            # Con token incorrecto
            resp = await client.get("/memory", headers={"Authorization": "Bearer wrong-token"})
            assert resp.status == 401

            # Con token correcto
            resp = await client.get("/memory", headers={"Authorization": "Bearer test-token"})
            assert resp.status == 200
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_status_endpoint():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.get("/status")
            assert resp.status == 200
            data = await resp.json()
            assert "version" in data
            assert "agents" in data
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_plan_endpoint_invalid_json():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.post("/plan", headers={"Authorization": "Bearer test-token"}, data="invalid")
            assert resp.status == 400
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_agents_endpoint_public():
    """Test que /agents es público (no requiere auth)."""
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.get("/agents")
            assert resp.status == 200
            data = await resp.json()
            assert "agents" in data
            assert "total" in data
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_memory_search_endpoint():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            # Sin query
            resp = await client.get("/memory/search", headers={"Authorization": "Bearer test-token"})
            assert resp.status == 400
            
            # Con query
            resp = await client.get("/memory/search?q=test", headers={"Authorization": "Bearer test-token"})
            assert resp.status == 200
            data = await resp.json()
            assert "query" in data
            assert "hits" in data
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_audit_endpoint():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.get("/audit?tail=5", headers={"Authorization": "Bearer test-token"})
            assert resp.status == 200
            data = await resp.json()
            assert "events" in data
            assert "count" in data
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())


def test_stats_endpoint():
    async def _test():
        client = create_test_client()
        try:
            await client.start_server()
            resp = await client.get("/stats", headers={"Authorization": "Bearer test-token"})
            assert resp.status == 200
            data = await resp.json()
            assert isinstance(data, dict)
        finally:
            await client.close()
            reset_for_tests()
    asyncio.run(_test())