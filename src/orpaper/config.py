from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "project.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def search_string(cfg: dict) -> str:
    """Compose the Boolean search string recorded in the methodology section."""
    s = cfg["search"]
    parts = [s["mandatory"], s["topic_terms"], s["method_terms"]]
    return " AND ".join(p for p in parts if p and not p.startswith("TODO"))
