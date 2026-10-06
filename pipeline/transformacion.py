from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ("Año", "Indicador", "Valor", "Pais")


class TransformationError(ValueError):
    """Indica que los datos extraídos no cumplen el contrato del dataset."""


def transform_climate_data(records: list[dict]) -> pd.DataFrame:
    """Valida, limpia y ordena registros para el CSV consumido por Flask."""
    frame = pd.DataFrame(records)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise TransformationError(f"Faltan columnas requeridas: {missing}")

    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    frame["Año"] = pd.to_numeric(frame["Año"], errors="coerce")
    frame["Valor"] = pd.to_numeric(frame["Valor"], errors="coerce")
    frame["Indicador"] = frame["Indicador"].astype("string").str.strip()
    frame["Pais"] = frame["Pais"].astype("string").str.strip()

    valid = (
        frame["Año"].notna()
        & frame["Valor"].notna()
        & frame["Indicador"].notna()
        & frame["Pais"].notna()
        & frame["Indicador"].ne("")
        & frame["Pais"].ne("")
    )
    frame = frame.loc[valid].copy()
    if frame.empty:
        raise TransformationError("La fuente no contiene registros climáticos válidos")

    frame["Año"] = frame["Año"].astype(int)
    frame["Valor"] = frame["Valor"].astype(float)
    return frame.sort_values("Año").reset_index(drop=True)


def save_climate_data(frame: pd.DataFrame, destination: Path) -> None:
    """Guarda el dataset de forma atómica para proteger el archivo del dashboard."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")
    frame.loc[:, REQUIRED_COLUMNS].to_csv(temporary_path, index=False, encoding="utf-8")
    temporary_path.replace(destination)