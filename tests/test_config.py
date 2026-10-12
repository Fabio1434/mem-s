from gnn_sdn_apt.config import load_config


def test_missing_config_uses_safe_defaults(tmp_path):
    config = load_config(tmp_path / "missing.yaml")
    assert config["mitigation"]["enabled"] is False
    assert config["detection"]["model"] == "baseline"
    assert config["graph"]["temporal_window_seconds"] == 10
