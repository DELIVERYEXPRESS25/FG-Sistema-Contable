import copy
from flask import Blueprint, render_template, request

from services.store import load_data
from services.calculos import (
    calcular_mayor,
    calcular_balanza,
    calcular_estado_resultados,
    calcular_balance_general,
    meses_disponibles,
)


reportes_core_bp = Blueprint("reportes_core", __name__)


@reportes_core_bp.route("/mayor", endpoint="mayor")
def mayor():
    try:
        data = load_data()
        mayor_data = calcular_mayor(data)
        return render_template("mayor.html", mayor=mayor_data, cuentas=data["cuentas"])
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"<pre>ERROR /mayor: {e}</pre>", 500


@reportes_core_bp.route("/balanza", endpoint="balanza")
def balanza():
    try:
        data = load_data()
        meses = meses_disponibles(data)
        periodo = request.args.get("periodo", "")

        def _calcular_balanza_tipo(d):
            bal, td, th, tsd, tsh = calcular_balanza(d)
            tipos_totales = {}
            for row in bal:
                if not row["es_header"] and not row["es_subtotal"] and row["tipo"]:
                    t = row["tipo"]
                    if t not in tipos_totales:
                        tipos_totales[t] = {"debe": 0, "haber": 0, "saldo_debe": 0, "saldo_haber": 0}
                    tipos_totales[t]["debe"] += row["debe"]
                    tipos_totales[t]["haber"] += row["haber"]
                    tipos_totales[t]["saldo_debe"] += row["saldo_debe"]
                    tipos_totales[t]["saldo_haber"] += row["saldo_haber"]
            return bal, td, th, tsd, tsh, tipos_totales

        if periodo:
            data_filtrada = copy.deepcopy(data)
            data_filtrada["diario"] = [e for e in data["diario"] if e["fecha"][:7] == periodo]
            data_filtrada["ajustes"] = [a for a in data.get("ajustes", []) if a["fecha"][:7] == periodo]
            balanza_data, td, th, tsd, tsh, tipos_totales = _calcular_balanza_tipo(data_filtrada)

            idx = meses.index(periodo) if periodo in meses else -1
            periodo_anterior = meses[idx - 1] if idx > 0 else ""
            if periodo_anterior:
                data_ant = copy.deepcopy(data)
                data_ant["diario"] = [e for e in data["diario"] if e["fecha"][:7] == periodo_anterior]
                data_ant["ajustes"] = [a for a in data.get("ajustes", []) if a["fecha"][:7] == periodo_anterior]
                balanza_ant, td_a, th_a, tsd_a, tsh_a, _ = _calcular_balanza_tipo(data_ant)
            else:
                balanza_ant = []
                td_a = th_a = tsd_a = tsh_a = 0
                periodo_anterior = ""
        else:
            balanza_data, td, th, tsd, tsh, tipos_totales = _calcular_balanza_tipo(data)
            balanza_ant = []
            td_a = th_a = tsd_a = tsh_a = 0
            periodo_anterior = ""

        return render_template(
            "balanza.html",
            balanza=balanza_data,
            balanza_anterior=balanza_ant,
            total_debe=td,
            total_haber=th,
            total_saldo_debe=tsd,
            total_saldo_haber=tsh,
            total_debe_ant=td_a,
            total_haber_ant=th_a,
            meses=meses,
            periodo_actual=periodo,
            periodo_anterior=periodo_anterior,
            tipos_totales=tipos_totales,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"<pre>ERROR /balanza: {e}</pre>", 500


@reportes_core_bp.route("/estado_resultados", endpoint="estado_resultados")
def estado_resultados():
    try:
        data = load_data()
        di, ti, dg, tg, util = calcular_estado_resultados(data)
        return render_template(
            "estado_resultados.html",
            detalle_ingresos=di,
            total_ingresos=ti,
            detalle_gastos=dg,
            total_gastos=tg,
            utilidad=util,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"<pre>ERROR /estado_resultados: {e}</pre>", 500


@reportes_core_bp.route("/balance_general", endpoint="balance_general")
def balance_general():
    try:
        data = load_data()
        activos, ta, pasivos, tp, capital, tc = calcular_balance_general(data)
        return render_template(
            "balance_general.html",
            activos=activos,
            total_activo=ta,
            pasivos=pasivos,
            total_pasivo=tp,
            capital=capital,
            total_capital=tc,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return f"<pre>ERROR /balance_general: {e}</pre>", 500