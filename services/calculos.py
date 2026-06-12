from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from services.helpers import tipo_saldo


def calcular_mayor(data):
    mayor = defaultdict(lambda: {"debe": 0, "haber": 0, "movimientos": []})
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            cuenta = mov["cuenta"]
            if mov["tipo"] == "Debe":
                mayor[cuenta]["debe"] += mov["monto"]
            else:
                mayor[cuenta]["haber"] += mov["monto"]
            mayor[cuenta]["movimientos"].append(
                {
                    "fecha": entry["fecha"],
                    "descripcion": entry["descripcion"],
                    "tipo": mov["tipo"],
                    "monto": mov["monto"],
                    "ref": entry.get("ref", ""),
                }
            )
    for aj in data.get("ajustes", []):
        for mov in aj["movimientos"]:
            cuenta = mov["cuenta"]
            if mov["tipo"] == "Debe":
                mayor[cuenta]["debe"] += mov["monto"]
            else:
                mayor[cuenta]["haber"] += mov["monto"]
            mayor[cuenta]["movimientos"].append(
                {
                    "fecha": aj["fecha"],
                    "descripcion": aj["descripcion"],
                    "tipo": mov["tipo"],
                    "monto": mov["monto"],
                    "ref": "AJ",
                }
            )
    return mayor


def calcular_balanza(data):
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]
    balanza = []
    total_debe = 0
    total_haber = 0
    total_saldo_d = 0
    total_saldo_h = 0
    for codigo in sorted(cuentas.keys()):
        info = cuentas[codigo]
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        ts = tipo_saldo(info["tipo"])
        if ts == "Debe":
            saldo = debe - haber
            saldo_d = max(saldo, 0)
            saldo_h = max(-saldo, 0)
        else:
            saldo = haber - debe
            saldo_h = max(saldo, 0)
            saldo_d = max(-saldo, 0)
        balanza.append(
            {
                "codigo": codigo,
                "nombre": info["nombre"],
                "tipo": info["tipo"],
                "debe": debe,
                "haber": haber,
                "saldo_debe": saldo_d,
                "saldo_haber": saldo_h,
            }
        )
        total_debe += debe
        total_haber += haber
        total_saldo_d += saldo_d
        total_saldo_h += saldo_h
    return balanza, total_debe, total_haber, total_saldo_d, total_saldo_h


def calcular_estado_resultados(data):
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]
    ingresos = 0
    gastos = 0
    detalle_ingresos = []
    detalle_gastos = []
    for codigo, info in cuentas.items():
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        if info["tipo"] == "Ingreso":
            monto = haber - debe
            ingresos += monto
            detalle_ingresos.append({"nombre": info["nombre"], "monto": monto})
        elif info["tipo"] == "Gasto":
            monto = debe - haber
            gastos += monto
            detalle_gastos.append({"nombre": info["nombre"], "monto": monto})
    utilidad = ingresos - gastos
    return detalle_ingresos, ingresos, detalle_gastos, gastos, utilidad


def calcular_balance_general(data):
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]
    _, _, _, _, utilidad = calcular_estado_resultados(data)
    activos = []
    pasivos = []
    capital_items = []
    total_activo = 0
    total_pasivo = 0
    total_capital = 0
    for codigo in sorted(cuentas.keys()):
        info = cuentas[codigo]
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        ts = tipo_saldo(info["tipo"])
        if ts == "Debe":
            saldo = debe - haber
        else:
            saldo = haber - debe
        if info["tipo"] == "Activo":
            activos.append({"nombre": info["nombre"], "saldo": saldo})
            total_activo += saldo
        elif info["tipo"] == "Pasivo":
            pasivos.append({"nombre": info["nombre"], "saldo": saldo})
            total_pasivo += saldo
        elif info["tipo"] == "Capital":
            capital_items.append({"nombre": info["nombre"], "saldo": saldo})
            total_capital += saldo
    total_capital += utilidad
    capital_items.append({"nombre": "Utilidad del Periodo", "saldo": utilidad})
    return activos, total_activo, pasivos, total_pasivo, capital_items, total_capital


def get_ventas_por_dia(data):
    ventas = defaultdict(float)
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            cuenta = mov["cuenta"]
            if cuenta == "4001" and mov["tipo"] == "Haber":
                ventas[entry["fecha"]] += mov["monto"]
    return dict(sorted(ventas.items()))


def get_ventas_por_mes(data):
    ventas = defaultdict(float)
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            if mov["cuenta"] == "4001" and mov["tipo"] == "Haber":
                mes = entry["fecha"][:7]
                ventas[mes] += mov["monto"]
    return dict(sorted(ventas.items()))


def get_gastos_por_mes(data):
    gastos = defaultdict(float)
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            cuenta = mov["cuenta"]
            if (
                data["cuentas"].get(cuenta, {}).get("tipo") == "Gasto"
                and mov["tipo"] == "Debe"
            ):
                mes = entry["fecha"][:7]
                gastos[mes] += mov["monto"]
    return dict(sorted(gastos.items()))


