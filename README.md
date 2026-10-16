# ClimaAcción 360

Proyecto universitario de apoyo al **ODS 13: Acción por el clima**. Su objetivo es facilitar la consulta y comprensión de las emisiones de CO₂ per cápita de Colombia, explorar predicciones con modelos de aprendizaje automático y mostrar el clima actual de Montería cuando hay una clave meteorológica configurada.

## Tecnologías y módulos

- Python 3.12, Flask, Jinja2 y SQLite para la aplicación, las cuentas y el historial por usuario.
- Pandas y scikit-learn para preparar la serie de emisiones y consultar los modelos entrenados.
- Plotly en el navegador para las visualizaciones del dashboard y de las predicciones.
- Gunicorn para servir la aplicación en Render.
- CSV del Banco Mundial en `datos/emisiones_colombia.csv`; OpenWeatherMap para `/api/clima`.

La aplicación ofrece `/`, `/ods13`, `/dashboard`, `/modelos`, `/acciones`, `/registro`, `/login`, `/logout` y `/perfil`. El perfil requiere sesión. La API de predicción sigue disponible para visitantes; solo las consultas autenticadas se guardan en el historial.

## Instalación local

Clona el repositorio y, desde su raíz, crea un entorno con Python 3.12. En PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\.venv\Scripts\python.exe app.py
```

En Linux o macOS:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py
```

Abre `http://127.0.0.1:5000`. En desarrollo, la base se crea automáticamente en `instance/usuarios.db` si no defines `DATABASE_PATH`. No subas esa base ni archivos `.env` a Git. Gunicorn se usa en Linux/macOS; no se ejecuta de forma nativa en Windows.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `SECRET_KEY` | **Obligatoria.** Clave privada y aleatoria para las sesiones Flask. La aplicación no inicia sin ella. |
| `DATABASE_PATH` | Ruta del archivo SQLite. Por defecto: `instance/usuarios.db`. En Render debe apuntar a un disco persistente para conservar usuarios e historial. |
| `WEATHER_API_KEY` | Clave de OpenWeatherMap para `/api/clima`. Sin ella el monitor muestra el estado de indisponibilidad. |
| `WEATHER_CITY` | Ciudad meteorológica; por defecto `Monteria`. |
| `WEATHER_COUNTRY_CODE` | País meteorológico; por defecto `CO`. |
| `PORT` | Puerto suministrado por Render. `gunicorn.conf.py` escucha en `0.0.0.0:$PORT` y usa `10000` como valor local por defecto. |

`.env.example` enumera variables de ejemplo, pero Flask no lo carga automáticamente. Nunca publiques claves reales ni bases con usuarios reales.

## Base de datos y entregables

El esquema implementado está en `database.py` y se reproduce en [database/schema.sql](database/schema.sql). La aplicación crea las tablas al iniciar, incluida la tabla de historial si ya existía una base de usuarios anterior.

| Tabla | Contenido |
| --- | --- |
| `usuarios` | `id` (PK), `nombre`, `correo` (único sin distinguir mayúsculas), `password_hash`, `fecha_registro`. |
| `predicciones_usuario` | `id` (PK), `usuario_id` (FK), `modelo`, `año_objetivo`, `prediccion`, `r2`, `mae`, `rmse`, `fecha`. |

La relación es **usuarios 1 → 0..N predicciones_usuario**: cada predicción pertenece a un usuario y un usuario puede no tener predicciones o tener muchas. La llave foránea `usuario_id` referencia `usuarios.id` con `ON DELETE CASCADE`. El índice `(usuario_id, fecha DESC, id DESC)` acelera el historial reciente. Las fechas se guardan como texto UTC de SQLite. Consulta el [diagrama ER](database/diagrama_er.svg).

