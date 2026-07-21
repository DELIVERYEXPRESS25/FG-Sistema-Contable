from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from services.helpers import tipo_saldo


def _es_padre(codigo, cuentas):
    """True si el código tiene al menos una subcuenta dentro del catálogo."""
    prefix = codigo + "."
    return any(c.startswith(prefix) for c in cuentas)


def _construir_lista_jerarquica(cuentas, mayor, tipo_cuenta, calcular_saldo):
    """
    Construye lista jerárquica para reportes.
    
    Returns lista de dicts con: tipo (header/leaf/subtotal), nombre, saldo, nivel.
    """
    codes = sorted(c for c, info in cuentas.items() if info["tipo"] == tipo_cuenta)

    # First pass: headers + leaves
    items = []
    for codigo in codes:
        info = cuentas[codigo]
        nivel = codigo.count(".")
        es_padre = _es_padre(codigo, cuentas)
        if es_padre:
            items.append({"tipo": "header", "nombre": info["nombre"], "nivel": nivel, "codigo": codigo})
        else:
            saldo = calcular_saldo(codigo, info)
            items.append({"tipo": "leaf", "nombre": info["nombre"], "saldo": saldo, "nivel": nivel, "codigo": codigo})

    # Second pass: insert subtotals bottom-up
    max_nivel = max((item["nivel"] for item in items), default=0)
    for nivel in range(max_nivel, -1, -1):
        i = 0
        while i < len(items):
            item = items[i]
            if item["tipo"] == "header" and item["nivel"] == nivel:
                total = 0
                j = i + 1
                while j < len(items):
                    child = items[j]
                    if child["tipo"] == "header" and child["nivel"] <= nivel:
                        break
                    if child["tipo"] == "leaf" and child.get("codigo", "").startswith(item["codigo"] + "."):
                        total += child.get("saldo", 0)
                    j += 1
                subtotal = {
                    "tipo": "subtotal",
                    "nombre": "Total " + item["nombre"],
                    "saldo": total,
                    "nivel": nivel,
                }
                items.insert(j, subtotal)
                i = j + 1
            else:
                i += 1

    return items


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

    def _es_padre_balanza(codigo):
        prefix = codigo + "."
        return any(c.startswith(prefix) for c in cuentas)

    def _calc_row(codigo):
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
        return {"debe": debe, "haber": haber, "saldo_debe": saldo_d, "saldo_haber": saldo_h}

    # Group by tipo, then process hierarchically within each
    for tipo in ("Activo", "Pasivo", "Capital", "Ingreso", "Gasto"):
        codes = sorted(c for c, info in cuentas.items() if info["tipo"] == tipo)

        # First pass: headers + leaves
        items = []
        for codigo in codes:
            info = cuentas[codigo]
            nivel = codigo.count(".")
            if _es_padre_balanza(codigo):
                items.append({"tipo": "header", "nombre": info["nombre"], "nivel": nivel, "codigo": codigo})
            else:
                items.append({"tipo": "leaf", "nombre": info["nombre"], "nivel": nivel, "codigo": codigo, "_row": _calc_row(codigo)})

        # Insert subtotals bottom-up — only at nivel 0 (type level)
        max_nivel = max((item["nivel"] for item in items), default=0)
        for nivel in range(max_nivel, -1, -1):
            i = 0
            while i < len(items):
                item = items[i]
                if item["tipo"] == "header" and item["nivel"] == nivel:
                    if nivel > 0:
                        i += 1
                        continue
                    total_d = 0; total_h = 0; total_sd = 0; total_sh = 0
                    j = i + 1
                    while j < len(items):
                        child = items[j]
                        if child["tipo"] == "header" and child["nivel"] <= nivel:
                            break
                        if child["tipo"] == "leaf" and child.get("codigo", "").startswith(item["codigo"] + "."):
                            r = child.get("_row", {})
                            total_d += r.get("debe", 0)
                            total_h += r.get("haber", 0)
                            total_sd += r.get("saldo_debe", 0)
                            total_sh += r.get("saldo_haber", 0)
                        j += 1
                    sub = {
                        "tipo": "subtotal",
                        "nombre": "Total " + item["nombre"],
                        "nivel": nivel,
                        "_row": {"debe": total_d, "haber": total_h, "saldo_debe": total_sd, "saldo_haber": total_sh},
                    }
                    items.insert(j, sub)
                    i = j + 1
                else:
                    i += 1

        # Flatten into balanza list (no subtotals — template handles type-level totals)
        for item in items:
            if item["tipo"] == "subtotal":
                continue
            r = item.get("_row", {"debe": 0, "haber": 0, "saldo_debe": 0, "saldo_haber": 0})
            balanza.append({
                "codigo": item.get("codigo", ""),
                "nombre": item["nombre"],
                "tipo": cuentas.get(item.get("codigo", ""), {}).get("tipo", "") if item["tipo"] == "leaf" else "",
                "debe": r["debe"],
                "haber": r["haber"],
                "saldo_debe": r["saldo_debe"],
                "saldo_haber": r["saldo_haber"],
                "es_header": item["tipo"] == "header",
                "es_subtotal": False,
                "nivel": item["nivel"],
            })
            if item["tipo"] != "header":
                total_debe += r["debe"]
                total_haber += r["haber"]
                total_saldo_d += r["saldo_debe"]
                total_saldo_h += r["saldo_haber"]

    return balanza, total_debe, total_haber, total_saldo_d, total_saldo_h


