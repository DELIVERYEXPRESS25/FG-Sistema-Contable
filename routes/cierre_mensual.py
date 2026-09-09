from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for

from services.helpers import get_next_id
from services.auth import audit_log
from services.store import load_data, save_data, _periodos_disponibles_por_tipo, _obtener_rango_fechas
from services.calculos import (
    procesar_movimientos_periodo,
    validar_cierre_posible,
    calcular_movimientos_cierre,
    obtener_cuenta_capital_cierre,
)


cierre_mensual_bp = Blueprint("cierre_mensual", __name__)


@cierre_mensual_bp.route("/cierre-mensual", endpoint="cierre_mensual")
def cierre_mensual():
    data = load_data()
    cuentas = data["cuentas"]
    tipo = request.args.get("tipo", "mensual")
    if tipo not in ("mensual", "semanal", "quincenal"):
        tipo = "mensual"

    disponibles = _periodos_disponibles_por_tipo(data, tipo)
    cerrados = {c["periodo"] for c in data.get("cierres_mensuales", [])
                if c.get("tipo", "mensual") == tipo}

    periodos = []
    for p in disponibles:
        desde, hasta = _obtener_rango_fechas(tipo, p)
        ing = 0
        gast = 0
        for entry in data.get("diario", []):
            if desde <= entry["fecha"] <= hasta:
                if entry.get("ref", "").startswith("CIERRE-"):
                    continue
                for mov in entry["movimientos"]:
                    cta = data["cuentas"].get(mov["cuenta"], {})
                    if cta.get("tipo") == "Ingreso" and mov["tipo"] == "Haber":
                        ing += mov["monto"]
                    elif cta.get("tipo") == "Gasto" and mov["tipo"] == "Debe":
                        gast += mov["monto"]
        for aj in data.get("ajustes", []):
            if desde <= aj["fecha"] <= hasta:
                for mov in aj["movimientos"]:
                    cta = data["cuentas"].get(mov["cuenta"], {})
                    if cta.get("tipo") == "Ingreso" and mov["tipo"] == "Haber":
                        ing += mov["monto"]
                    elif cta.get("tipo") == "Gasto" and mov["tipo"] == "Debe":
                        gast += mov["monto"]

        result = ing - gast
        periodos.append({
            "periodo": p,
            "cerrado": p in cerrados,
            "total_ingresos": ing,
            "total_gastos": gast,
            "resultado": result,
            "cuentas": 1 if ing or gast else 0,
        })

    periodos.reverse()
    total_cerrados = sum(1 for c in data.get("cierres_mensuales", [])
                         if c.get("tipo", "mensual") == tipo)

    return render_template(
        "cierre_mensual.html",
        periodos=periodos,
        cuentas=cuentas,
        cerrados=cerrados,
        total_cerrados=total_cerrados,
        tipo_actual=tipo,
    )


@cierre_mensual_bp.route("/cierre-mensual/vista-previa/<tipo>/<periodo>", endpoint="cierre_mensual_vista_previa")
def cierre_mensual_vista_previa(tipo, periodo):
    """
    Muestra una vista previa del cierre antes de ejecutarlo.
    Permite al usuario validar los movimientos y totales.
    """
    data = load_data()
    cuentas = data["cuentas"]

    if tipo not in ("mensual", "semanal", "quincenal"):
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=periodo_invalido")

    cerrados = {c["periodo"] for c in data.get("cierres_mensuales", [])
                if c.get("tipo", "mensual") == tipo}
    if periodo in cerrados:
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=periodo_ya_cerrado")

    desde, hasta = _obtener_rango_fechas(tipo, periodo)

    saldos = procesar_movimientos_periodo(data, desde, hasta, excluir_cierre=True)

    cuentas_resultado = {}
    for cod, info in cuentas.items():
        if info.get("tipo") not in ("Ingreso", "Gasto"):
            continue

        saldo_data = saldos.get(cod, {"debe": 0, "haber": 0})
        debe = saldo_data["debe"]
        haber = saldo_data["haber"]

        if info.get("tipo") == "Ingreso":
            saldo = float(haber - debe)
        else:  # Gasto
            saldo = float(debe - haber)

        if saldo != 0:
            cuentas_resultado[cod] = {
                "nombre": info.get("nombre", cod),
                "tipo": info.get("tipo", ""),
                "debe": float(debe),
                "haber": float(haber),
                "saldo": saldo,
            }

    total_ingresos = sum(s["saldo"] for s in cuentas_resultado.values()
                         if s["tipo"] == "Ingreso")
    total_gastos = sum(s["saldo"] for s in cuentas_resultado.values()
                       if s["tipo"] == "Gasto")
    resultado = total_ingresos - total_gastos

    disponibles = _periodos_disponibles_por_tipo(data, tipo)
    cerrados_set = {c["periodo"] for c in data.get("cierres_mensuales", [])
                    if c.get("tipo", "mensual") == tipo}
    periodos = []
    for p in disponibles:
        d, h = _obtener_rango_fechas(tipo, p)
        ing = 0
        gast = 0
        for entry in data.get("diario", []):
            if d <= entry["fecha"] <= h:
                if entry.get("ref", "").startswith("CIERRE-"): continue
                for mov in entry["movimientos"]:
                    cta = data["cuentas"].get(mov["cuenta"], {})
                    if cta.get("tipo") == "Ingreso" and mov["tipo"] == "Haber": ing += mov["monto"]
                    elif cta.get("tipo") == "Gasto" and mov["tipo"] == "Debe": gast += mov["monto"]
        for aj in data.get("ajustes", []):
            if d <= aj["fecha"] <= h:
                for mov in aj["movimientos"]:
                    cta = data["cuentas"].get(mov["cuenta"], {})
                    if cta.get("tipo") == "Ingreso" and mov["tipo"] == "Haber": ing += mov["monto"]
                    elif cta.get("tipo") == "Gasto" and mov["tipo"] == "Debe": gast += mov["monto"]
        periodos.append({"periodo": p, "cerrado": p in cerrados,
                         "total_ingresos": ing, "total_gastos": gast,
                         "resultado": ing - gast, "cuentas": 1 if ing or gast else 0})
    periodos.reverse()
    total_cerrados = sum(1 for c in data.get("cierres_mensuales", [])
                         if c.get("tipo", "mensual") == tipo)

    return render_template(
        "cierre_mensual.html",
        periodos=periodos,
        cuentas=cuentas,
        cerrados=cerrados,
        total_cerrados=total_cerrados,
        tipo_actual=tipo,
        periodo_preview=periodo,
        cuentas_resultado=cuentas_resultado,
        total_ingresos=total_ingresos,
        total_gastos=total_gastos,
        resultado=resultado,
    )


