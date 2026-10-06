"""Cliente pequeño y aislado para consultar el clima actual."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherServiceError(RuntimeError):
    """Error controlado al consultar o interpretar el servicio meteorológico."""


def get_current_weather(timeout: int = 10) -> dict[str, str | float]:
    """Devuelve clima actual normalizado para el monitor de la portada."""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise WeatherServiceError("Falta configurar la variable WEATHER_API_KEY")

    city = os.getenv("WEATHER_CITY", "Monteria")
    country_code = os.getenv("WEATHER_COUNTRY_CODE", "CO")
    query = urlencode(
        {
            "q": f"{city},{country_code}",
            "appid": api_key,
            "units": "metric",
            "lang": "es",
        }
    )
    request = Request(
        f"{OPENWEATHER_URL}?{query}",
        headers={"User-Agent": "ClimaAccion360/1.0"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise WeatherServiceError("No fue posible consultar el servicio meteorológico") from error

    try:
        return {
            "ciudad": payload["name"],
            "temperatura": float(payload["main"]["temp"]),
            "humedad": int(payload["main"]["humidity"]),
            "condicion": payload["weather"][0]["description"].capitalize(),
            "viento": float(payload.get("wind", {}).get("speed", 0)),
        }
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise WeatherServiceError("La respuesta meteorológica no tiene el formato esperado") from error