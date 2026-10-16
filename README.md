# ClimaAcción 360

Proyecto universitario de apoyo al **ODS 13: Acción por el clima**. Su objetivo es facilitar la consulta y comprensión de las emisiones de CO₂ per cápita de Colombia, explorar predicciones con modelos de aprendizaje automático y mostrar el clima actual de Montería cuando hay una clave meteorológica configurada.

## Tecnologías y módulos

- Python 3.12, Flask y Jinja2; SQLite local o PostgreSQL 18 para las cuentas y el historial por usuario.
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
| `DATABASE_URL` | URL PostgreSQL. Si está definida, PostgreSQL tiene prioridad y la aplicación no cambia a SQLite ante errores. Sin esta variable se usa SQLite. Configúrala como secreto en Render, nunca en Git. |
| `DATABASE_PATH` | Ruta del archivo SQLite cuando no se configura `DATABASE_URL`. Por defecto: `instance/usuarios.db`. |
| `WEATHER_API_KEY` | Clave de OpenWeatherMap para `/api/clima`. Sin ella el monitor muestra el estado de indisponibilidad. |
| `WEATHER_CITY` | Ciudad meteorológica; por defecto `Monteria`. |
| `WEATHER_COUNTRY_CODE` | País meteorológico; por defecto `CO`. |
| `PORT` | Puerto suministrado por Render. `gunicorn.conf.py` escucha en `0.0.0.0:$PORT` y usa `10000` como valor local por defecto. |

`.env.example` enumera variables de ejemplo, pero Flask no lo carga automáticamente. Nunca publiques claves reales ni bases con usuarios reales.

## Base de datos y entregables

El esquema SQLite implementado está en `database.py` y se reproduce en [database/schema.sql](database/schema.sql); el de PostgreSQL está en [database/schema_postgres.sql](database/schema_postgres.sql). La aplicación crea las tablas e índices de forma idempotente al iniciar. No borra tablas ni filas existentes. El motor se elige exclusivamente con `DATABASE_URL`.

| Tabla | Contenido |
| --- | --- |
| `usuarios` | `id` (PK), `nombre`, `correo` (único sin distinguir mayúsculas), `password_hash`, `fecha_registro`. |
| `predicciones_usuario` | `id` (PK), `usuario_id` (FK), `modelo`, `año_objetivo`, `prediccion`, `r2`, `mae`, `rmse`, `fecha`. |

La relación es **usuarios 1 → 0..N predicciones_usuario**: cada predicción pertenece a un usuario y un usuario puede no tener predicciones o tener muchas. La llave foránea `usuario_id` referencia `usuarios.id` con `ON DELETE CASCADE`. El índice `(usuario_id, fecha DESC, id DESC)` acelera el historial reciente. SQLite guarda fechas como texto UTC; PostgreSQL usa `TIMESTAMPTZ`, claves `BIGINT` y métricas `DOUBLE PRECISION`. En ambos motores el correo es único sin distinguir mayúsculas. Consulta el [diagrama ER](database/diagrama_er.svg).

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
3. Mantén `SECRET_KEY` como secreto en Render. Añade `WEATHER_API_KEY` si necesitas clima en vivo. Conserva la `SECRET_KEY` actual para que las sesiones existentes sigan siendo válidas.
4. En el Web Service, añade la variable de entorno `DATABASE_URL` con el **Internal Database URL** de la base PostgreSQL `climaaccion360-db` en Oregon. Cópialo desde el panel de Render; no lo pegues en archivos, mensajes, commits ni logs. El Web Service y la base deben poder comunicarse por la red interna de Render. No configures `DATABASE_PATH` como sustituto de esta variable.
5. Si hay cuentas reales en SQLite, **antes de activar `DATABASE_URL`** recupera una copia de la base actual y sigue la migración indicada abajo. Si ya se perdió por un reinicio del Web Service Free, este repositorio no puede recuperarla.
6. Despliega cuando la base de destino esté lista. Al iniciar, Flask crea las tablas e índices de PostgreSQL si faltan. Revisa que no haya errores de conexión o esquema en los logs; no se imprime la URL. Prueba `/`, `/registro`, `/login`, `/perfil`, `/dashboard`, `/modelos` y `/api/prediccion`.
7. Registra una cuenta de prueba, inicia sesión, consulta una predicción y verifica el historial en `/perfil`. Reinicia el Web Service y comprueba que cuenta e historial permanecen. Esta comprobación en producción está pendiente; el repositorio no demuestra que la variable haya sido configurada en Render.