def calcular_saldos_cierre(data, periodo):
    mayor_temp = defaultdict(lambda: {"debe": 0, "haber": 0})
    for entry in data.get("diario", []):
        if entry["fecha"][:7] > periodo:
            continue
        for mov in entry["movimientos"]:
            if mov["tipo"] == "Debe":
                mayor_temp[mov["cuenta"]]["debe"] += mov["monto"]
            else:
                mayor_temp[mov["cuenta"]]["haber"] += mov["monto"]
    for aj in data.get("ajustes", []):
        if aj["fecha"][:7] > periodo:
            continue
        for mov in aj["movimientos"]:
            if mov["tipo"] == "Debe":
                mayor_temp[mov["cuenta"]]["debe"] += mov["monto"]
            else:
                mayor_temp[mov["cuenta"]]["haber"] += mov["monto"]
    saldos = {}
    for cod, info in data["cuentas"].items():
        d = mayor_temp[cod]["debe"]
        h = mayor_temp[cod]["haber"]
        ts = tipo_saldo(info["tipo"])
        saldo = (d - h) if ts == "Debe" else (h - d)
        saldos[cod] = {
            "nombre": info["nombre"],
            "tipo": info["tipo"],
            "debe": d,
            "haber": h,
            "saldo": saldo,
        }
    return saldos


def meses_disponibles(data):
    meses = set()
    for entry in data.get("diario", []):
        meses.add(entry["fecha"][:7])
    for aj in data.get("ajustes", []):
        meses.add(aj["fecha"][:7])
    return sorted(meses)


def calcular_saldos_periodo(data, periodo):
    mayor_temp = defaultdict(lambda: {"debe": 0, "haber": 0})
    for entry in data.get("diario", []):
        if entry["fecha"][:7] != periodo:
            continue
        if entry.get("ref", "").startswith("CIERRE-"):
            continue
        for mov in entry["movimientos"]:
            if mov["tipo"] == "Debe":
                mayor_temp[mov["cuenta"]]["debe"] += mov["monto"]
            else:
                mayor_temp[mov["cuenta"]]["haber"] += mov["monto"]
    for aj in data.get("ajustes", []):
        if aj["fecha"][:7] != periodo:
            continue
        for mov in aj["movimientos"]:
            if mov["tipo"] == "Debe":
                mayor_temp[mov["cuenta"]]["debe"] += mov["monto"]
            else:
                mayor_temp[mov["cuenta"]]["haber"] += mov["monto"]
    saldos = {}
    for cod, info in data["cuentas"].items():
        d = mayor_temp[cod]["debe"]
        h = mayor_temp[cod]["haber"]
        ts = tipo_saldo(info["tipo"])
        saldo = (d - h) if ts == "Debe" else (h - d)
        if d != 0 or h != 0:
            saldos[cod] = {
                "nombre": info["nombre"],
                "tipo": info["tipo"],
                "debe": d,
                "haber": h,
                "saldo": saldo,
            }
    return saldos


def calcular_total_comercializacion(data):
    mayor = calcular_mayor(data)
    total = 0.0
    detalle = []
    for cod in sorted(data["cuentas"].keys()):
        if not cod.startswith("6"):
            continue
        info = data["cuentas"][cod]
        if info.get("tipo") != "Gasto":
            continue
        debe = mayor[cod]["debe"] if cod in mayor else 0
        haber = mayor[cod]["haber"] if cod in mayor else 0
        saldo = debe - haber
        if saldo != 0 or debe != 0:
            detalle.append(
                {
                    "codigo": cod,
                    "nombre": info["nombre"],
                    "debe": debe,
                    "haber": haber,
                    "saldo": saldo,
                }
            )
        total += saldo
    return detalle, total


def estan_balanceados(movimientos):
    total_debe = sum(m["monto"] for m in movimientos if m["tipo"] == "Debe")
    total_haber = sum(m["monto"] for m in movimientos if m["tipo"] == "Haber")
    return abs(total_debe - total_haber) <= 0.01 and total_debe > 0 and total_haber > 0


# ═══════════════════════════════════════════════════════════════
# FUNCIONES MEJORADAS PARA CIERRE MENSUAL
# ═══════════════════════════════════════════════════════════════

