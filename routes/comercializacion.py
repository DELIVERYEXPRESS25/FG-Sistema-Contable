from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for

from services.helpers import get_next_id
from services.auth import audit_log
from services.store import load_data, save_data
from services.calculos import calcular_mayor, calcular_total_comercializacion


comercializacion_bp = Blueprint("comercializacion", __name__)


@comercializacion_bp.route("/comercializacion", endpoint="comercializacion")
def comercializacion():
    data = load_data()
    mayor = calcular_mayor(data)

    movimientos = []
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            if mov["cuenta"].startswith("6"):
                movimientos.append(
                    {
                        "id": entry["id"],
                        "fecha": entry["fecha"],
                        "ref": entry.get("ref", ""),
                        "descripcion": entry["descripcion"],
                        "cuenta": mov["cuenta"],
                        "nombre_cuenta": data["cuentas"]
                        .get(mov["cuenta"], {})
                        .get("nombre", mov["cuenta"]),
                        "tipo": mov["tipo"],
                        "monto": mov["monto"],
                    }
                )
    movimientos.sort(key=lambda x: x["fecha"], reverse=True)

    detalle, total = calcular_total_comercializacion(data)

    cuentas_6 = {
        cod: info
        for cod, info in data["cuentas"].items()
        if cod.startswith(("5.2", "6")) and info.get("tipo") == "Gasto"
    }
    todas_cuentas = data["cuentas"]

    return render_template(
        "comercializacion.html",
        movimientos=movimientos,
        detalle=detalle,
        total=total,
        cuentas_6=cuentas_6,
        todas_cuentas=todas_cuentas,
        mayor=mayor,
    )


@comercializacion_bp.route("/comercializacion/registrar", methods=["POST"], endpoint="comercializacion_registrar")
def comercializacion_registrar():
    """Registra un gasto de comercialización como asiento en el diario."""
    data = load_data()
    fecha = request.form.get("fecha", date.today().isoformat())
    descripcion = request.form.get("descripcion", "")
    ref = request.form.get("ref", "")
    cuenta_gasto = request.form.get("cuenta_gasto", "")
    cuenta_pago = request.form.get("cuenta_pago", "")
    monto_str = request.form.get("monto", "0")

    try:
        monto = float(monto_str)
    except ValueError:
        return redirect(url_for("comercializacion.comercializacion"))

    if not cuenta_gasto or not cuenta_pago or monto <= 0:
        return redirect(url_for("comercializacion.comercializacion"))

    entry = {
        "id": get_next_id(data, "diario"),
        "fecha": fecha,
        "descripcion": descripcion
        or f"Gasto de comercialización — {data['cuentas'].get(cuenta_gasto, {}).get('nombre', cuenta_gasto)}",
        "ref": ref,
        "movimientos": [
            {"cuenta": cuenta_gasto, "tipo": "Debe", "monto": monto},
            {"cuenta": cuenta_pago, "tipo": "Haber", "monto": monto},
        ],
    }
    data["diario"].append(entry)

    if cuenta_pago in ("1001", "1002", "1.1.01", "1.1.02"):
        data["caja_movimientos"].append(
            {
                "id": get_next_id(data, "caja_movimientos"),
                "fecha": fecha,
                "descripcion": entry["descripcion"],
                "tipo": "Haber",
                "monto": monto,
                "cuenta": cuenta_pago,
                "ref_diario": entry["id"],
            }
        )

    data = audit_log(data, "gasto_comercializacion", f"{descripcion[:60]} — C${monto:.2f}")
    save_data(data)
    return redirect(url_for("comercializacion.comercializacion"))


@comercializacion_bp.route("/comercializacion/cuenta/nueva", methods=["POST"], endpoint="comercializacion_cuenta_nueva")
def comercializacion_cuenta_nueva():
    """Agrega una nueva cuenta de comercialización al catálogo."""
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    if codigo and nombre and codigo not in data["cuentas"]:
        data["cuentas"][codigo] = {"nombre": nombre, "tipo": "Gasto", "saldo": 0}
        save_data(data)
    return redirect(url_for("comercializacion.comercializacion"))


@comercializacion_bp.route("/comercializacion/cuenta/eliminar", methods=["POST"], endpoint="comercializacion_cuenta_eliminar")
def comercializacion_cuenta_eliminar():
    """Elimina una cuenta 6xxx del catálogo (solo si no tiene movimientos)."""
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    mayor = calcular_mayor(data)
    if codigo.startswith("6") and codigo in data["cuentas"]:
        tiene_mov = codigo in mayor and (
            mayor[codigo]["debe"] > 0 or mayor[codigo]["haber"] > 0
        )
        if not tiene_mov:
            del data["cuentas"][codigo]
            save_data(data)
    return redirect(url_for("comercializacion.comercializacion"))