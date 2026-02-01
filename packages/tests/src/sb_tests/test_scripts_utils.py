"""Tests for utility script functions."""


class TestScriptUtils:
    """Test suite for script utilities."""

    def test_get_aws_region_default(self):
        """Test getting default AWS region."""
        from scripts.utils import get_aws_region

        region = get_aws_region()
        assert region == "us-west-2"

    def test_get_aws_region_from_env(self, monkeypatch):
        """Test getting AWS region from environment."""
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        from scripts.utils import get_aws_region

        region = get_aws_region()
        assert region == "eu-west-1"

    def test_get_environment_default(self):
        """Test getting default environment."""
        from scripts.utils import get_environment

        env = get_environment()
        assert env == "dev"

    def test_get_environment_from_env(self, monkeypatch):
        """Test getting environment from environment variable."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        from scripts.utils import get_environment

        env = get_environment()
        assert env == "production"