def procesar_movimientos_periodo(data, desde, hasta, excluir_cierre=True):
    """
    Procesa movimientos del diario y ajustes en un rango de fechas.
    Retorna saldos de todas las cuentas en ese período (usando float para compatibilidad).
    
    Args:
        data: dict con estructura de datos
        desde: fecha inicio (YYYY-MM-DD)
        hasta: fecha fin (YYYY-MM-DD)
        excluir_cierre: si True, ignora movimientos de CIERRE-*
    
    Returns:
        dict con estructura: {codigo: {"debe": X, "haber": Y, ...}} (todos float)
    """
    saldos = defaultdict(lambda: {"debe": 0.0, "haber": 0.0})
    
    # Procesar diario
    for entry in data.get("diario", []):
        if not (desde <= entry["fecha"] <= hasta):
            continue
        if excluir_cierre and entry.get("ref", "").startswith("CIERRE-"):
            continue
        for mov in entry["movimientos"]:
            monto = float(mov["monto"]) if isinstance(mov["monto"], (int, float)) else 0.0
            if mov["tipo"] == "Debe":
                saldos[mov["cuenta"]]["debe"] += monto
            else:
                saldos[mov["cuenta"]]["haber"] += monto
    
    # Procesar ajustes
    for aj in data.get("ajustes", []):
        if not (desde <= aj["fecha"] <= hasta):
            continue
        for mov in aj["movimientos"]:
            monto = float(mov["monto"]) if isinstance(mov["monto"], (int, float)) else 0.0
            if mov["tipo"] == "Debe":
                saldos[mov["cuenta"]]["debe"] += monto
            else:
                saldos[mov["cuenta"]]["haber"] += monto
    
    return dict(saldos)


def calcular_movimientos_cierre(data, desde, hasta):
    """
    Calcula los movimientos exactos necesarios para el asiento de cierre.
    Cierra todas las cuentas de Ingresos y Gastos.
    
    Args:
        data: dict con estructura de datos
        desde: fecha inicio del período (YYYY-MM-DD)
        hasta: fecha fin del período (YYYY-MM-DD)
    
    Returns:
        tuple: (movimientos_cierre, total_ingresos, total_gastos, diferencia)
        movimientos_cierre es una lista de dicts {"cuenta": X, "tipo": Y, "monto": Z}
    """
    saldos = procesar_movimientos_periodo(data, desde, hasta, excluir_cierre=True)
    cuentas = data["cuentas"]
    movimientos = []
    total_ing = 0.0
    total_gast = 0.0
    
    # Procesar cada cuenta
    for cod, info in cuentas.items():
        tipo_cta = info.get("tipo", "")
        saldo_data = saldos.get(cod, {"debe": 0.0, "haber": 0.0})
        debe = round(float(saldo_data.get("debe", 0)), 2)
        haber = round(float(saldo_data.get("haber", 0)), 2)
        
        if tipo_cta == "Ingreso":
            # Para ingresos: saldo = haber - debe
            saldo = round(haber - debe, 2)
            if abs(saldo) > 0.001:  # Mayor a 0.001 para evitar errores de redondeo
                # Debitar la cuenta de ingreso para cerrarla
                movimientos.append({
                    "cuenta": cod,
                    "tipo": "Debe",
                    "monto": saldo
                })
                total_ing += saldo
        elif tipo_cta == "Gasto":
            # Para gastos: saldo = debe - haber
            saldo = round(debe - haber, 2)
            if abs(saldo) > 0.001:  # Mayor a 0.001 para evitar errores de redondeo
                # Acreditar la cuenta de gasto para cerrarla
                movimientos.append({
                    "cuenta": cod,
                    "tipo": "Haber",
                    "monto": saldo
                })
                total_gast += saldo
    
    # Calcular diferencia (redondear para evitar errores de precisión)
    total_debe = sum(round(m["monto"], 2) for m in movimientos if m["tipo"] == "Debe")
    total_haber = sum(round(m["monto"], 2) for m in movimientos if m["tipo"] == "Haber")
    diferencia = round(total_debe - total_haber, 2)
    
    return movimientos, round(total_ing, 2), round(total_gast, 2), diferencia


def obtener_cuenta_capital_cierre(data, crear_si_no_existe=True):
    """
    Obtiene la cuenta de capital para registrar diferencias de cierre.
    Prioridad: 3002 (Utilidades Retenidas) > 3001 (Capital).
    
    Args:
        data: dict con estructura de datos
        crear_si_no_existe: si True, crea Utilidades Retenidas si no existe
    
    Returns:
        str: código de cuenta para diferencias
    """
    for cod in ("3002", "3001"):
        if cod in data.get("cuentas", {}):
            return cod
    
    if crear_si_no_existe:
        data.setdefault("cuentas", {})["3002"] = {
            "nombre": "Utilidades Retenidas",
            "tipo": "Capital",
            "saldo": 0
        }
        return "3002"
    
    # Si no encuentra nada y no puede crear, retorna cuenta por defecto
    return "3002"


def validar_cierre_posible(data, desde, hasta):
    """
    Valida que un cierre sea posible en el período dado.
    
    Returns:
        tuple: (es_valido, mensaje_error)
    """
    saldos = procesar_movimientos_periodo(data, desde, hasta, excluir_cierre=True)
    cuentas = data["cuentas"]
    
    # Verificar que existan cuentas de resultado con saldo
    hay_resultado = False
    for cod in cuentas:
        tipo_cta = cuentas[cod].get("tipo", "")
        if tipo_cta in ("Ingreso", "Gasto"):
            if cod in saldos and (saldos[cod]["debe"] != 0 or saldos[cod]["haber"] != 0):
                hay_resultado = True
                break
    
    if not hay_resultado:
        return False, "No hay cuentas de resultado (ingresos/gastos) con saldo en este período."
    
    return True, ""
