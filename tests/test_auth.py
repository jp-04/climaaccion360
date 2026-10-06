"""Flujos de autenticación y regresión de rutas públicas."""

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "clave-exclusiva-para-pruebas-que-no-se-usa-en-produccion")

from app import app  # noqa: E402
from database import get_db, init_db  # noqa: E402


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        app.config.update(TESTING=True, DATABASE=str(Path(self.temp_dir.name) / "usuarios.db"))
        with app.app_context():
            init_db()
        self.client = app.test_client()

    def register(self, correo="ana@example.com", **overrides):
        data = {
            "nombre": "Ana Pérez",
            "correo": correo,
            "contrasena": "clave-segura-123",
            "confirmacion": "clave-segura-123",
        }
        data.update(overrides)
        return self.client.post("/registro", data=data)

    def login(self, correo="ana@example.com"):
        return self.client.post(
            "/login", data={"correo": correo, "contrasena": "clave-segura-123"}
        )

    def saved_predictions(self):
        with app.app_context():
            return get_db().execute(
                """SELECT usuario_id, modelo, año_objetivo, prediccion, r2, mae, rmse, fecha
                   FROM predicciones_usuario ORDER BY id"""
            ).fetchall()

    def test_registration_validation_and_password_hash(self):
        for overrides, message in (
            ({"nombre": ""}, "Completa todos los campos"),
            ({"correo": "invalido"}, "correo electrónico válido"),
            ({"confirmacion": "otra-clave"}, "no coinciden"),
            ({"contrasena": "corta", "confirmacion": "corta"}, "al menos 8"),
        ):
            response = self.register(**overrides)
            self.assertEqual(response.status_code, 400)
            self.assertIn(message, response.get_data(as_text=True))

        response = self.register()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        with app.app_context():
            row = get_db().execute(
                "SELECT nombre, correo, password_hash, fecha_registro FROM usuarios"
            ).fetchone()
        self.assertEqual(row[0], "Ana Pérez")
        self.assertEqual(row[1], "ana@example.com")
        self.assertNotEqual(row[2], "clave-segura-123")
        self.assertTrue(row[3])
        self.assertIn("ya está registrado", self.register(correo="ANA@example.com").get_data(as_text=True))

    def test_login_profile_header_and_logout(self):
        self.assertEqual(self.client.get("/perfil").headers["Location"], "/login")
        self.register()
        self.assertIn("contraseña incorrectos", self.client.post(
            "/login", data={"correo": "ana@example.com", "contrasena": "incorrecta"}
        ).get_data(as_text=True))
        response = self.client.post(
            "/login", data={"correo": "ana@example.com", "contrasena": "clave-segura-123"}
        )
        self.assertEqual(response.headers["Location"], "/perfil")
        profile = self.client.get("/perfil").get_data(as_text=True)
        self.assertIn("Ana Pérez", profile)
        self.assertIn("ana@example.com", profile)
        self.assertIn("Fecha de registro", profile)
        self.assertIn("Huella de Carbono", profile)
        self.assertIn("Mi perfil", profile)
        self.assertIn("Cerrar sesión", profile)
        self.assertNotIn("Iniciar sesión", profile)

        self.assertEqual(self.client.get("/logout").headers["Location"], "/")
        self.assertEqual(self.client.get("/perfil").headers["Location"], "/login")
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn("Iniciar sesión", home)
        self.assertIn("Crear cuenta", home)

    def test_public_pages_and_existing_apis(self):
        for path in ("/", "/ods13", "/dashboard", "/modelos", "/acciones", "/registro", "/login"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/api/emisiones").status_code, 200)
        self.assertEqual(self.client.get("/api/prediccion?year=2030").status_code, 200)
        with patch("app.get_current_weather", return_value={"ciudad": "Montería"}):
            self.assertEqual(self.client.get("/api/clima").status_code, 200)
        with patch("app.update_dataset", return_value=5):
            self.assertEqual(self.client.post("/api/actualizar-datos").status_code, 200)

    def test_home_hero_links_resolve_to_live_pages(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        html = home.get_data(as_text=True)
        self.assertIn('class="button button-outline" href="/registro">Crear cuenta', html)
        self.assertIn('class="button button-primary" href="/dashboard">Explorar plataforma', html)
        self.assertIn('class="text-link hero-dashboard-link" href="/dashboard">Ver dashboard', html)
        self.assertEqual(self.client.get("/registro").status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_authenticated_prediction_is_saved_with_metrics(self):
        self.register()
        self.login()
        response = self.client.get("/api/prediccion?modelo=arbol_decision&year=2042")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        rows = self.saved_predictions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["modelo"], result["modelo"])
        self.assertEqual(rows[0]["año_objetivo"], result["año"])
        self.assertAlmostEqual(rows[0]["prediccion"], result["prediccion"])
        for metric in ("r2", "mae", "rmse"):
            self.assertAlmostEqual(rows[0][metric], result["metricas"][metric])
        self.assertTrue(rows[0]["fecha"])
        profile = self.client.get("/perfil").get_data(as_text=True)
        self.assertIn("Mi historial climático", profile)
        self.assertIn("Árbol de decisión", profile)
        self.assertIn("2042", profile)

    def test_anonymous_prediction_works_without_history(self):
        response = self.client.get("/api/prediccion?year=2043")
        self.assertEqual(response.status_code, 200)
        self.assertIn("prediccion", response.get_json())
        self.assertEqual(len(self.saved_predictions()), 0)
        self.assertEqual(self.client.get("/perfil").headers["Location"], "/login")

    def test_profile_shows_only_current_users_history(self):
        self.register()
        self.login()
        self.assertIn(
            "Aún no has realizado predicciones climáticas.",
            self.client.get("/perfil").get_data(as_text=True),
        )
        self.client.get("/api/prediccion?year=2044")
        self.client.get("/logout")

        self.register(correo="beatriz@example.com", nombre="Beatriz")
        self.login("beatriz@example.com")
        empty_profile = self.client.get("/perfil").get_data(as_text=True)
        self.assertIn("Aún no has realizado predicciones climáticas.", empty_profile)
        self.assertNotIn("2044", empty_profile)
        self.client.get("/api/prediccion?year=2055")
        own_profile = self.client.get("/perfil").get_data(as_text=True)
        self.assertIn("2055", own_profile)
        self.assertNotIn("2044", own_profile)

        self.client.get("/logout")
        self.login()
        first_profile = self.client.get("/perfil").get_data(as_text=True)
        self.assertIn("2044", first_profile)
        self.assertNotIn("2055", first_profile)
        self.assertEqual(len(self.saved_predictions()), 2)

    def test_existing_user_database_gains_history_table(self):
        old_database = Path(self.temp_dir.name) / "usuarios_existentes.db"
        with closing(sqlite3.connect(old_database)) as connection:
            connection.execute(
                """CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    correo TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    fecha_registro TEXT NOT NULL
                )"""
            )
            connection.execute(
                """INSERT INTO usuarios (nombre, correo, password_hash, fecha_registro)
                   VALUES ('Existente', 'existente@example.com', 'hash-anterior', '2025-01-01')"""
            )
            connection.commit()

        app.config["DATABASE"] = str(old_database)
        with app.app_context():
            init_db()
            self.assertEqual(
                get_db().execute("SELECT nombre FROM usuarios").fetchone()["nombre"],
                "Existente",
            )
            self.assertEqual(
                get_db().execute("SELECT COUNT(*) FROM predicciones_usuario").fetchone()[0],
                0,
            )
            with self.assertRaises(sqlite3.IntegrityError):
                get_db().execute(
                    """INSERT INTO predicciones_usuario
                       (usuario_id, modelo, año_objetivo, prediccion, r2, mae, rmse)
                       VALUES (999, 'regresion_lineal', 2030, 1.0, 1.0, 1.0, 1.0)"""
                )


if __name__ == "__main__":
    unittest.main()
