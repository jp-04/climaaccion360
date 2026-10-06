from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


INDICATOR = "EN.GHG.CO2.PC.CE.AR5"
COUNTRY_CODE = "COL"
COUNTRY_NAME = "Colombia"
WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/"
    f"{COUNTRY_CODE}/indicator/{INDICATOR}"
)


class ClimateSourceError(RuntimeError):
    """Indica un error de conexión o de estructura en la fuente externa."""


def fetch_climate_data(timeout: int = 30) -> list[dict[str, Any]]:
    """Extrae los registros del indicador desde la API oficial del Banco Mundial."""
    query = urlencode({"format": "json", "per_page": 100})
    request = Request(f"{WORLD_BANK_URL}?{query}", headers={"User-Agent": "ClimaAccion360/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise ClimateSourceError("No fue posible consultar la fuente climática oficial") from error

    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ClimateSourceError("La fuente climática devolvió una respuesta inesperada")

    records = []
    for item in payload[1]:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "Año": item.get("date"),
                "Indicador": item.get("indicator", {}).get("id", INDICATOR),
                "Valor": item.get("value"),
                "Pais": item.get("country", {}).get("value", COUNTRY_NAME),
            }
        )

    return records