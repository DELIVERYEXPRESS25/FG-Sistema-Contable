from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for

from services.helpers import get_next_id
from services.auth import audit_log
from services.store import load_data, save_data, _paginar, _periodo_cerrado


diario_bp = Blueprint("diario", __name__)


@diario_bp.route("/diario", endpoint="diario")
def diario():
    data = load_data()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = request.args.get("search", "").strip()
    per_page = min(per_page, 200)

    entries = data["diario"]
    if search:
        search_lower = search.lower()
        filtered = []
        for e in entries:
            if search_lower in e.get("descripcion", "").lower() or \
               search_lower in e.get("ref", "").lower() or \
               search_lower in e.get("fecha", ""):
                filtered.append(e)
        entries = filtered
    page_entries, page, total_pages, total = _paginar(entries, page, per_page)
    return render_template(
        "diario.html", diario=page_entries, cuentas=data["cuentas"],
        page=page, total_pages=total_pages, total_entries=total,
        search=search, per_page=per_page,
    )


@diario_bp.route("/diario/agregar", methods=["POST"], endpoint="agregar_diario")
def agregar_diario():
    data = load_data()
    fecha = request.form.get("fecha", date.today().isoformat())

    if _periodo_cerrado(data, fecha):
        return redirect(url_for("diario.diario") + "?error=mes_cerrado")

    descripcion = request.form.get("descripcion", "")
    ref = request.form.get("ref", "")
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
            return redirect(url_for("diario.diario") + "?error=asiento_desbalanceado")

        entry = {
            "id": get_next_id(data, "diario"),
            "fecha": fecha,
            "descripcion": descripcion,
            "ref": ref,
            "movimientos": movimientos,
        }
        data["diario"].append(entry)
        for mov in movimientos:
            if mov["cuenta"] in ("1003", "1.1.03") and mov["tipo"] == "Debe":
                data["cuentas_cobrar"].append(
                    {
                        "id": get_next_id(data, "cuentas_cobrar"),
                        "fecha": fecha,
                        "descripcion": descripcion,
                        "monto": mov["monto"],
                        "estado": "Pendiente",
                        "ref_diario": entry["id"],
                    }
                )
            if mov["cuenta"] in ("1001", "1002", "1.1.01", "1.1.02"):
                data["caja_movimientos"].append(
                    {
                        "id": get_next_id(data, "caja_movimientos"),
                        "fecha": fecha,
                        "descripcion": descripcion,
                        "tipo": mov["tipo"],
                        "monto": mov["monto"],
                        "cuenta": mov["cuenta"],
                        "ref_diario": entry["id"],
                    }
                )
        data = audit_log(data, "crear_asiento", f"Asiento #{entry.get('id','?')} — {descripcion[:60]}")
        save_data(data)
    return redirect(url_for("diario.diario"))


@diario_bp.route("/diario/editar/<int:asiento_id>", methods=["GET", "POST"], endpoint="editar_asiento")
def editar_asiento(asiento_id):
    data = load_data()

    if request.method == "GET":
        asiento = None
        for a in data["diario"]:
            if a.get("id") == asiento_id:
                asiento = a
                break

        if not asiento:
            return redirect(url_for("diario.diario"))

        movimientos_form = []
        for mov in asiento.get("movimientos", []):
            debe = (
                mov.get("debe", 0)
                if "debe" in mov
                else (mov.get("monto", 0) if mov.get("tipo") == "Debe" else 0)
            )
            haber = (
                mov.get("haber", 0)
                if "haber" in mov
                else (mov.get("monto", 0) if mov.get("tipo") == "Haber" else 0)
            )

            movimientos_form.append(
                {"cuenta": mov.get("cuenta", ""), "debe": debe, "haber": haber}
            )

        return render_template(
            "diario_editar.html",
            asiento=asiento,
            movimientos=movimientos_form,
            cuentas=data["cuentas"],
        )

    else:  # POST - guardar cambios
        if _periodo_cerrado(data, request.form.get("fecha", date.today().isoformat())):
            return redirect(url_for("diario.diario") + "?error=mes_cerrado")

        idx = None
        for i, a in enumerate(data["diario"]):
            if a.get("id") == asiento_id:
                idx = i
                break

        if idx is None:
            return redirect(url_for("diario.diario"))

        fecha = request.form.get("fecha", date.today().isoformat())
        descripcion = request.form.get("descripcion", "")
        ref = request.form.get("ref", "")

        cuentas_sel = request.form.getlist("cuenta")
        debes = request.form.getlist("debe")
        haberes = request.form.getlist("haber")

        movimientos = []
        for i in range(len(cuentas_sel)):
            if cuentas_sel[i]:
                debe = float(debes[i]) if debes[i] else 0
                haber = float(haberes[i]) if haberes[i] else 0

                if debe > 0:
                    movimientos.append(
                        {"cuenta": cuentas_sel[i], "tipo": "Debe", "monto": debe}
                    )
                if haber > 0:
                    movimientos.append(
                        {"cuenta": cuentas_sel[i], "tipo": "Haber", "monto": haber}
                    )

        total_debe = sum(m["monto"] for m in movimientos if m["tipo"] == "Debe")
        total_haber = sum(m["monto"] for m in movimientos if m["tipo"] == "Haber")
        if round(total_debe, 2) != round(total_haber, 2) or total_debe == 0:
            return redirect(url_for("diario.diario"))

        if movimientos:
            data["diario"][idx] = {
                "id": asiento_id,
                "fecha": fecha,
                "descripcion": descripcion,
                "ref": ref,
                "movimientos": movimientos,
            }
            data = audit_log(data, "editar_asiento", f"Asiento #{asiento_id} editado")
            save_data(data)

        return redirect(url_for("diario.diario"))


@diario_bp.route("/diario/borrar/<int:asiento_id>", methods=["POST"], endpoint="borrar_asiento")
def borrar_asiento(asiento_id):
    data = load_data()

    for a in data["diario"]:
        if a.get("id") == asiento_id:
            if _periodo_cerrado(data, a.get("fecha", "")):
                return redirect(url_for("diario.diario") + "?error=mes_cerrado")
            break

    data["diario"] = [a for a in data["diario"] if a.get("id") != asiento_id]

    data = audit_log(data, "borrar_asiento", f"Asiento #{asiento_id} borrado")
    save_data(data)
    return redirect(url_for("diario.diario"))