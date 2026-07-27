from pathlib import Path
import yaml

def load_fiche(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def list_datasets(fiche: dict) -> list[str]:
    return [fiche["dataset"]]

def describe(fiche: dict) -> dict:
    return fiche
