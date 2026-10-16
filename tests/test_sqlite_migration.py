"""Checks that the optional data import starts safely from a real SQLite file."""

import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "database" / "migrar_sqlite_a_postgres.py"
EXAMPLE = ROOT / "database" / "respaldo_ejemplo.sql"
SPEC = importlib.util.spec_from_file_location("sqlite_to_postgres_migration", SCRIPT)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class SQLiteMigrationTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sqlite_path = Path(self.temp_dir.name) / "origen.db"
        with closing(sqlite3.connect(self.sqlite_path)) as db:
            db.executescript(EXAMPLE.read_text(encoding="utf-8"))

    def invoke(self, *args, url=None):
        environment = os.environ.copy()
        environment.pop("DATABASE_URL", None)
        if url is not None:
            environment["DATABASE_URL"] = url
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--sqlite", str(self.sqlite_path), *args],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_dry_run_counts_rows_without_contacting_postgres(self):
        result = self.invoke(url="postgresql://usuario:secreto@host/base")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 usuarios y 3 predicciones", result.stdout)
        self.assertIn("no se conectó a PostgreSQL", result.stdout)

    def test_example_users_cannot_be_imported(self):
        result = self.invoke("--apply", url="postgresql://usuario:secreto@host/base")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cuentas ficticias", result.stdout)
        self.assertNotIn("secreto", result.stdout + result.stderr)

    def test_apply_requires_database_url(self):
        result = self.invoke("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("DATABASE_URL", result.stdout)

    def test_import_preserves_rows_in_one_transaction(self):
        users, predictions = MIGRATION.read_sqlite(self.sqlite_path)
        users = [(*user[:2], f"persona{user[0]}@test.local", *user[3:]) for user in users]
        pg = MagicMock()
        pg.execute.side_effect = [
            MagicMock(),
            MagicMock(fetchone=lambda: (0, 0)),
            MagicMock(),
            MagicMock(),
            MagicMock(fetchone=lambda: (len(users), len(predictions))),
        ]
        with patch.object(MIGRATION.psycopg, "connect") as connect:
            connect.return_value.__enter__.return_value = pg
            MIGRATION.migrate("postgresql://usuario:secreto@host/base", users, predictions)
        pg.transaction.assert_called_once_with()
        inserts = pg.cursor.return_value.__enter__.return_value.executemany.call_args_list
        self.assertEqual(len(inserts), 2)
        self.assertEqual(inserts[0].args[1], users)
        self.assertEqual(inserts[1].args[1], predictions)

    def test_import_refuses_nonempty_destination(self):
        pg = MagicMock()
        pg.execute.side_effect = [MagicMock(), MagicMock(fetchone=lambda: (1, 0))]
        with patch.object(MIGRATION.psycopg, "connect") as connect:
            connect.return_value.__enter__.return_value = pg
            with self.assertRaisesRegex(ValueError, "no está vacía"):
                MIGRATION.migrate(
                    "postgresql://usuario:secreto@host/base",
                    [(1, "Persona", "persona@test.local", "hash", "2026-01-01T00:00:00Z")],
                    [],
                )
        pg.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
