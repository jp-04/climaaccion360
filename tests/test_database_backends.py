"""Backend selection and failure handling without contacting a real database."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg

os.environ.setdefault("SECRET_KEY", "clave-exclusiva-para-pruebas-que-no-se-usa-en-produccion")
os.environ.pop("DATABASE_URL", None)
_bootstrap_dir = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = str(Path(_bootstrap_dir.name) / "bootstrap.db")

from app import app
from database import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    execute,
    get_db,
    init_db,
    save_prediction,
    template_row,
)


class DatabaseBackendsTestCase(unittest.TestCase):
    def setUp(self):
        self.original_url = app.config["DATABASE_URL"]
        self.addCleanup(app.config.__setitem__, "DATABASE_URL", self.original_url)
        app.config["DATABASE_URL"] = "postgresql://usuario:secreto@localhost:5432/climaaccion"

    def test_postgres_url_selects_psycopg_and_initializes_idempotently(self):
        with patch("database.psycopg.connect") as connect:
            connection = connect.return_value
            with app.app_context():
                init_db()
                execute("SELECT id FROM usuarios WHERE id = ?", (7,))
                self.assertIs(get_db(), connection)
            connect.assert_called_once()
            self.assertEqual(connect.call_args.kwargs["connect_timeout"], 5)
            self.assertEqual(connection.execute.call_count, 5)  # four DDL statements and one query
            connection.execute.assert_any_call("SELECT id FROM usuarios WHERE id = %s", (7,))
            connection.commit.assert_called_once()
            connection.close.assert_called_once()

    def test_invalid_url_never_falls_back_to_sqlite(self):
        app.config["DATABASE_URL"] = "sqlite:///no-es-postgres.db"
        with patch("database.sqlite3.connect") as sqlite_connect, patch("database.psycopg.connect") as pg_connect:
            with app.app_context():
                with self.assertRaises(DatabaseConfigurationError):
                    get_db()
        sqlite_connect.assert_not_called()
        pg_connect.assert_not_called()

    def test_connection_failure_is_sanitized_and_does_not_fall_back(self):
        with patch("database.sqlite3.connect") as sqlite_connect, patch(
            "database.psycopg.connect", side_effect=psycopg.OperationalError("secreto: conexión fallida")
        ):
            with app.app_context():
                with self.assertRaises(DatabaseConnectionError) as raised:
                    get_db()
        self.assertNotIn("secreto", str(raised.exception))
        sqlite_connect.assert_not_called()

    def test_request_returns_controlled_error_when_postgres_is_unavailable(self):
        with patch(
            "database.psycopg.connect",
            side_effect=psycopg.OperationalError("secreto: conexión fallida"),
        ):
            response = app.test_client().post(
                "/registro",
                data={
                    "nombre": "Persona",
                    "correo": "persona@example.com",
                    "contrasena": "clave-segura-123",
                    "confirmacion": "clave-segura-123",
                },
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secreto", response.get_data(as_text=True))

    def test_prediction_write_rolls_back_on_postgres_error(self):
        result = {
            "modelo": "regresion_lineal", "año": 2030, "prediccion": 1.5,
            "metricas": {"r2": 0.8, "mae": 0.1, "rmse": 0.2},
        }
        with patch("database.psycopg.connect") as connect:
            connection = connect.return_value
            connection.execute.side_effect = psycopg.IntegrityError("fallo controlado")
            with app.app_context():
                with self.assertRaises(psycopg.IntegrityError):
                    save_prediction(1, result)
            connection.rollback.assert_called_once()
            connection.commit.assert_not_called()

    def test_postgres_timestamp_is_text_for_existing_templates(self):
        timestamp = datetime(2026, 10, 16, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
        self.assertEqual(template_row({"fecha": timestamp})["fecha"], "2026-10-16T14:30:00.000Z")


def tearDownModule():
    _bootstrap_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