@cierre_mensual_bp.route("/cierre-mensual/ejecutar", methods=["POST"], endpoint="cierre_mensual_ejecutar")
def cierre_mensual_ejecutar():
    """
    Ejecuta el cierre de un período (mensual, semanal o quincenal).
    Genera un asiento de cierre y registra la información del cierre.
    """
    data = load_data()
    periodo = request.form.get("periodo", "").strip()
    tipo = request.form.get("tipo", "mensual")

    if tipo not in ("mensual", "semanal", "quincenal"):
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=periodo_invalido")

    cerrados = {c["periodo"] for c in data.get("cierres_mensuales", [])
                if c.get("tipo", "mensual") == tipo}
    if periodo in cerrados:
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=periodo_ya_cerrado")

    desde, hasta = _obtener_rango_fechas(tipo, periodo)

    es_valido, error_msg = validar_cierre_posible(data, desde, hasta)
    if not es_valido:
        return redirect(url_for("cierre_mensual.cierre_mensual") + f"?error=sin_cuentas_resultado&tipo={tipo}")

    try:
        movs_cierre, total_ing, total_gast, diferencia = calcular_movimientos_cierre(data, desde, hasta)
    except Exception as e:
        return redirect(url_for("cierre_mensual.cierre_mensual") + f"?error=calculo_error&tipo={tipo}")

    if not movs_cierre:
        return redirect(url_for("cierre_mensual.cierre_mensual") + f"?error=sin_cuentas_resultado&tipo={tipo}")

    if abs(diferencia) > 0.01:
        cta_capital = obtener_cuenta_capital_cierre(data, crear_si_no_existe=True)
        diferencia = round(diferencia, 2)
        if diferencia > 0:
            movs_cierre.append({"cuenta": cta_capital, "tipo": "Haber", "monto": diferencia})
        else:
            movs_cierre.append({"cuenta": cta_capital, "tipo": "Debe", "monto": abs(diferencia)})

    ref_cierre = f"CIERRE-{tipo.upper()[:4]}-{periodo}"
    asiento = {
        "id": get_next_id(data, "diario"),
        "fecha": hasta,
        "descripcion": f"Cierre {tipo} - {periodo}",
        "ref": ref_cierre,
        "movimientos": movs_cierre,
    }
    data["diario"].append(asiento)

    data.setdefault("cierres_mensuales", []).append({
        "tipo": tipo,
        "periodo": periodo,
        "fecha_cierre": date.today().isoformat(),
        "asiento_id": asiento["id"],
        "total_ingresos": total_ing,
        "total_gastos": total_gast,
        "usuario": "sistema",  # Para auditoría futura
    })

    data = audit_log(data, "cierre_mensual", f"Cierre {tipo} {periodo} — resultado C${diferencia:.2f}")
    save_data(data)
    return redirect(url_for("cierre_mensual.cierre_mensual") + f"?ok=cierre_{periodo}&tipo={tipo}")


@cierre_mensual_bp.route("/cierre-mensual/revertir/<tipo>/<periodo>", methods=["POST"], endpoint="cierre_mensual_revertir")
def cierre_mensual_revertir(tipo, periodo):
    """
    Revierte un cierre de período: elimina el asiento de cierre y el registro del cierre.
    """
    if tipo not in ("mensual", "semanal", "quincenal"):
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=periodo_invalido")

    data = load_data()

    cierre_idx = None
    for i, c in enumerate(data.get("cierres_mensuales", [])):
        if c["periodo"] == periodo and c.get("tipo", "mensual") == tipo:
            cierre_idx = i
            break

    if cierre_idx is None:
        return redirect(url_for("cierre_mensual.cierre_mensual") + "?error=cierre_no_encontrado")

    cierre_info = data["cierres_mensuales"][cierre_idx]
    asiento_id = cierre_info.get("asiento_id")

    if asiento_id is not None:
        data["diario"] = [e for e in data["diario"] if e.get("id") != asiento_id]

    data["cierres_mensuales"].pop(cierre_idx)

    data = audit_log(data, "revertir_cierre", f"Revertir cierre {tipo} {periodo}")
    save_data(data)
    return redirect(url_for("cierre_mensual.cierre_mensual") + f"?ok=cierre_revertido&tipo={tipo}")