"""Tests for Bedrock application module."""

import pytest


class TestBedrockApp:
    """Test suite for BedrockApp."""

    def test_app_initialization(self):
        """Test that BedrockApp initializes correctly."""
        from bedrock.app import BedrockApp

        app = BedrockApp()
        assert app is not None
        assert app.region == "us-east-1"
        assert "claude" in app.model_id.lower()

    def test_model_id_from_env(self, monkeypatch):
        """Test that model ID can be set from environment."""
        monkeypatch.setenv("AWS_BEDROCK_MODEL_ID", "custom-model-id")
        from bedrock.app import BedrockApp

        app = BedrockApp()
        assert app.model_id == "custom-model-id"
