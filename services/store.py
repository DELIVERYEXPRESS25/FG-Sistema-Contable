import time
from flask import g
import db_internal
from services.helpers import ensure_ids
from services.calculos import calcular_mayor


_archivos_temp = {}
_MAX_ARCHIVOS_TEMP = 20

_data_cache_global = {"data": None, "ts": 0}
_DATA_CACHE_TTL = 0.5


CUENTAS_BASE = {
    "1":     {"nombre": "Activo", "tipo": "Activo", "saldo": 0},
    "1.1":   {"nombre": "Activo Corriente", "tipo": "Activo", "saldo": 0},
    "1.1.01":{"nombre": "Efectivo", "tipo": "Activo", "saldo": 0},
    "1.1.02":{"nombre": "Bancos", "tipo": "Activo", "saldo": 0},
    "1.1.03":{"nombre": "Cuentas por cobrar", "tipo": "Activo", "saldo": 0},
    "1.1.04":{"nombre": "Inventario de mercancias", "tipo": "Activo", "saldo": 0},
    "1.1.05":{"nombre": "Deudores Diversos", "tipo": "Activo", "saldo": 0},
    "1.2":   {"nombre": "Activo No Corriente", "tipo": "Activo", "saldo": 0},
    "1.2.01":{"nombre": "Terreno", "tipo": "Activo", "saldo": 0},
    "1.2.02":{"nombre": "Edificio", "tipo": "Activo", "saldo": 0},
    "1.2.03":{"nombre": "Mobiliario y Equipo", "tipo": "Activo", "saldo": 0},
    "1.2.04":{"nombre": "Equipo de Computo Electronico", "tipo": "Activo", "saldo": 0},
    "2":     {"nombre": "Pasivo", "tipo": "Pasivo", "saldo": 0},
    "2.1":   {"nombre": "Pasivo Corriente", "tipo": "Pasivo", "saldo": 0},
    "2.1.01":{"nombre": "Proveedores", "tipo": "Pasivo", "saldo": 0},
    "2.1.02":{"nombre": "Acreedores Diversos", "tipo": "Pasivo", "saldo": 0},
    "2.1.03":{"nombre": "Impuestos por Pagar", "tipo": "Pasivo", "saldo": 0},
    "2.2":   {"nombre": "Pasivo No Corriente", "tipo": "Pasivo", "saldo": 0},
    "2.2.01":{"nombre": "Prestamos Bancarios Por Pagar Largo Plazo", "tipo": "Pasivo", "saldo": 0},
    "3":     {"nombre": "Patrimonio", "tipo": "Capital", "saldo": 0},
    "3.1":   {"nombre": "Capital Social", "tipo": "Capital", "saldo": 0},
    "3.2":   {"nombre": "Capital Contable", "tipo": "Capital", "saldo": 0},
    "3.3":   {"nombre": "Resultados", "tipo": "Capital", "saldo": 0},
    "3.3.01":{"nombre": "Utilidad del Ejercicio", "tipo": "Capital", "saldo": 0},
    "3.3.02":{"nombre": "Perdida del Ejercicio", "tipo": "Capital", "saldo": 0},
    "3.4":   {"nombre": "Utilidad Acumulada", "tipo": "Capital", "saldo": 0},
    "4":     {"nombre": "Ingresos", "tipo": "Ingreso", "saldo": 0},
    "4.1":   {"nombre": "Ingresos por Ventas", "tipo": "Ingreso", "saldo": 0},
    "4.1.01":{"nombre": "Ventas al contado", "tipo": "Ingreso", "saldo": 0},
    "4.1.02":{"nombre": "Ventas al credito", "tipo": "Ingreso", "saldo": 0},
    "4.2":   {"nombre": "Devoluciones sobre Ventas (Resta a los ingresos)", "tipo": "Ingreso", "saldo": 0},
    "5":     {"nombre": "Costos y Gastos", "tipo": "Gasto", "saldo": 0},
    "5.1":   {"nombre": "Costo de Ventas", "tipo": "Gasto", "saldo": 0},
    "5.2":   {"nombre": "Gastos de Operacion", "tipo": "Gasto", "saldo": 0},
    "5.2.01":{"nombre": "Sueldos y Salarios", "tipo": "Gasto", "saldo": 0},
    "5.2.02":{"nombre": "Renta del Local", "tipo": "Gasto", "saldo": 0},
    "5.2.03":{"nombre": "Servicios Basicos (Luz, agua, internet)", "tipo": "Gasto", "saldo": 0},
    "5.2.04":{"nombre": "Publicidad y Marketing", "tipo": "Gasto", "saldo": 0},
    "5.2.05":{"nombre": "Papeleria y Empaques (Bolsas, cajas de regalo)", "tipo": "Gasto", "saldo": 0},
}

FORMAS_PAGO_VALIDAS = {"Efectivo", "Banco", "Credito"}


