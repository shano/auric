import tomllib

from auric.config.manager import ConfigManager
from auric.models.config import AppConfig


class TestConfigManager:
    def test_creates_default_config_when_absent(self, tmp_path):
        mgr = ConfigManager(config_path=tmp_path / "config.toml")
        config = mgr.load()
        assert isinstance(config, AppConfig)
        assert "claude" in config.providers
        assert config.providers["claude"].ping_interval_s == 300
        assert config.providers["claude"].poll_interval_s == 30
        assert config.providers["claude"].enabled is True

    def test_writes_default_config_to_disk(self, tmp_path):
        config_path = tmp_path / "config.toml"
        mgr = ConfigManager(config_path=config_path)
        mgr.load()
        assert config_path.exists()
        raw = tomllib.loads(config_path.read_text())
        assert "claude" in raw

    def test_reads_existing_config(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            "[claude]\n"
            'api_key = "sk-ant-test"\n'
            "ping_interval = 60\n"
            "poll_interval = 10\n"
            "enabled = true\n"
        )
        mgr = ConfigManager(config_path=config_path)
        config = mgr.load()
        assert config.providers["claude"].api_key == "sk-ant-test"
        assert config.providers["claude"].ping_interval_s == 60
        assert config.providers["claude"].poll_interval_s == 10

    def test_missing_keys_use_defaults(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("[claude]\nenabled = false\n")
        mgr = ConfigManager(config_path=config_path)
        config = mgr.load()
        assert config.providers["claude"].enabled is False
        assert config.providers["claude"].ping_interval_s == 300

    def test_creates_parent_dirs_if_absent(self, tmp_path):
        config_path = tmp_path / "nested" / "dir" / "config.toml"
        mgr = ConfigManager(config_path=config_path)
        mgr.load()
        assert config_path.exists()

    def test_api_key_empty_by_default(self, tmp_path):
        mgr = ConfigManager(config_path=tmp_path / "config.toml")
        config = mgr.load()
        assert config.providers["claude"].api_key == ""
