# ClimaAcción 360

Aplicación Flask sobre emisiones de Colombia, predicciones y clima actual.

## Despliegue en Render

1. Sube el proyecto a un repositorio Git accesible desde Render. Incluye `datos/emisiones_colombia.csv` y los modelos de `modelos_ml/`.
2. En Render, crea un **Web Service** conectado al repositorio y selecciona **Python 3** como lenguaje.
3. Usa `pip install -r requirements.txt` como **Build Command** y `gunicorn app:app` como **Start Command**.
4. En **Environment**, configura `SECRET_KEY` con una cadena aleatoria y privada de al menos 32 bytes. Puedes generarla localmente con `python -c "import secrets; print(secrets.token_hex(32))"`. La app no inicia sin esta variable. Configura también `WEATHER_API_KEY` con una clave válida de OpenWeatherMap para que funcione `/api/clima`. Puedes configurar `WEATHER_CITY` (por defecto, `Monteria`) y `WEATHER_COUNTRY_CODE` (por defecto, `CO`). No subas claves reales al repositorio.
5. Para conservar las cuentas en Render, usa un servicio que permita **Persistent Disk**, monta el disco en `/var/data` y configura `DATABASE_PATH=/var/data/usuarios.db`. Sin disco persistente, la base SQLite se pierde al reiniciar o volver a desplegar. Los servicios gratuitos de Render no admiten discos persistentes.
6. Despliega y comprueba `/`, `/registro`, `/login` y, si configuraste la clave meteorológica, `/api/clima`.

Render toma la versión de Python de `.python-version`. Gunicorn lee `gunicorn.conf.py` desde la raíz y escucha en `0.0.0.0:$PORT`; si `PORT` no está definido, usa `10000`. No hace falta establecer `PORT` manualmente en Render. El `Procfile` contiene el mismo comando de inicio para plataformas que lo usan.

`/api/actualizar-datos` escribe en `datos/emisiones_colombia.csv`. Los cambios locales del sistema de archivos de Render no persisten entre despliegues o reinicios, así que los datos actualizados mediante esa ruta pueden perderse.

## Usuarios

La primera vez que inicia, la app crea `instance/usuarios.db` y las tablas `usuarios` y `predicciones_usuario`, salvo que configures `DATABASE_PATH`. También crea la tabla de historial al iniciar con una base de usuarios existente. El registro guarda un hash de la contraseña y exige nombre, correo válido, contraseña de al menos ocho caracteres y confirmación. Tras crear una cuenta, inicia sesión en `/login` para acceder a `/perfil`; `/logout` cierra la sesión. Cada consulta válida a `/api/prediccion` hecha con sesión guarda su resultado y métricas; el perfil muestra las diez más recientes del usuario. Las consultas sin sesión siguen funcionando, sin guardarse. La base y los archivos `.env` están excluidos de Git.

## Ejecución local

Con Python 3.12, crea un entorno virtual, instala las dependencias y configura una clave local. En PowerShell:

```powershell
python -m venv .venv
python -m pip install -r requirements.txt
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
python app.py
```

En Bash, asigna la clave con `export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")`. La app de desarrollo estará en `http://127.0.0.1:5000`. Para probar el servidor de producción, ejecuta `gunicorn app:app` en Linux o macOS (Gunicorn no se ejecuta de forma nativa en Windows). `.env.example` solo muestra los nombres de las variables; Flask no carga ese archivo automáticamente.
