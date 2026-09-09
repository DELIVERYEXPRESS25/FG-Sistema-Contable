from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for

from services.helpers import get_next_id
from services.auth import audit_log
from services.store import load_data, save_data, _periodo_cerrado


ajustes_bp = Blueprint("ajustes", __name__)


@ajustes_bp.route("/ajustes", endpoint="ajustes")
def ajustes():
    data = load_data()
    margen_config = data.get("configuracion", {}).get("margen_default", 30)
    return render_template(
        "ajustes.html",
        ajustes=data.get("ajustes", []),
        cuentas=data["cuentas"],
        margen_config=margen_config,
    )


@ajustes_bp.route("/ajustes/guardar_margen", methods=["POST"], endpoint="guardar_margen")
def guardar_margen():
    data = load_data()
    margen = float(request.form.get("margen", 30))
    if margen < 0 or margen >= 100:
        margen = 30
    data.setdefault("configuracion", {})["margen_default"] = margen
    save_data(data)
    return redirect(url_for("ajustes.ajustes") + "?ok=margen")


@ajustes_bp.route("/ajustes/agregar", methods=["POST"], endpoint="agregar_ajuste")
def agregar_ajuste():
    data = load_data()
    fecha = request.form.get("fecha", date.today().isoformat())

    if _periodo_cerrado(data, fecha):
        return redirect(url_for("ajustes.ajustes") + "?error=mes_cerrado")

    descripcion = request.form.get("descripcion", "")
    cuentas_sel = request.form.getlist("cuenta")
    tipos = request.form.getlist("tipo")
    montos = request.form.getlist("monto")
    movimientos = []
    for i in range(len(cuentas_sel)):
        if cuentas_sel[i] and montos[i]:
            monto = float(montos[i])
            if monto <= 0:
                continue
            movimientos.append(
                {"cuenta": cuentas_sel[i], "tipo": tipos[i], "monto": monto}
            )
    if movimientos:
        total_debe = sum(m["monto"] for m in movimientos if m["tipo"] == "Debe")
        total_haber = sum(m["monto"] for m in movimientos if m["tipo"] == "Haber")
        if abs(total_debe - total_haber) > 0.01 or total_debe == 0 or total_haber == 0:
            return redirect(url_for("ajustes.ajustes") + "?error=asiento_desbalanceado")

        data.setdefault("ajustes", []).append(
            {
                "id": get_next_id(data, "ajustes"),
                "fecha": fecha,
                "descripcion": descripcion,
                "movimientos": movimientos,
            }
        )
        data = audit_log(data, "crear_ajuste", f"Ajuste #{data['ajustes'][-1]['id']} — {descripcion[:60]}")
        save_data(data)
    return redirect(url_for("ajustes.ajustes"))