El [respaldo lógico de ejemplo](database/respaldo_ejemplo.sql) contiene solo dos cuentas ficticias `example.invalid` y tres predicciones inventadas para demostrar la relación. Las contraseñas originales de esas cuentas son aleatorias y no se conservan; el archivo incluye únicamente sus hashes. **No es un respaldo de producción ni se debe restaurar sobre una base real.**

### Restaurar el respaldo de ejemplo

Restaura en un archivo **nuevo** desde la raíz del proyecto. El comando falla si ese archivo ya existe:

```powershell
python -c "import sqlite3; from pathlib import Path; p=Path('instance/usuarios_demo.db'); assert not p.exists(), 'El destino ya existe'; p.parent.mkdir(parents=True, exist_ok=True); db=sqlite3.connect(p); db.executescript(Path('database/respaldo_ejemplo.sql').read_text(encoding='utf-8')); db.close()"
```

Luego configura `DATABASE_PATH` con la ruta de `instance/usuarios_demo.db` antes de iniciar la aplicación. El mismo comando funciona en Bash. Para datos reales, conserva una copia de seguridad fuera del repositorio y restaura únicamente en una ruta controlada.

## Despliegue en Render y persistencia

1. Conecta el repositorio a un **Web Service** Python y usa la versión de `.python-version`.
2. Configura **Build Command**: `pip install -r requirements.txt` y **Start Command**: `gunicorn app:app`. `Procfile` declara el mismo inicio y `gunicorn.conf.py` usa el puerto de Render.
3. Configura `SECRET_KEY` como secreto en Render; añade `WEATHER_API_KEY` si necesitas clima en vivo.
4. **Para persistir SQLite**, el servicio debe admitir un **Persistent Disk**. Monta el disco en `/var/data` y define `DATABASE_PATH=/var/data/usuarios.db`. La aplicación ya acepta esta ruta y crea las tablas allí al iniciar. Comprueba en el panel de Render el plan, el disco montado y el valor efectivo de la variable; este repositorio no demuestra que estén configurados.
5. Comprueba `/`, `/registro`, `/login`, `/perfil`, `/dashboard` y `/modelos`. Para verificar persistencia, registra una cuenta de prueba, crea una predicción, reinicia o redespliega y confirma que la cuenta y su historial siguen presentes. Hazlo solo después de tener el almacenamiento persistente configurado.

**Estado de la persistencia remota en esta entrega:** el servicio desplegado usa el plan **Free**, según confirmó el responsable del proyecto. Render no permite añadirle un disco persistente y su sistema de archivos local es efímero. Por tanto, las cuentas y predicciones guardadas en SQLite **pueden perderse** cuando el servicio se suspende, reinicia o redespliega. La ruta `DATABASE_PATH` ya está preparada en el código, pero garantizar persistencia requiere pasar el servicio a un plan que admita Persistent Disk, montar `/var/data` y configurar la variable, o contratar y configurar una base relacional externa permitida por la guía. No se ha realizado ninguna de esas acciones. Antes de cambiar el almacenamiento de un servicio con usuarios reales, respalda y migra sus datos; cambiar la ruta no los traslada automáticamente. Consulta la [documentación de discos](https://render.com/docs/disks) y las [limitaciones del plan gratuito](https://render.com/docs/free).

`/api/actualizar-datos` escribe en `datos/emisiones_colombia.csv`. Los cambios hechos a ese archivo durante la ejecución también son efímeros en Render si la ruta no está en almacenamiento persistente; el CSV versionado vuelve a estar disponible con cada despliegue.

## Pruebas

Con las dependencias instaladas:

```powershell
$env:SECRET_KEY = 'clave-local-exclusiva-para-pruebas'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas cubren registro y validaciones, hash de contraseña, login, logout, perfil protegido, separación del historial entre usuarios, predicciones con y sin sesión, migración de una base anterior y rutas/API existentes. En Linux o macOS, usa `SECRET_KEY=clave-local-exclusiva-para-pruebas python -m unittest discover -s tests -v`.
