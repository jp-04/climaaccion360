# ClimaAcción 360

Aplicación Flask sobre emisiones de Colombia, predicciones y clima actual.

## Despliegue en Render

1. Sube el proyecto a un repositorio Git accesible desde Render. Incluye `datos/emisiones_colombia.csv` y los modelos de `modelos_ml/`.
2. En Render, crea un **Web Service** conectado al repositorio y selecciona **Python 3** como lenguaje.
3. Usa `pip install -r requirements.txt` como **Build Command** y `gunicorn app:app` como **Start Command**.
4. En **Environment**, configura `WEATHER_API_KEY` con una clave válida de OpenWeatherMap para que funcione `/api/clima`. Puedes configurar `WEATHER_CITY` (por defecto, `Monteria`) y `WEATHER_COUNTRY_CODE` (por defecto, `CO`). No subas una clave real al repositorio.
5. Despliega y comprueba la ruta `/` y, si configuraste la clave meteorológica, `/api/clima`.

Render toma la versión de Python de `.python-version`. Gunicorn lee `gunicorn.conf.py` desde la raíz y escucha en `0.0.0.0:$PORT`; si `PORT` no está definido, usa `10000`. No hace falta establecer `PORT` manualmente en Render. El `Procfile` contiene el mismo comando de inicio para plataformas que lo usan.

`/api/actualizar-datos` escribe en `datos/emisiones_colombia.csv`. Los cambios locales del sistema de archivos de Render no persisten entre despliegues o reinicios, así que los datos actualizados mediante esa ruta pueden perderse.

## Ejecución local

Con Python 3.12, crea un entorno virtual e instala las dependencias:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python app.py
```

La app de desarrollo estará en `http://127.0.0.1:5000`. Para probar el servidor de producción, ejecuta `gunicorn app:app` en Linux o macOS (Gunicorn no se ejecuta de forma nativa en Windows). Copia los nombres de variables de `.env.example` al entorno si vas a usar el servicio meteorológico; Flask no carga ese archivo automáticamente.
