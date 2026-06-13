import os
import sys


def get_next_id(data, key):
    if key not in data or not data[key]:
        return 1
    items = data[key]
    max_id = 0
    for item in items:
        if isinstance(item, dict) and "id" in item:
            if item["id"] > max_id:
                max_id = item["id"]
    return max_id + 1


def ensure_ids(data):
    skip_keys = {"pos_historial", "auditoria"}
    for key, lista in data.items():
        if key in skip_keys or not isinstance(lista, list) or not lista:
            continue
        seen = set()
        next_id_for_key = 1
        for item in lista:
            if isinstance(item, dict):
                if "id" not in item:
                    while next_id_for_key in seen:
                        next_id_for_key += 1
                    item["id"] = next_id_for_key
                    seen.add(next_id_for_key)
                    next_id_for_key += 1
                else:
                    if item["id"] in seen:
                        while next_id_for_key in seen:
                            next_id_for_key += 1
                        item["id"] = next_id_for_key
                        next_id_for_key += 1
                    seen.add(item["id"])


def get_data_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


DATA_FILE = os.path.join(get_data_dir(), "data.json")


def tipo_saldo(tipo_cuenta):
    return "Debe" if tipo_cuenta in ["Activo", "Gasto"] else "Haber"
