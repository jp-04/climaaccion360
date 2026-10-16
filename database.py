"""Acceso a usuarios e historial en SQLite local o PostgreSQL."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


DATABASE_ERRORS = (sqlite3.Error, psycopg.Error)
INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)
POSTGRES_SCHEMA_PATH = Path(__file__).with_name("database") / "schema_postgres.sql"


class DatabaseConfigurationError(RuntimeError):
    """The configured database URL cannot be used."""


class DatabaseConnectionError(RuntimeError):
    """The configured PostgreSQL database is unavailable."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    fecha_registro TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS predicciones_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    modelo TEXT NOT NULL,
    año_objetivo INTEGER NOT NULL,
    prediccion REAL NOT NULL,
    r2 REAL NOT NULL,
    mae REAL NOT NULL,
    rmse REAL NOT NULL,
    fecha TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_predicciones_usuario_fecha
    ON predicciones_usuario (usuario_id, fecha DESC, id DESC);
"""


def is_postgres():
    return current_app.config.get("DATABASE_URL") is not None


def get_db():
    if "db" not in g:
        if is_postgres():
            url = current_app.config["DATABASE_URL"]
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/"):
                    raise ValueError("Invalid PostgreSQL URL")
            except (TypeError, ValueError):
                raise DatabaseConfigurationError("DATABASE_URL debe ser una URL PostgreSQL válida.") from None
            try:
                g.db = psycopg.connect(url, row_factory=dict_row, connect_timeout=5)
            except (psycopg.Error, ValueError):
                raise DatabaseConnectionError(
                    "No fue posible conectar a PostgreSQL. Revisa DATABASE_URL y la disponibilidad de la base."
                ) from None
        else:
            g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def execute(statement, parameters=()):
    """Execute an application-owned parameterized statement on either engine."""
    if is_postgres():
        statement = statement.replace("?", "%s")
    return get_db().execute(statement, parameters)


def template_row(row):
    """Keep the existing templates' ISO text dates on both engines."""
    if row is None:
        return None
    values = dict(row)
    for key, value in values.items():
        if isinstance(value, datetime):
            values[key] = value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return values


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    if is_postgres():
        db = get_db()
        statements = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8").split(";")
        try:
            for statement in statements:
                if statement.strip():
                    db.execute(statement)
            db.commit()
        except psycopg.Error:
            db.rollback()
            raise DatabaseConnectionError("No fue posible inicializar el esquema PostgreSQL.") from None
    else:
        path = Path(current_app.config["DATABASE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        get_db().executescript(SCHEMA)
        get_db().commit()


def save_prediction(user_id, result):
    metrics = result["metricas"]
    try:
        execute(
            """INSERT INTO predicciones_usuario
               (usuario_id, modelo, año_objetivo, prediccion, r2, mae, rmse)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                result["modelo"],
                result["año"],
                result["prediccion"],
                metrics["r2"],
                metrics["mae"],
                metrics["rmse"],
            ),
        )
        get_db().commit()
    except DATABASE_ERRORS:
        get_db().rollback()
        raise


def get_recent_predictions(user_id, limit=10):
    rows = execute(
        """SELECT modelo, año_objetivo, prediccion, r2, mae, rmse, fecha
           FROM predicciones_usuario
           WHERE usuario_id = ?
           ORDER BY fecha DESC, id DESC
           LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [template_row(row) for row in rows]


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
