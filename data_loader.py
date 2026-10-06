from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).parent / "datos" / "emisiones_colombia.csv"
REQUIRED_COLUMNS = ("Año", "Indicador", "Valor", "Pais")


class DataValidationError(ValueError):
    """Indica que un archivo climático no cumple el contrato esperado."""


def load_emissions_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Carga y valida la serie de emisiones desde un CSV local."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de datos: {path}")

    frame = pd.read_csv(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise DataValidationError(f"Faltan columnas requeridas: {missing}")

    frame = frame.loc[:, REQUIRED_COLUMNS].copy()
    frame["Año"] = pd.to_numeric(frame["Año"], errors="coerce")
    frame["Valor"] = pd.to_numeric(frame["Valor"], errors="coerce")

    invalid_rows = frame[frame[["Año", "Valor"]].isna().any(axis=1)]
    if not invalid_rows.empty:
        raise DataValidationError("Año y Valor deben ser numéricos en todas las filas con datos")

    frame["Año"] = frame["Año"].astype(int)
    frame["Valor"] = frame["Valor"].astype(float)
    return frame.sort_values("Año").reset_index(drop=True)


def summarize_emissions(frame: pd.DataFrame) -> dict:
    """Calcula indicadores descriptivos sin crear valores cuando no hay datos."""
    if frame.empty:
        return {
            "initial_value": None,
            "latest_value": None,
            "latest_year": None,
            "variation_percent": None,
            "maximum_value": None,
            "minimum_value": None,
            "historical_average": None,
        }

    ordered = frame.sort_values("Año").reset_index(drop=True)
    initial_value = float(ordered.iloc[0]["Valor"])
    latest_value = float(ordered.iloc[-1]["Valor"])
    variation_percent = None
    if initial_value != 0:
        variation_percent = ((latest_value - initial_value) / abs(initial_value)) * 100

    return {
        "initial_value": initial_value,
        "latest_value": latest_value,
        "latest_year": int(ordered.iloc[-1]["Año"]),
        "variation_percent": variation_percent,
        "maximum_value": float(ordered["Valor"].max()),
        "minimum_value": float(ordered["Valor"].min()),
        "historical_average": float(ordered["Valor"].mean()),
    }


def prepare_for_visualization(frame: pd.DataFrame) -> list[dict]:
    """Convierte el DataFrame validado a registros serializables para el frontend."""
    records = frame.to_dict(orient="records")
    return [
        {
            "Año": int(record["Año"]),
            "Indicador": record["Indicador"],
            "Valor": float(record["Valor"]),
            "Pais": record["Pais"],
        }
        for record in records
    ]