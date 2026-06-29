

class TestRouter:
    def test_fallback_requires_auth(self, client):
        resp = client.get("/api/fallback", headers={"Authorization": "Bearer invalid_key"})
        assert resp.status_code == 401
