"""EXTRACT: read the three Walmart files exactly as downloaded from Kaggle.

Kaggle ships train.csv and features.csv zipped; pandas can read the .zip directly,
so either the .csv or the .csv.zip works.
"""
import io
from pathlib import Path

import pandas as pd

FILES = ["train", "features", "stores"]


def _find(data_dir: Path, name: str) -> Path:
    for candidate in (data_dir / f"{name}.csv", data_dir / f"{name}.csv.zip"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"{name}.csv not found in {data_dir} - see data/README.md")


def _read(path: Path) -> pd.DataFrame:
    if path.suffix == ".zip":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    # Some copies of stores.csv use old Mac line endings (\r only), so normalise them first
    text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)


def extract(data_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in FILES:
        path = _find(Path(data_dir), name)
        frames[name] = _read(path)
        print(f"  {path.name:<18} {len(frames[name]):>8,} rows, {frames[name].shape[1]} columns")
    return frames
