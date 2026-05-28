import json

from auric.models.provider import ProviderStatus
from auric.services.detector import AutoDetector


class TestAutoDetector:
    def test_detects_claude_when_settings_exist_and_key_in_env(
        self, tmp_path, monkeypatch
    ):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(json.dumps({"theme": "dark"}))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.ACTIVE
        assert result.id == "claude"
        assert result.display_name == "Claude Max"

    def test_not_detected_when_settings_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.NOT_DETECTED

    def test_api_key_from_env(self, tmp_path, monkeypatch):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.ACTIVE

    def test_api_key_from_credentials_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}")
        (claude_dir / ".credentials.json").write_text(
            json.dumps({"claudeAiOauthToken": "oauth-token-abc"})
        )
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.ACTIVE

    def test_not_detected_when_no_key_anywhere(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}")
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.NOT_DETECTED

    def test_malformed_credentials_file_gracefully_falls_through(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{}")
        (claude_dir / ".credentials.json").write_text("not json {{{")
        result = AutoDetector(home_dir=tmp_path).detect_claude()
        assert result.status == ProviderStatus.NOT_DETECTED

    def test_detect_all_returns_list_with_claude(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = AutoDetector(home_dir=tmp_path).detect_all()
        assert isinstance(result, list)
        assert any(p.id == "claude" for p in result)

    def test_resolve_api_key_public_method(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-pub")
        key = AutoDetector(home_dir=tmp_path).resolve_claude_api_key()
        assert key == "sk-ant-pub"

    def test_resolve_api_key_returns_empty_when_nothing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        key = AutoDetector(home_dir=tmp_path).resolve_claude_api_key()
        assert key == ""
