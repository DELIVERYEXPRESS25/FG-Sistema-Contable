from io import BytesIO
from flask import Blueprint, render_template, request, send_file

from services.auth import login_required
from services.store import load_data, _paginar, _mayor_cached
from services.calculos import (
    calcular_balanza,
    calcular_estado_resultados,
    calcular_balance_general,
)


reportes_pdf_bp = Blueprint("reportes_pdf", __name__)


def _send_pdf(pdf_func, data, filename, desde=None, hasta=None):
    from services.reportes_pdf import generar_pdf_bytes

    buf = BytesIO()
    buf.write(generar_pdf_bytes(pdf_func, data, desde, hasta))
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


def _desde_hasta():
    d = request.args.get("desde", "")
    h = request.args.get("hasta", "")
    return (d, h) if d and h else (None, None)


@reportes_pdf_bp.route("/reportes", endpoint="reportes")
def reportes():
    data = load_data()
    mayor = _mayor_cached(data)
    _, td, th, tsd, tsh = calcular_balanza(data)
    di, ti, dg, tg, util = calcular_estado_resultados(data)
    activos, ta, pasivos, tp, capital, tc = calcular_balance_general(data)
    entries = data.get("auditoria", [])[:]
    entries.reverse()
    page = request.args.get("auditoria_page", 1, type=int)
    page_entries, aud_page, aud_total_pages, aud_total = _paginar(entries, page, 50)
    fechas = set()
    for e in data.get("diario", []):
        f = e.get("fecha", "")
        if len(f) >= 7:
            fechas.add(f[:7])
    meses = sorted(fechas, reverse=True)
    return render_template(
        "reportes.html",
        diario=data["diario"],
        cuentas=data["cuentas"],
        mayor=mayor,
        balanza_td=td, balanza_th=th, balanza_tsd=tsd, balanza_tsh=tsh,
        detalle_ingresos=di, total_ingresos=ti,
        detalle_gastos=dg, total_gastos=tg, utilidad=util,
        activos=activos, total_activo=ta,
        pasivos=pasivos, total_pasivo=tp,
        capital=capital, total_capital=tc,
        kardex=data["kardex"],
        pos_historial=data.get("pos_historial", []),
        auditoria_entries=page_entries, auditoria_page=aud_page,
        auditoria_total_pages=aud_total_pages, auditoria_total=aud_total,
        meses=meses,
    )


@reportes_pdf_bp.route("/reportes/pdf/balanza", endpoint="pdf_balanza")
@login_required
def pdf_balanza():
    from services.reportes_pdf import pdf_balanza as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Balanza.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/estado-resultados", endpoint="pdf_estado_resultados")
@login_required
def pdf_estado_resultados():
    from services.reportes_pdf import pdf_estado_resultados as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Estado_Resultados.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/balance-general", endpoint="pdf_balance_general")
@login_required
def pdf_balance_general():
    from services.reportes_pdf import pdf_balance_general as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Balance_General.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/diario", endpoint="pdf_diario")
@login_required
def pdf_diario():
    from services.reportes_pdf import pdf_diario as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Libro_Diario.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/mayor", endpoint="pdf_mayor")
@login_required
def pdf_mayor():
    from services.reportes_pdf import pdf_mayor as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Libro_Mayor.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/cobrar", endpoint="pdf_cobrar")
@login_required
def pdf_cobrar():
    from services.reportes_pdf import pdf_cobrar as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Cuentas_Cobrar.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/caja", endpoint="pdf_caja")
@login_required
def pdf_caja():
    from services.reportes_pdf import pdf_caja as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Movimientos_Caja.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/completo", endpoint="pdf_completo")
@login_required
def pdf_completo():
    from services.reportes_pdf import pdf_completo as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Reporte_Completo.pdf", d, h)


@reportes_pdf_bp.route("/reportes/pdf/antiguedad-cobros", endpoint="pdf_antiguedad_cobros")
@login_required
def pdf_antiguedad_cobros():
    from services.reportes_pdf import pdf_antiguedad_cobros as fn

    d, h = _desde_hasta()
    return _send_pdf(fn, load_data(), "Antiguedad_Cobros.pdf", d, h)