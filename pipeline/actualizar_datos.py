from __future__ import annotations

from pathlib import Path

from pipeline.fuente_climatica import fetch_climate_data
from pipeline.transformacion import save_climate_data, transform_climate_data


DATASET_PATH = Path(__file__).resolve().parent.parent / "datos" / "emisiones_colombia.csv"


def update_dataset() -> int:
    """Ejecuta extracción, transformación y carga; devuelve filas guardadas."""
    extracted_records = fetch_climate_data()
    transformed_data = transform_climate_data(extracted_records)
    save_climate_data(transformed_data, DATASET_PATH)
    return len(transformed_data)


if __name__ == "__main__":
    rows = update_dataset()
    print(f"Datos climáticos actualizados correctamente: {rows} registros")