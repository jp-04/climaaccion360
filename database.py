"""Conexión SQLite y esquema de usuarios e historial climático."""

import sqlite3
from pathlib import Path

from flask import current_app, g


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


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    path = Path(current_app.config["DATABASE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    get_db().executescript(SCHEMA)
    get_db().commit()


def save_prediction(user_id, result):
    metrics = result["metricas"]
    get_db().execute(
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


def get_recent_predictions(user_id, limit=10):
    return get_db().execute(
        """SELECT modelo, año_objetivo, prediccion, r2, mae, rmse, fecha
           FROM predicciones_usuario
           WHERE usuario_id = ?
           ORDER BY fecha DESC, id DESC
           LIMIT ?""",
        (user_id, limit),
    ).fetchall()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