def calcular_estado_resultados(data):
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]

    def _saldo_ingreso(codigo, info):
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        return haber - debe

    def _saldo_gasto(codigo, info):
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        return debe - haber

    detalle_ingresos = _construir_lista_jerarquica(cuentas, mayor, "Ingreso", _saldo_ingreso)
    detalle_gastos = _construir_lista_jerarquica(cuentas, mayor, "Gasto", _saldo_gasto)

    total_ingresos = sum(item["saldo"] for item in detalle_ingresos if item["tipo"] == "leaf")
    total_gastos = sum(item["saldo"] for item in detalle_gastos if item["tipo"] == "leaf")
    utilidad = total_ingresos - total_gastos

    return detalle_ingresos, total_ingresos, detalle_gastos, total_gastos, utilidad


def calcular_balance_general(data):
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]
    _, _, _, _, utilidad = calcular_estado_resultados(data)

    def _saldo(codigo, info):
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        ts = tipo_saldo(info["tipo"])
        saldo = (debe - haber) if ts == "Debe" else (haber - debe)
        if codigo == "3.3.01":
            saldo += max(utilidad, 0)
        elif codigo == "3.3.02":
            saldo += max(-utilidad, 0)
        elif codigo == "3.4":
            # When using full data (no period filter), accumulated utility = total utility - current utility
            # For full data, utilidad_periodo = utilidad, so accumulated = 0
            pass
        return saldo

    activos = _construir_lista_jerarquica(cuentas, mayor, "Activo", _saldo)
    pasivos = _construir_lista_jerarquica(cuentas, mayor, "Pasivo", _saldo)
    capital_items = _construir_lista_jerarquica(cuentas, mayor, "Capital", _saldo)

    total_activo = sum(item["saldo"] for item in activos if item["tipo"] == "leaf")
    total_pasivo = sum(item["saldo"] for item in pasivos if item["tipo"] == "leaf")
    total_capital = sum(item["saldo"] for item in capital_items if item["tipo"] == "leaf")

    return activos, total_activo, pasivos, total_pasivo, capital_items, total_capital


