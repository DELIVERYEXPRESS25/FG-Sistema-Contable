"""
════════════════════════════════════════════════════════════════════════════
 Colectivo FG - Base de Datos SQLite Optimizada
═══════════════════════════════════════════════════════════════════════════

Base de datos SQLite con:
- Soporte para variables de entorno
- Índices optimizados
- Connection pool
- Caché en memoria
- Transacciones eficientes
- Archivo oculto
"""

import sqlite3
import json
import os
import sys
from functools import lru_cache
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN - Variables de entorno
# ════════════════════════════════════════════════════════════════════════


def get_db_config():
    """Lee configuración de base de datos desde variables de entorno."""
    return {
        "type": os.getenv("DB_TYPE", "sqlite"),
        "path": os.getenv("DB_PATH", ".colectivo_fg.db"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "name": os.getenv("DB_NAME", "colectivo_fg"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


def get_db_path():
    """Retorna la ruta de la base de datos (archivo oculto)."""
    config = get_db_config()

    if config["type"] != "sqlite":
        # Para PostgreSQL/MySQL retornar None
        return None

    # Verificar si estamos en modo compilado
    if getattr(sys, "frozen", False):
        # Compilado: junto al .exe
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, config["path"])
    else:
        # Desarrollo - usar variable de entorno o valor por defecto
        return config["path"]


def get_db_connection_string():
    """Retorna string de conexión para PostgreSQL/MySQL."""
    config = get_db_config()

    if config["type"] == "postgresql":
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['name']}"
    elif config["type"] == "mysql":
        return f"mysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['name']}"

    return None


# Caché global de conexión
_connection_pool = {}


@contextmanager
def get_connection():
    """Context manager para obtener conexión SQLite con optimizaciones."""
    db_path = get_db_path()

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna

    # Optimizaciones de rendimiento
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance seguridad/velocidad
    conn.execute("PRAGMA cache_size=10000")  # Cache de 10MB
    conn.execute("PRAGMA temp_store=MEMORY")  # Temporales en RAM

    try:
        yield conn
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN
# ════════════════════════════════════════════════════════════════════════════


def init_database():
    """Crea tablas e índices optimizados."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabla principal de datos (JSON comprimido)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_data (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de cuentas (desnormalizada para velocidad)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cuentas (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                saldo REAL DEFAULT 0,
                activa INTEGER DEFAULT 1
            )
        """)

        # Tabla de movimientos (para consultas rápidas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE NOT NULL,
                asiento_id INTEGER,
                cuenta TEXT NOT NULL,
                debe REAL DEFAULT 0,
                haber REAL DEFAULT 0,
                descripcion TEXT,
                FOREIGN KEY (cuenta) REFERENCES cuentas(codigo)
            )
        """)

        # Índices para rendimiento
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta ON movimientos(cuenta)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_movimientos_asiento ON movimientos(asiento_id)"
        )

        # Tabla de Kardex PEPS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kardex_lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto TEXT NOT NULL,
                fecha DATE NOT NULL,
                cantidad_original INTEGER NOT NULL,
                cantidad_restante INTEGER NOT NULL,
                costo_unitario REAL NOT NULL,
                activo INTEGER DEFAULT 1
            )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_kardex_producto ON kardex_lotes(producto, fecha)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_kardex_activo ON kardex_lotes(activo)"
        )

        # Inicializar datos si no existen
        cursor.execute("SELECT COUNT(*) FROM app_data WHERE key = ?", ("main_data",))
        if cursor.fetchone()[0] == 0:
            initial_data = empty_data()
            cursor.execute(
                "INSERT INTO app_data (key, value) VALUES (?, ?)",
                ("main_data", json.dumps(initial_data)),
            )

            print("✓ Base de datos inicializada con cuentas por defecto")

        conn.commit()

        # Ocultar archivo en Windows
        if sys.platform == "win32":
            try:
                import ctypes

                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                ctypes.windll.kernel32.SetFileAttributesW(
                    db_path, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
                )
            except:
                pass


# ════════════════════════════════════════════════════════════════════════════
#  OPERACIONES OPTIMIZADAS
# ════════════════════════════════════════════════════════════════════════════


def load_data():
    """Carga datos desde SQLite. Sin caché para ser thread-safe con Flask."""
    if not os.path.exists(get_db_path()):
        init_database()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_data WHERE key = ?", ("main_data",))
        row = cursor.fetchone()

        if row:
            return json.loads(row[0])
        else:
            init_database()
            # Reintentar tras inicializar
            cursor.execute("SELECT value FROM app_data WHERE key = ?", ("main_data",))
            row2 = cursor.fetchone()
            return json.loads(row2[0]) if row2 else {}


def save_data(data):
    """Guarda datos en SQLite."""

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO app_data (key, value, updated_at) VALUES (?, ?, datetime("now"))',
            ("main_data", json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()


def empty_data():
    """Retorna estructura vacía con cuentas iniciales."""
    return {
        "cuentas": {
            "1001": {"nombre": "Efectivo", "tipo": "Activo", "saldo": 0},
            "1002": {"nombre": "Bancos", "tipo": "Activo", "saldo": 0},
            "1003": {"nombre": "Cuentas por Cobrar", "tipo": "Activo", "saldo": 0},
            "1004": {"nombre": "Inventario", "tipo": "Activo", "saldo": 0},
            "2001": {"nombre": "Cuentas por Pagar", "tipo": "Pasivo", "saldo": 0},
            "2002": {"nombre": "Proveedores", "tipo": "Pasivo", "saldo": 0},
            "3001": {"nombre": "Capital", "tipo": "Capital", "saldo": 0},
            "4001": {"nombre": "Ventas", "tipo": "Ingreso", "saldo": 0},
            "4002": {"nombre": "Otros Ingresos", "tipo": "Ingreso", "saldo": 0},
            "5001": {"nombre": "Costo de Ventas", "tipo": "Gasto", "saldo": 0},
            "5002": {"nombre": "Gastos Operativos", "tipo": "Gasto", "saldo": 0},
            "5003": {"nombre": "Gastos Administrativos", "tipo": "Gasto", "saldo": 0},
        },
        "diario": [],
        "productos": {},
        "kardex": {},
        "kardex_peps": {},
        "pos_historial": [],
        "cuentas_cobrar": [],
        "caja": [],
    }


# ════════════════════════════════════════════════════════════════════════════
#  CONSULTAS OPTIMIZADAS
# ════════════════════════════════════════════════════════════════════════════


def get_movimientos_cuenta(cuenta, fecha_desde=None, fecha_hasta=None):
    """Consulta rápida de movimientos de una cuenta."""
    with get_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM movimientos WHERE cuenta = ?"
        params = [cuenta]

        if fecha_desde:
            query += " AND fecha >= ?"
            params.append(fecha_desde)

        if fecha_hasta:
            query += " AND fecha <= ?"
            params.append(fecha_hasta)

        query += " ORDER BY fecha DESC, id DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_saldo_cuenta(cuenta):
    """Consulta optimizada de saldo de una cuenta."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT SUM(debe) as total_debe, SUM(haber) as total_haber FROM movimientos WHERE cuenta = ?",
            (cuenta,),
        )
        row = cursor.fetchone()
        if row and row["total_debe"] is not None:
            return row["total_debe"] - row["total_haber"]
        return 0


def optimize_database():
    """Optimiza la base de datos (VACUUM, ANALYZE)."""
    with get_connection() as conn:
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        conn.commit()
