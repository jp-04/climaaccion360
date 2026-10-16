-- Respaldo lógico SQLite con datos ficticios. No contiene usuarios reales.
-- Las cuentas tienen hashes de contraseñas aleatorias no conservadas.
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;
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

INSERT INTO "usuarios" VALUES(1,'Persona Ejemplo Uno','ejemplo1@example.invalid','scrypt:32768:8:1$GGt8qkrbjSrjOQi6$8255115bc6875ffdf29ad11c294523e653f15b260f901c16cfe7f97d3d66908700e76d225716c632837e9781d3ec904efd5516f77f6922984c18f9e9d61b53a0','2026-01-15T10:00:00.000Z');
INSERT INTO "usuarios" VALUES(2,'Persona Ejemplo Dos','ejemplo2@example.invalid','scrypt:32768:8:1$ZHqR4743JoCZ1Prg$5e0fab6856c85cef5154cab9fcd0be3c748bfebc1e478d607fac72dc524d2657cd85a4237ebfca62b9833ca36f7ee5e569dce250b21061cf3eb9ee03ed05c836','2026-01-16T10:00:00.000Z');
INSERT INTO "predicciones_usuario" VALUES(1,1,'regresion_lineal',2030,1.65,0.81,0.13,0.17,'2026-01-17T12:00:00.000Z');
INSERT INTO "predicciones_usuario" VALUES(2,1,'arbol_decision',2040,1.72,0.79,0.14,0.18,'2026-01-18T12:00:00.000Z');
INSERT INTO "predicciones_usuario" VALUES(3,2,'regresion_lineal',2035,1.69,0.81,0.13,0.17,'2026-01-19T12:00:00.000Z');
COMMIT;
