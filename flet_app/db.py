"""
══════════════════════════════════════════════════════════════════════════════
 Módulo de Base de Datos para Flet
══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os

# Agregar el directorio padre al path para importar db_internal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db_internal import (
        init_database,
        load_data as _load_data,
        save_data as _save_data,
        empty_data,
        get_db_path,
    )
except ImportError:
    # Fallback si no se puede importar
    import json

    DB_FILE = ".colectivo_fg_flet.db"

    def init_db():
        """Inicializa la base de datos."""
        if not os.path.exists(DB_FILE):
            data = empty_data()
            with open(DB_FILE, "w") as f:
                json.dump(data, f)

    def load_data():
        """Carga datos desde archivo JSON."""
        if not os.path.exists(DB_FILE):
            init_db()
        with open(DB_FILE, "r") as f:
            return json.load(f)

    def save_data(data):
        """Guarda datos en archivo JSON."""
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def empty_data():
        """Retorna estructura vacía."""
        return {
            "cuentas": {},
            "diario": [],
            "kardex": {},
            "kardex_peps": {},
            "pos_historial": [],
            "cuentas_cobrar": [],
            "caja": [],
            "caja_movimientos": [],
            "ajustes": [],
            "gastos_comercializacion": [],
        }
else:

    def init_db():
        """Inicializa la base de datos."""
        init_database()

    def load_data():
        """Carga datos desde SQLite."""
        return _load_data()

    def save_data(data):
        """Guarda datos en SQLite."""
        _save_data(data)

    def empty_data():
        """Retorna estructura vacía."""
        return (
            _load_data.__code__.co_consts[1] if hasattr(_load_data, "__code__") else {}
        )


# Funciones helper para IDs únicos
def get_next_id(data: dict, key: str) -> int:
    """Retorna el siguiente ID único para una lista."""
    if key not in data or not data[key]:
        return 1
    items = data[key]
    max_id = 0
    for item in items:
        if isinstance(item, dict) and "id" in item:
            if item["id"] > max_id:
                max_id = item["id"]
    return max_id + 1


def ensure_ids(data: dict):
    """Asegura que todas las listas tengan IDs únicos."""
    for key, lista in data.items():
        if isinstance(lista, list) and lista:
            seen = set()
            next_id = 1
            for item in lista:
                if isinstance(item, dict):
                    if "id" not in item:
                        while next_id in seen:
                            next_id += 1
                        item["id"] = next_id
                        seen.add(next_id)
                        next_id += 1
                    else:
                        if item["id"] in seen:
                            while next_id in seen:
                                next_id += 1
                            item["id"] = next_id
                            next_id += 1
                        seen.add(item["id"])
