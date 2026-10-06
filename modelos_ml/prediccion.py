from __future__ import annotations

import pickle

import pandas as pd

from modelos_ml.entrenamiento import MODELS_PATH, load_training_data, train_models
from modelos_ml.metricas import calcular_metricas


MODEL_FILES = {
    "regresion_lineal": MODELS_PATH / "regresion_lineal.pkl",
    "arbol_decision": MODELS_PATH / "arbol_decision.pkl",
}


def _load_model(model_name: str):
    if model_name not in MODEL_FILES:
        raise ValueError("Modelo no válido. Use regresion_lineal o arbol_decision")
    model_path = MODEL_FILES[model_name]
    if not model_path.exists():
        train_models()
    with model_path.open("rb") as model_file:
        return pickle.load(model_file)


def predecir(year: int, model_name: str) -> dict:
    """Devuelve año, modelo, predicción y métricas del modelo seleccionado."""
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError("El año debe ser un entero")
    model = _load_model(model_name)
    features, target = load_training_data()
    prediction = float(model.predict(pd.DataFrame({"Año": [year]}))[0])
    metrics = calcular_metricas(target, model.predict(features))
    return {"año": year, "modelo": model_name, "prediccion": prediction, "metricas": metrics}