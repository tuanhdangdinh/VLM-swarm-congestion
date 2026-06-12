from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODELS_CONFIG = ROOT / "config" / "models.yaml"


def test_llama_paths_are_home_relative_and_vision_is_configured():
    raw = yaml.safe_load(MODELS_CONFIG.read_text(encoding="utf-8"))
    config = raw["vlm"]["llama_server"]

    assert config["base_url"] == "http://127.0.0.1:8080/v1"
    assert config["model_id"] == "cosmos-reason2-8b"
    assert config["model_path"].startswith("$HOME/")
    assert config["mmproj_path"].startswith("$HOME/")
    assert "tuanhdangdinh" not in config["model_path"]
    assert "tuanhdangdinh" not in config["mmproj_path"]
