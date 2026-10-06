from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor

from data_loader import DATA_PATH, REQUIRED_COLUMNS
from modelos_ml.metricas import calcular_metricas


MODELS_PATH = Path(__file__).resolve().parent
LINEAR_MODEL_PATH = MODELS_PATH / "regresion_lineal.pkl"
TREE_MODEL_PATH = MODELS_PATH / "arbol_decision.pkl"


def load_training_data(path: Path = DATA_PATH) -> tuple[pd.DataFrame, pd.Series]:
    """Carga Año como variable independiente y Valor como objetivo."""
    frame = pd.read_csv(path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing_columns)}")

    frame["Año"] = pd.to_numeric(frame["Año"], errors="coerce")
    frame["Valor"] = pd.to_numeric(frame["Valor"], errors="coerce")
    frame = frame.dropna(subset=["Año", "Valor"]).sort_values("Año")
    if len(frame) < 2:
        raise ValueError("Se requieren al menos dos registros válidos para entrenar")
    return frame[["Año"]].astype(int), frame["Valor"].astype(float)


def _temporal_split(features: pd.DataFrame, target: pd.Series) -> tuple:
    """Reserva el tramo final de la serie para evaluar sin mezclar el futuro."""
    split_index = max(1, int(len(features) * 0.8))
    if split_index == len(features):
        split_index -= 1
    return features.iloc[:split_index], features.iloc[split_index:], target.iloc[:split_index], target.iloc[split_index:]


def train_models() -> dict[str, dict[str, float]]:
    """Entrena, evalúa y persiste ambos estimadores."""
    features, target = load_training_data()
    x_train, x_test, y_train, y_test = _temporal_split(features, target)
    models = {
        "regresion_lineal": LinearRegression(),
        "arbol_decision": DecisionTreeRegressor(max_depth=4, random_state=42),
    }
    metrics = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        metrics[name] = calcular_metricas(y_test, model.predict(x_test))
        with (MODELS_PATH / f"{name}.pkl").open("wb") as model_file:
            pickle.dump(model, model_file)
    return metrics


if __name__ == "__main__":
    print(train_models())