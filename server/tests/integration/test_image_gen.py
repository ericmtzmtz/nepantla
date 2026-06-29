"""Integration tests for image generation endpoint."""


class TestImageGen:
    def test_requires_auth(self, client):
        """POST /v1/images/generations without auth returns 401."""
        resp = client.post(
            "/v1/images/generations",
            json={"prompt": "a cat"},
        )
        # No auth header at all → 422 (missing required header deps)
        # OR 401 if auth fails validation
        assert resp.status_code in (401, 422)

    def test_invalid_auth(self, client):
        """POST /v1/images/generations with invalid auth returns 401."""
        resp = client.post(
            "/v1/images/generations",
            json={"prompt": "a cat"},
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    def test_unknown_model_returns_404(self, client):
        """Direct model selection with nonexistent model returns 404."""
        resp = client.post(
            "/v1/images/generations",
            json={"prompt": "a cat", "model": "nonexistent-model"},
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        assert resp.status_code == 404

    def test_missing_prompt_returns_400(self, client):
        """POST without prompt returns 400."""
        resp = client.post(
            "/v1/images/generations",
            json={},
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        assert resp.status_code == 400

    def test_auto_routing_no_image_gen_models(self, client):
        """Auto-routing with no image_gen config returns 429 or 500 (no providers configured)."""
        resp = client.post(
            "/v1/images/generations",
            json={"prompt": "a cat", "model": "auto"},
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Without image_gen models in test DB, expect 429 (no route) or 5xx
        assert resp.status_code in (429, 500, 502)
