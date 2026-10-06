from __future__ import annotations

from typing import Any

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calcular_metricas(y_real: Any, y_predicho: Any) -> dict[str, float]:
    """Calcula R2, MAE, MSE y RMSE para un modelo regresor."""
    mse = mean_squared_error(y_real, y_predicho)
    return {
        "r2": float(r2_score(y_real, y_predicho)),
        "mae": float(mean_absolute_error(y_real, y_predicho)),
        "mse": float(mse),
        "rmse": float(mse**0.5),
    }