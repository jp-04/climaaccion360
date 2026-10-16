"""The academic database artifacts must match the running SQLite schema."""

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from database import SCHEMA


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "database"


class DatabaseArtifactsTestCase(unittest.TestCase):
    def test_documented_schema_matches_application(self):
        documented = (ARTIFACTS / "schema.sql").read_text(encoding="utf-8")
        self.assertEqual(documented.strip(), SCHEMA.strip())

    def test_fictional_backup_restores_with_valid_relations(self):
        backup = (ARTIFACTS / "respaldo_ejemplo.sql").read_text(encoding="utf-8")
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(backup)
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            self.assertEqual(tables, {"usuarios", "predicciones_usuario"})
            users = connection.execute("SELECT correo, password_hash FROM usuarios").fetchall()
            self.assertEqual(len(users), 2)
            self.assertTrue(all(email.endswith("@example.invalid") for email, _ in users))
            self.assertTrue(all(password_hash.startswith("scrypt:") for _, password_hash in users))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM predicciones_usuario").fetchone()[0],
                3,
            )
            foreign_keys = connection.execute("PRAGMA foreign_key_list(predicciones_usuario)").fetchall()
            self.assertEqual(len(foreign_keys), 1)
            self.assertEqual(
                (foreign_keys[0][2], foreign_keys[0][3], foreign_keys[0][4], foreign_keys[0][6]),
                ("usuarios", "usuario_id", "id", "CASCADE"),
            )
            connection.execute("DELETE FROM usuarios WHERE id = 1")
            self.assertEqual(
                connection.execute("SELECT usuario_id FROM predicciones_usuario").fetchall(),
                [(2,)],
            )


if __name__ == "__main__":
    unittest.main()
