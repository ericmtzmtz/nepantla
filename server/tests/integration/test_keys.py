

class TestKeys:
    def test_list_keys_requires_auth(self, client):
        resp = client.get("/api/keys", headers={"Authorization": "Bearer invalid_key"})
        assert resp.status_code == 401