def calcular_balance_general_con_utilidad(data, desde=None, hasta=None):
    """
    Calcula el Balance General separando:
    - 3.3.01 Utilidad del Ejercicio: Solo utilidad del período actual (desde-hasta)
    - 3.3.02 Utilidad Acumulada: Utilidad de períodos anteriores (antes de desde)
    """
    import copy
    
    # Calcular utilidad acumulada (antes del período actual)
    utilidad_acumulada = 0
    if desde:
        data_antes = copy.deepcopy(data)
        data_antes["diario"] = [e for e in data_antes.get("diario", []) if e.get("fecha", "") < desde]
        data_antes["ajustes"] = [a for a in data_antes.get("ajustes", []) if a.get("fecha", "") < desde]
        _, _, _, _, utilidad_acumulada = calcular_estado_resultados(data_antes)
    
    # Calcular utilidad del período actual
    utilidad_periodo = 0
    if hasta:
        data_periodo = copy.deepcopy(data)
        if desde:
            data_periodo["diario"] = [e for e in data_periodo.get("diario", []) if desde <= e.get("fecha", "") <= hasta]
            data_periodo["ajustes"] = [a for a in data_periodo.get("ajustes", []) if desde <= a.get("fecha", "") <= hasta]
        else:
            data_periodo["diario"] = [e for e in data_periodo.get("diario", []) if e.get("fecha", "") <= hasta]
            data_periodo["ajustes"] = [a for a in data_periodo.get("ajustes", []) if a.get("fecha", "") <= hasta]
        _, _, _, _, utilidad_periodo = calcular_estado_resultados(data_periodo)
    else:
        # Sin filtro, usar toda la utilidad
        _, _, _, _, utilidad_periodo = calcular_estado_resultados(data)
    
    # Calcular mayor con todos los datos hasta la fecha
    mayor = calcular_mayor(data)
    cuentas = data["cuentas"]

    def _saldo(codigo, info):
        debe = mayor[codigo]["debe"] if codigo in mayor else 0
        haber = mayor[codigo]["haber"] if codigo in mayor else 0
        ts = tipo_saldo(info["tipo"])
        saldo = (debe - haber) if ts == "Debe" else (haber - debe)
        
        if codigo == "3.3.01":
            # Utilidad del Ejercicio: Solo utilidad del período actual
            saldo += max(utilidad_periodo, 0)
        elif codigo == "3.3.02":
            # Pérdida del Ejercicio: Solo pérdida del período actual
            saldo += max(-utilidad_periodo, 0)
        elif codigo == "3.4":
            # Utilidad Acumulada: Utilidad de períodos anteriores
            saldo += max(utilidad_acumulada, 0)
        
        return saldo

    activos = _construir_lista_jerarquica(cuentas, mayor, "Activo", _saldo)
    pasivos = _construir_lista_jerarquica(cuentas, mayor, "Pasivo", _saldo)
    capital_items = _construir_lista_jerarquica(cuentas, mayor, "Capital", _saldo)

    total_activo = sum(item["saldo"] for item in activos if item["tipo"] == "leaf")
    total_pasivo = sum(item["saldo"] for item in pasivos if item["tipo"] == "leaf")
    total_capital = sum(item["saldo"] for item in capital_items if item["tipo"] == "leaf")

    return activos, total_activo, pasivos, total_pasivo, capital_items, total_capital


def get_ventas_por_dia(data):
    ventas = defaultdict(float)
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            cuenta = mov["cuenta"]
            if cuenta in ("4001", "4.1.01") and mov["tipo"] == "Haber":
                ventas[entry["fecha"]] += mov["monto"]
    return dict(sorted(ventas.items()))


def get_ventas_por_mes(data):
    ventas = defaultdict(float)
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            if mov["cuenta"] in ("4001", "4.1.01") and mov["tipo"] == "Haber":
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
        if not cod.startswith(("6", "5.2")):
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
    Prioridad: 3.3.02 (Pérdida del Ejercicio) > 3.1 (Capital Social).
    """
    for cod in ("3.3.02", "3.1"):
        if cod in data.get("cuentas", {}):
            return cod

    if crear_si_no_existe:
        data.setdefault("cuentas", {})["3.3.02"] = {
            "nombre": "Pérdida del Ejercicio",
            "tipo": "Capital",
            "saldo": 0
        }
        return "3.3.02"

    return "3.3.02"


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
