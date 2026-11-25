"""Script de migración: agrega columnas de sync y tabla historial_sync_academico."""
import os
import sys

os.chdir(r'c:\Users\ACER\Documents\NEXO_UNDAC_V9')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

url = URL.create(
    'mysql+pymysql',
    username=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '3306')),
    database=os.getenv('DB_NAME', 'seguimiento_egresados'),
)
engine = create_engine(url)

def col_existe(conn, tabla, columna):
    q = text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() "
        "AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    )
    return conn.execute(q, {"t": tabla, "c": columna}).scalar() > 0


with engine.connect() as conn:
    # -- Columnas nuevas en egresados --
    nuevas_cols = [
        ("ultima_sync_undac",       "DATETIME NULL"),
        ("ultima_sync_sunedu",      "DATETIME NULL"),
        ("ultima_sync_reniec",      "DATETIME NULL"),
        ("consentimiento_consulta", "TINYINT(1) NOT NULL DEFAULT 0"),
    ]
    for col, tipo in nuevas_cols:
        if not col_existe(conn, 'egresados', col):
            conn.execute(text(f"ALTER TABLE egresados ADD COLUMN {col} {tipo}"))
            print(f"OK: columna egresados.{col}")
        else:
            print(f"YA EXISTE: egresados.{col}")

    # -- Tabla historial_sync_academico --
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS historial_sync_academico (
            id_sync        INT AUTO_INCREMENT PRIMARY KEY,
            id_egresado    INT NOT NULL,
            fuente         VARCHAR(30)  NOT NULL,
            campo          VARCHAR(60)  NOT NULL,
            valor_anterior TEXT,
            valor_nuevo    TEXT,
            operador       ENUM('sistema','egresado','admin') NOT NULL DEFAULT 'sistema',
            creado_en      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_egresado) REFERENCES egresados(id_egresado) ON DELETE CASCADE,
            INDEX idx_hsa_egresado (id_egresado),
            INDEX idx_hsa_fecha    (creado_en)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    print("OK: tabla historial_sync_academico")

    conn.commit()

print("Migracion completada con exito.")
