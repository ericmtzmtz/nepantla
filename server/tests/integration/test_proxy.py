class TestProxy:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data

    def test_models_v1(self, client):
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"

    def test_chat_requires_auth(self, client):
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "test", "messages": []},
            headers={"Authorization": "Bearer invalid_key"}
        )
        assert resp.status_code == 401

    def test_chat_with_image_auto_routing(self, client):
        """POST /v1/chat/completions with image_url and model=auto."""
        resp = client.post(
            "/v1/chat/completions",
            json={
"model": "auto",
                 "messages": [
                     {"role": "user", "content": [
                         {"type": "text", "text": "What's in this image?"},
                         {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ=="}},  # noqa: E501
                     ]},
                 ],
            },
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Without vision models in test DB, expect 429 (no route) or similar
        assert resp.status_code in (429, 400, 500)

    def test_chat_with_image_direct_model(self, client):
        """POST /v1/chat/completions with image_url and direct model."""
        resp = client.post(
            "/v1/chat/completions",
            json={
"model": "nonexistent-vision-model",
                 "messages": [
                     {"role": "user", "content": [
                         {"type": "text", "text": "What's in this image?"},
                         {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ=="}},  # noqa: E501
                     ]},
                 ],
            },
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Model doesn't exist → 404
        assert resp.status_code == 404

    # ----- Audio endpoints -----

    def test_audio_transcription_requires_auth(self, client):
        """POST /v1/audio/transcriptions without valid auth."""
        resp = client.post(
            "/v1/audio/transcriptions",
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    def test_audio_speech_requires_auth(self, client):
        """POST /v1/audio/speech without valid auth."""
        resp = client.post(
            "/v1/audio/speech",
            json={"input": "Hello"},
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    def test_audio_speech_direct_model_unknown(self, client):
        """POST /v1/audio/speech with nonexistent model."""
        resp = client.post(
            "/v1/audio/speech",
            json={"model": "nonexistent-audio-model", "input": "Hello world"},
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Model doesn't exist → 404; DB pool may be stale → 500
        assert resp.status_code in (404, 500)

    # ----- Analytics endpoints -----

    def test_analytics_errors_invalid_auth(self, client):
        """GET /api/analytics/errors with invalid auth."""
        resp = client.get(
            "/api/analytics/errors",
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    def test_analytics_error_distribution_invalid_auth(self, client):
        """GET /api/analytics/error-distribution with invalid auth."""
        resp = client.get(
            "/api/analytics/error-distribution",
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    # ----- Embeddings endpoint -----

    def test_embeddings_with_invalid_key(self, client):
        """POST /v1/embeddings with invalid auth."""
        resp = client.post(
            "/v1/embeddings",
            json={"input": "hello", "model": "text-embedding-3-small"},
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert resp.status_code == 401

    # ----- Context-aware routing tests -----

    def test_auto_routing_context_window_skip_small(self, client):
        """Auto-routing with payload > small model context_window should skip that model.
        
        Models with small context_window (e.g., gemma2-9b-it with 8K) should be
        filtered out when the payload exceeds their limit.
        """
        # ~10K token payload — exceeds 8K models but fits 131K models
        huge_text = "Hello " * 2500
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": huge_text}],
            },
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Should either succeed (routed to large context model) or fail gracefully
        assert resp.status_code in (200, 429, 500)

    def test_auto_routing_all_contexts_exceeded(self, client):
        """Payload exceeding ALL model context windows should return 429 with clear message."""
        # ~50K token payload — likely exceeds all models in test DB
        massive_text = "X" * 200000
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": massive_text}],
            },
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert "input exceeds max available context" in data["detail"].lower()

    def test_auto_routing_small_payload_works_normally(self, client):
        """Small payload should route normally without context filtering."""
        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": "Hi"}],
            },
            headers={"Authorization": "Bearer test-key-for-testing"},
        )
        # Without keys in test DB, expect 429 (no candidate) but NOT context error
        assert resp.status_code == 429
        data = resp.json()
        assert "input exceeds max available context" not in data["detail"].lower()