def empty_data():
    return {
        "cuentas": dict(CUENTAS_BASE),
        "diario": [],
        "kardex": {},
        "cuentas_cobrar": [],
        "caja_movimientos": [],
        "ajustes": [],
    }


def _obtener_rango_fechas(tipo, periodo):
    import calendar
    if tipo == "mensual":
        anio, mes = periodo.split("-")
        ultimo = calendar.monthrange(int(anio), int(mes))[1]
        return f"{periodo}-01", f"{periodo}-{ultimo:02d}"
    elif tipo == "semanal":
        anio, semana = periodo.split("-W")
        from datetime import date as _dt, timedelta
        d = _dt.fromisocalendar(int(anio), int(semana), 1)
        return d.isoformat(), (d + timedelta(days=6)).isoformat()
    elif tipo == "quincenal":
        if periodo.endswith("-S1"):
            base = periodo[:-3]
            return f"{base}-01", f"{base}-15"
        elif periodo.endswith("-S2"):
            base = periodo[:-3]
            anio, mes = base.split("-")
            ultimo = calendar.monthrange(int(anio), int(mes))[1]
            return f"{base}-16", f"{base}-{ultimo:02d}"
        else:
            base = periodo[:7]
            return f"{base}-01", f"{base}-15"
    return periodo[:7] + "-01", periodo[:7] + "-28"


def _periodo_cerrado(data, fecha):
    for c in data.get("cierres_mensuales", []):
        tipo = c.get("tipo", "mensual")
        desde, hasta = _obtener_rango_fechas(tipo, c["periodo"])
        if desde <= fecha <= hasta:
            return True
    return False


def _periodos_disponibles_por_tipo(data, tipo):
    fechas = set()
    for entry in data.get("diario", []):
        fechas.add(entry["fecha"])
    for aj in data.get("ajustes", []):
        fechas.add(aj["fecha"])
    periodos = set()
    for f in fechas:
        if tipo == "mensual":
            periodos.add(f[:7])
        elif tipo == "semanal":
            from datetime import date as _dt
            d = _dt.fromisoformat(f)
            iso = d.isocalendar()
            periodos.add(f"{iso[0]}-W{iso[1]:02d}")
        elif tipo == "quincenal":
            dia = int(f[8:10])
            suf = "S1" if dia <= 15 else "S2"
            periodos.add(f[:7] + "-" + suf)
    return sorted(periodos)


def _paginar(items, page, per_page=50):
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages, total


def load_data():
    """Carga datos desde base de datos interna SQLite.
    Usa cache por-request (Flask g) para evitar lecturas repetidas a SQLite
    dentro de la misma peticion HTTP — mejora de rendimiento."""
    if hasattr(g, "_data_cache") and g._data_cache is not None:
        return g._data_cache
    now = time.time()
    global _data_cache_global
    if _data_cache_global["data"] is not None and (now - _data_cache_global["ts"]) < _DATA_CACHE_TTL:
        data = _data_cache_global["data"]
    else:
        data = db_internal.load_data()
        _data_cache_global["data"] = data
        _data_cache_global["ts"] = now
    ensure_ids(data)
    _defaults = {
        "caja_movimientos": [],
        "cuentas_cobrar": [],
        "pos_historial": [],
        "ajustes": [],
        "diario": [],
        "kardex": {},
        "kardex_peps": {},
        "productos": {},
        "cuentas": {},
        "gastos_comercializacion": [],
        "cierres_mensuales": [],
        "auditoria": [],
        "_config": {},
        "configuracion": {},
    }
    for key, default in _defaults.items():
        if key not in data:
            data[key] = default

    if not data["caja_movimientos"] and data.get("caja"):
        data["caja_movimientos"] = data["caja"]

    for entry in data.get("diario", []):
        if "movimientos" not in entry:
            entry["movimientos"] = []
        if "ref" not in entry:
            entry["ref"] = ""
        if "id" not in entry:
            entry["id"] = 0
    for aj in data.get("ajustes", []):
        if "movimientos" not in aj:
            aj["movimientos"] = []
        if "ref" not in aj:
            aj["ref"] = ""

    try:
        g._data_cache = data
    except RuntimeError:
        pass
    return data


def save_data(data):
    """Guarda datos en base de datos interna SQLite e invalida cache del request."""
    db_internal.save_data(data)
    global _data_cache_global
    _data_cache_global["data"] = None
    _data_cache_global["ts"] = 0
    try:
        g._data_cache = data
        g._mayor_cache = None
    except RuntimeError:
        pass


def _mayor_cached(data):
    try:
        if hasattr(g, "_mayor_cache") and g._mayor_cache is not None:
            return g._mayor_cache
        result = calcular_mayor(data)
        g._mayor_cache = result
        return result
    except RuntimeError:
        return calcular_mayor(data)
