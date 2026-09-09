from flask import Blueprint, render_template, request, send_file
from io import BytesIO

from services.auth import login_required
from services.store import load_data


fiscales_bp = Blueprint("fiscales", __name__)


def _meses_disponibles(data):
    fechas = set()
    for e in data.get("diario", []):
        f = e.get("fecha", "")
        if len(f) >= 7:
            fechas.add(f[:7])
    return sorted(fechas, reverse=True)


def _calcular_ingresos_gastos(data, desde, hasta):
    saldos = {}
    for cod in data.get("cuentas", {}):
        saldos[cod] = {"debe": 0, "haber": 0}
    for e in data.get("diario", []):
        if e.get("fecha", "") >= desde and e.get("fecha", "") <= hasta and not e.get("ref", "").startswith("CIERRE-"):
            for m in e.get("movimientos", []):
                if m["tipo"] == "Debe":
                    saldos[m["cuenta"]]["debe"] += m["monto"]
                else:
                    saldos[m["cuenta"]]["haber"] += m["monto"]
    for aj in data.get("ajustes", []):
        if aj.get("fecha", "") >= desde and aj.get("fecha", "") <= hasta:
            for m in aj.get("movimientos", []):
                if m["tipo"] == "Debe":
                    saldos[m["cuenta"]]["debe"] += m["monto"]
                else:
                    saldos[m["cuenta"]]["haber"] += m["monto"]
    total_ing = 0.0
    total_gas = 0.0
    for cod, info in data.get("cuentas", {}).items():
        if info["tipo"] == "Ingreso":
            total_ing += saldos[cod]["haber"] - saldos[cod]["debe"]
        elif info["tipo"] == "Gasto":
            total_gas += saldos[cod]["debe"] - saldos[cod]["haber"]
    return total_ing, total_gas


@fiscales_bp.route("/fiscales", endpoint="fiscales")
@login_required
def fiscales():
    data = load_data()
    return render_template("fiscales.html", meses=_meses_disponibles(data))


@fiscales_bp.route("/fiscales/iva", endpoint="fiscal_iva")
@login_required
def fiscal_iva():
    data = load_data()
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    total_ing = total_gas = iva_deb = iva_cred = iva_pagar = None
    if desde and hasta:
        total_ing, total_gas = _calcular_ingresos_gastos(data, desde, hasta)
        iva_deb = round(total_ing * 0.15, 2)
        iva_cred = round(total_gas * 0.15, 2)
        iva_pagar = round(iva_deb - iva_cred, 2)
    return render_template("fiscal_iva.html", data=data, desde=desde, hasta=hasta,
                           total_ing=total_ing, total_gas=total_gas,
                           iva_deb=iva_deb, iva_cred=iva_cred, iva_pagar=iva_pagar)


@fiscales_bp.route("/fiscales/iva/pdf", endpoint="fiscal_iva_pdf")
@login_required
def fiscal_iva_pdf():
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    from services.reportes_pdf import pdf_reporte_iva, generar_pdf_bytes_con_periodo

    buf = BytesIO()
    buf.write(generar_pdf_bytes_con_periodo(pdf_reporte_iva, load_data(), desde, hasta))
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=f"IVA_{desde}_a_{hasta}.pdf")


@fiscales_bp.route("/fiscales/dgi", endpoint="fiscal_dgi")
@login_required
def fiscal_dgi():
    data = load_data()
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    total_ing = total_gas = utilidad = ir_estimado = None
    if desde and hasta:
        total_ing, total_gas = _calcular_ingresos_gastos(data, desde, hasta)
        utilidad = round(total_ing - total_gas, 2)
        ir_estimado = round(utilidad * 0.30, 2) if utilidad > 0 else 0
    return render_template("fiscal_dgi.html", data=data, desde=desde, hasta=hasta,
                           total_ing=total_ing, total_gas=total_gas,
                           utilidad=utilidad, ir_estimado=ir_estimado)


@fiscales_bp.route("/fiscales/alcaldia", endpoint="fiscal_alcaldia")
@login_required
def fiscal_alcaldia():
    data = load_data()
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    total_ing = impuesto_alc = None
    if desde and hasta:
        total_ing, _ = _calcular_ingresos_gastos(data, desde, hasta)
        impuesto_alc = round(total_ing * 0.01, 2)
    return render_template("fiscal_alcaldia.html", data=data, desde=desde, hasta=hasta,
                           total_ing=total_ing, impuesto_alc=impuesto_alc)