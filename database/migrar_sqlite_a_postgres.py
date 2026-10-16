"""Optional, one-time migration of real SQLite accounts to an empty PostgreSQL DB.

Dry-run by default. Refuses example accounts and never overwrites target rows.
"""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

import psycopg


def read_sqlite(source):
    path = Path(source).resolve()
    if not path.is_file():
        raise ValueError("No existe el archivo SQLite indicado.")
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA query_only = ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("El archivo SQLite no supera integrity_check.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("El archivo SQLite tiene referencias foráneas inválidas.")
        users = db.execute(
            "SELECT id, nombre, correo, password_hash, fecha_registro FROM usuarios ORDER BY id"
        ).fetchall()
        has_history = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'predicciones_usuario'"
        ).fetchone()
        predictions = (
            db.execute(
                """SELECT id, usuario_id, modelo, año_objetivo, prediccion, r2, mae, rmse, fecha
                   FROM predicciones_usuario ORDER BY id"""
            ).fetchall()
            if has_history else []
        )
    return users, predictions


def migrate(url, users, predictions):
    try:
        parsed = urlsplit(url)
        valid_url = (
            parsed.scheme in {"postgres", "postgresql"}
            and parsed.hostname
            and parsed.path.strip("/")
        )
    except (TypeError, ValueError):
        valid_url = False
    if not valid_url:
        raise ValueError("DATABASE_URL debe ser una URL PostgreSQL válida.")
    if any(user[2].lower().endswith("@example.invalid") for user in users):
        raise ValueError("Se detectaron cuentas ficticias; el respaldo de ejemplo no se migra a producción.")

    # One transaction: any failure rolls back all imported accounts and predictions.
    with psycopg.connect(url, connect_timeout=5, autocommit=True) as pg:
        with pg.transaction():
            pg.execute("LOCK TABLE usuarios, predicciones_usuario IN EXCLUSIVE MODE")
            existing = pg.execute(
                "SELECT (SELECT COUNT(*) FROM usuarios), (SELECT COUNT(*) FROM predicciones_usuario)"
            ).fetchone()
            if existing != (0, 0):
                raise ValueError("La base PostgreSQL de destino no está vacía; se canceló sin importar datos.")
            with pg.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO usuarios (id, nombre, correo, password_hash, fecha_registro)
                       VALUES (%s, %s, %s, %s, %s)""",
                    users,
                )
                cursor.executemany(
                    """INSERT INTO predicciones_usuario
                       (id, usuario_id, modelo, año_objetivo, prediccion, r2, mae, rmse, fecha)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    predictions,
                )
            for table in ("usuarios", "predicciones_usuario"):
                pg.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"GREATEST(COALESCE((SELECT MAX(id) FROM {table}), 0), 1), "
                    f"(SELECT COUNT(*) > 0 FROM {table}))"
                )
            copied = pg.execute(
                "SELECT (SELECT COUNT(*) FROM usuarios), (SELECT COUNT(*) FROM predicciones_usuario)"
            ).fetchone()
            if copied != (len(users), len(predictions)):
                raise ValueError("La verificación de cantidades falló; se canceló la transacción.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, help="Ruta del SQLite real de origen")
    parser.add_argument("--apply", action="store_true", help="Importar en PostgreSQL vacío")
    args = parser.parse_args()
    try:
        users, predictions = read_sqlite(args.sqlite)
        print(f"Origen válido: {len(users)} usuarios y {len(predictions)} predicciones.")
        if not args.apply:
            print("Simulación terminada; no se conectó a PostgreSQL ni se modificaron datos.")
            return 0
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError("Configura DATABASE_URL solo en el entorno local para importar.")
        migrate(url, users, predictions)
        print("Migración confirmada y verificada en PostgreSQL.")
        return 0
    except (ValueError, sqlite3.Error, psycopg.Error) as error:
        # Database and connection exceptions can contain connection details: never print them.
        if isinstance(error, ValueError):
            print(f"Migración cancelada: {error}")
        else:
            print("Migración cancelada por un error de base de datos; no se confirmó ningún cambio.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
