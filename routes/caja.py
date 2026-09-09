from collections import defaultdict
from flask import Blueprint, render_template, request

from services.helpers import tipo_saldo
from services.store import load_data, _paginar


caja_bp = Blueprint("caja", __name__)


@caja_bp.route("/caja", endpoint="caja")
def caja():
    data = load_data()

    movs = data.get("caja_movimientos", []) or data.get("caja", [])
    saldo = 0
    for m in movs:
        if m.get("tipo") == "Debe":
            saldo += m.get("monto", 0)
        else:
            saldo -= m.get("monto", 0)

    page = request.args.get("page", 1, type=int)
    per_page = 50
    start = (page - 1) * per_page

    saldo_inicial = 0
    for m in movs[:start]:
        if m.get("tipo") == "Debe":
            saldo_inicial += m.get("monto", 0)
        else:
            saldo_inicial -= m.get("monto", 0)

    movs_pag, page, total_pages, total = _paginar(movs, page)
    return render_template(
        "caja.html",
        movimientos=movs_pag,
        saldo=saldo,
        page=page,
        total_pages=total_pages,
        total=total,
        saldo_inicial=saldo_inicial,
    )


@caja_bp.route("/auxiliar-diario", endpoint="auxiliar_diario")
def auxiliar_diario():
    data = load_data()
    cuentas = data["cuentas"]

    movs_planos = []
    for entry in data["diario"]:
        for mov in entry["movimientos"]:
            movs_planos.append(
                {
                    "asiento_id": entry["id"],
                    "fecha": entry["fecha"],
                    "descripcion": entry["descripcion"],
                    "ref": entry.get("ref", ""),
                    "cuenta": mov["cuenta"],
                    "nombre_cuenta": cuentas.get(mov["cuenta"], {}).get("nombre", mov["cuenta"]),
                    "tipo": mov["tipo"],
                    "monto": mov["monto"],
                    "tipo_cuenta": cuentas.get(mov["cuenta"], {}).get("tipo", ""),
                }
            )
    aj_id = -1
    for aj in data.get("ajustes", []):
        for mov in aj["movimientos"]:
            movs_planos.append(
                {
                    "asiento_id": aj_id,
                    "fecha": aj["fecha"],
                    "descripcion": aj["descripcion"],
                    "ref": "AJ",
                    "cuenta": mov["cuenta"],
                    "nombre_cuenta": cuentas.get(mov["cuenta"], {}).get("nombre", mov["cuenta"]),
                    "tipo": mov["tipo"],
                    "monto": mov["monto"],
                    "tipo_cuenta": cuentas.get(mov["cuenta"], {}).get("tipo", ""),
                }
            )
            aj_id -= 1

    saldos_cuenta = defaultdict(float)
    for m in movs_planos:
        ts = tipo_saldo(m["tipo_cuenta"])
        if ts == "Debe":
            saldos_cuenta[m["cuenta"]] += m["monto"] if m["tipo"] == "Debe" else -m["monto"]
        else:
            saldos_cuenta[m["cuenta"]] += m["monto"] if m["tipo"] == "Haber" else -m["monto"]

    movs_con_saldo = []
    saldo_run = defaultdict(float)
    for m in movs_planos:
        cuenta = m["cuenta"]
        ts = tipo_saldo(m["tipo_cuenta"])
        if ts == "Debe":
            saldo_run[cuenta] += m["monto"] if m["tipo"] == "Debe" else -m["monto"]
        else:
            saldo_run[cuenta] += m["monto"] if m["tipo"] == "Haber" else -m["monto"]
        m["saldo_cuenta"] = saldo_run[cuenta]
        movs_con_saldo.append(m)

    movs_con_saldo.sort(key=lambda x: (x["fecha"], x["asiento_id"]), reverse=True)

    cuentas_con_mov = sorted(set(m["cuenta"] for m in movs_con_saldo))
    total_debe = sum(m["monto"] for m in movs_con_saldo if m["tipo"] == "Debe")
    total_haber = sum(m["monto"] for m in movs_con_saldo if m["tipo"] == "Haber")

    sumario_ctas = {}
    for m in movs_con_saldo:
        c = m["cuenta"]
        if c not in sumario_ctas:
            sumario_ctas[c] = {"debe": 0.0, "haber": 0.0, "movs": 0}
        if m["tipo"] == "Debe":
            sumario_ctas[c]["debe"] += m["monto"]
        else:
            sumario_ctas[c]["haber"] += m["monto"]
        sumario_ctas[c]["movs"] += 1

    return render_template(
        "auxiliar_diario.html",
        movimientos=movs_con_saldo,
        cuentas=cuentas,
        cuentas_con_mov=cuentas_con_mov,
        sumario_ctas=sumario_ctas,
        saldos_cuenta=dict(saldos_cuenta),
        total_debe=total_debe,
        total_haber=total_haber,
        total_asientos=len(data["diario"]) + len(data.get("ajustes", [])),
        total_movs=len(movs_con_saldo),
    )