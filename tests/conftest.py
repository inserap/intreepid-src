from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"
SEED_PARQUET = FIXTURES / "accidents_seed.parquet"
GROUND_TRUTH = FIXTURES / "ground_truth.yaml"
FICHE = FIXTURES / "accidents.fiche.yaml"