Con `DATABASE_URL` configurada, un error de conexión **detiene el inicio o devuelve un error controlado**, sin escribir usuarios en SQLite. Si dejas `DATABASE_URL` sin definir en un Web Service Free, SQLite se almacena en el sistema de archivos efímero y puede perder datos al reiniciar o redesplegar. PostgreSQL Free sí separa los datos del ciclo de vida del Web Service, pero **caduca 30 días después de su creación**; Render indica un plazo de gracia adicional de 14 días y después elimina la base. El plan Free no incluye respaldos administrados. Agenda la exportación manual y una decisión de continuidad antes de esa fecha. Consulta [Render Free](https://render.com/docs/free) y [backups de Render Postgres](https://render.com/docs/postgresql-backups).

### Trasladar cuentas existentes de SQLite

El script [database/migrar_sqlite_a_postgres.py](database/migrar_sqlite_a_postgres.py) conserva IDs, hashes, fechas y predicciones. No importa las cuentas `example.invalid` del respaldo académico. Solo acepta un destino PostgreSQL **vacío**; una transacción revierte la importación si ocurre un error. No intenta fusionar cuentas ni sobrescribe filas.

1. Obtén una copia íntegra del archivo SQLite real y mantenla fuera del repositorio. Si está en el disco efímero del Web Service, recupérala **antes** de reiniciar o redesplegar. Detén escrituras de registro/predicción durante el corte y mantén esa pausa hasta activar PostgreSQL.
2. Haz un respaldo previo de PostgreSQL. Inicializa las tablas con `psql --file=database/schema_postgres.sql` en la base vacía, usando las variables estándar de conexión de PostgreSQL indicadas abajo, o con el primer arranque de esta versión de la aplicación.
3. En una estación segura, configura `DATABASE_URL` temporalmente con el **External Database URL** de Render, sin guardarlo en el repositorio ni pasarlo como argumento de línea de comandos. Ejecuta primero la simulación: `python database/migrar_sqlite_a_postgres.py --sqlite RUTA_AL_SQLITE_REAL`. Comprueba las cantidades.
4. Ejecuta `python database/migrar_sqlite_a_postgres.py --sqlite RUTA_AL_SQLITE_REAL --apply`. El script aborta si PostgreSQL ya contiene usuarios o predicciones. Comprueba las cantidades en PostgreSQL, el acceso de una cuenta existente y su historial antes de retirar SQLite.
5. Configura el **Internal Database URL** en el Web Service y redespliega. Usa la misma base PostgreSQL a la que importaste los datos. Conserva el respaldo SQLite hasta completar la verificación tras el reinicio.

Para una instalación nueva sin cuentas existentes, omite la importación. Crear `DATABASE_URL` **no** traslada automáticamente los datos de SQLite.

### Respaldo manual y recuperación

Desde una estación con `pg_dump` y `pg_restore` de PostgreSQL 18, configura `PGHOST`, `PGPORT`, `PGUSER` y `PGDATABASE` según el **External Database URL** de Render. Guarda la contraseña en un archivo privado indicado por `PGPASSFILE` (formato `.pgpass`), fuera del repositorio. Así no aparece en los argumentos del proceso. Define `BACKUP_FILE` con una ruta **fuera del repositorio**:

```bash
pg_dump --format=custom --file="$BACKUP_FILE"
pg_restore --list "$BACKUP_FILE"
```

No escribas la URL con contraseña en el historial de la terminal. Protege el archivo de respaldo: puede contener correos y hashes. Para restaurar, prepara una **base de destino vacía**, valida el archivo y ejecuta `pg_restore --dbname="$PGDATABASE" --no-owner --no-privileges --single-transaction "$BACKUP_FILE"`; después comprueba tablas, cantidades y autenticación. No restaures encima de una base con usuarios sin un procedimiento específico de conciliación.

### Regreso ante un despliegue fallido

Conserva el commit anterior y el respaldo previo. Si falla el nuevo código, vuelve a desplegar el commit anterior desde Render. **El código anterior usa SQLite y no entiende `DATABASE_URL`**: evita permitir registros o predicciones durante ese regreso, porque crearían datos separados en SQLite. Si PostgreSQL ya recibió datos reales, la solución segura es corregir el despliegue de esta versión o restaurar la base desde un respaldo verificado antes de reabrir escrituras. No cambies silenciosamente de motor ni borres `DATABASE_URL` con tráfico activo.

`/api/actualizar-datos` escribe en `datos/emisiones_colombia.csv`. Los cambios hechos a ese archivo durante la ejecución también son efímeros en Render si la ruta no está en almacenamiento persistente; el CSV versionado vuelve a estar disponible con cada despliegue.

## Pruebas

Con las dependencias instaladas:

```powershell
$env:SECRET_KEY = 'clave-local-exclusiva-para-pruebas'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas cubren registro y validaciones, hash de contraseña, login, logout, perfil protegido, separación del historial entre usuarios, predicciones con y sin sesión, migración de una base anterior, rutas/API existentes, selección de motor y manejo de fallos. La selección PostgreSQL se prueba con dobles de prueba; **todavía hay que verificarla contra la base real de Render**. En Linux o macOS, usa `SECRET_KEY=clave-local-exclusiva-para-pruebas python -m unittest discover -s tests -v`.
