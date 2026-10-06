"""Punto de entrada para ejecutar el pipeline desde la raíz del proyecto."""

from pipeline.actualizar_datos import update_dataset


if __name__ == "__main__":
    try:
        rows = update_dataset()
        print(f"Datos climáticos actualizados correctamente: {rows} registros")
    except Exception as error:
        print(f"No fue posible actualizar los datos: {error}")
        raise SystemExit(1) from error