from flask import Blueprint, render_template, request, redirect, url_for

from services.auth import audit_log
from services.store import load_data, save_data, CUENTAS_BASE


catalogar_bp = Blueprint("catalogar", __name__)


@catalogar_bp.route("/cuentas/nueva", methods=["POST"], endpoint="nueva_cuenta")
def nueva_cuenta():
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "Activo")
    if codigo and nombre and codigo not in data["cuentas"]:
        data["cuentas"][codigo] = {"nombre": nombre, "tipo": tipo, "saldo": 0}
        save_data(data)
    return redirect(request.referrer or url_for("index"))


@catalogar_bp.route("/catalogar", endpoint="catalogar")
def catalogar():
    data = load_data()
    cuentas = sorted(data["cuentas"].items(), key=lambda x: x[0])
    return render_template("catalogar.html", cuentas=cuentas)


@catalogar_bp.route("/catalogar/nueva", methods=["POST"], endpoint="catalogar_nueva")
def catalogar_nueva():
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "Activo")
    if not codigo or not nombre:
        return redirect(url_for("catalogar.catalogar") + "?error=codigo_invalido")
    if codigo in data["cuentas"]:
        return redirect(url_for("catalogar.catalogar") + "?error=codigo_invalido")
    data["cuentas"][codigo] = {"nombre": nombre, "tipo": tipo, "saldo": 0}
    data = audit_log(data, "crear_cuenta", f"Cuenta {codigo} — {nombre}")
    save_data(data)
    return redirect(url_for("catalogar.catalogar") + "?ok=cuenta_guardada")


@catalogar_bp.route("/catalogar/editar", methods=["POST"], endpoint="catalogar_editar")
def catalogar_editar():
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "Activo")
    if codigo not in data["cuentas"]:
        return redirect(url_for("catalogar.catalogar") + "?error=cuenta_no_existe")
    if not nombre:
        return redirect(url_for("catalogar.catalogar") + "?error=cuenta_no_existe")
    data["cuentas"][codigo]["nombre"] = nombre
    data["cuentas"][codigo]["tipo"] = tipo
    data = audit_log(data, "editar_cuenta", f"Cuenta {codigo} — {nombre}")
    save_data(data)
    return redirect(url_for("catalogar.catalogar") + "?ok=cuenta_guardada")


@catalogar_bp.route("/catalogar/eliminar", methods=["POST"], endpoint="catalogar_eliminar")
def catalogar_eliminar():
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    if codigo not in data["cuentas"]:
        return redirect(url_for("catalogar.catalogar") + "?error=cuenta_no_existe")

    tiene_mov = False
    for entry in data.get("diario", []):
        for mov in entry.get("movimientos", []):
            if mov["cuenta"] == codigo:
                tiene_mov = True
                break
        if tiene_mov:
            break
    if not tiene_mov:
        for aj in data.get("ajustes", []):
            for mov in aj.get("movimientos", []):
                if mov["cuenta"] == codigo:
                    tiene_mov = True
                    break
            if tiene_mov:
                break
    if not tiene_mov:
        for mov in data.get("caja_movimientos", []):
            if mov.get("cuenta") == codigo:
                tiene_mov = True
                break
    if not tiene_mov:
        for cc in data.get("cuentas_cobrar", []):
            if cc.get("cuenta") == codigo:
                tiene_mov = True
                break
            for pago in cc.get("pagos", []):
                if pago.get("cuenta") == codigo:
                    tiene_mov = True
                    break
    if not tiene_mov:
        for prod, regs in data.get("kardex", {}).items():
            for reg in regs:
                if reg.get("cuenta") == codigo:
                    tiene_mov = True
                    break
    if tiene_mov:
        return redirect(url_for("catalogar.catalogar") + "?error=no_se_puede_eliminar_cuenta_con_movimientos")
    data = audit_log(data, "eliminar_cuenta", f"Cuenta {codigo} — {data['cuentas'].get(codigo,{}).get('nombre','?')}")
    del data["cuentas"][codigo]
    save_data(data)
    return redirect(url_for("catalogar.catalogar") + "?ok=cuenta_eliminada")


@catalogar_bp.route("/cuentas/eliminar", methods=["POST"], endpoint="eliminar_cuenta")
def eliminar_cuenta():
    data = load_data()
    codigo = request.form.get("codigo", "").strip()
    if codigo not in data["cuentas"]:
        return redirect(request.referrer or url_for("index"))

    tiene_mov = False
    for entry in data.get("diario", []):
        for mov in entry.get("movimientos", []):
            if mov["cuenta"] == codigo:
                tiene_mov = True
                break
        if tiene_mov:
            break
    if not tiene_mov:
        for aj in data.get("ajustes", []):
            for mov in aj.get("movimientos", []):
                if mov["cuenta"] == codigo:
                    tiene_mov = True
                    break
            if tiene_mov:
                break
    if not tiene_mov:
        for mov in data.get("caja_movimientos", []):
            if mov.get("cuenta") == codigo:
                tiene_mov = True
                break
    if not tiene_mov:
        for cc in data.get("cuentas_cobrar", []):
            if cc.get("cuenta") == codigo:
                tiene_mov = True
                break
            for pago in cc.get("pagos", []):
                if pago.get("cuenta") == codigo:
                    tiene_mov = True
                    break
    if not tiene_mov:
        for prod, regs in data.get("kardex", {}).items():
            for reg in regs:
                if reg.get("cuenta") == codigo:
                    tiene_mov = True
                    break

    if tiene_mov:
        return redirect((request.referrer or url_for("index")) + "?error=no_se_puede_eliminar_cuenta_con_movimientos")
    del data["cuentas"][codigo]
    save_data(data)
    return redirect(request.referrer or url_for("index"))


@catalogar_bp.route("/catalogar/resetear", methods=["POST"], endpoint="catalogar_resetear")
def catalogar_resetear():
    """Reemplaza todo el catálogo con las cuentas base y migra datos existentes."""
    data = load_data()

    OLD_TO_NEW = {
        "1001": "1.1.01", "1002": "1.1.02", "1003": "1.1.03",
        "1004": "1.1.04", "2001": "2.1.01", "2002": "2.1.01",
        "3001": "3.1", "3002": "3.3.02",
        "4001": "4.1.01", "4002": "4.2",
        "5001": "5.1", "5002": "5.2", "5003": "5.2.05",
        "6001": "5.2.05",
    }

    def migrar_cuenta(cod):
        return OLD_TO_NEW.get(cod, cod)

    for entry in data.get("diario", []):
        for mov in entry.get("movimientos", []):
            mov["cuenta"] = migrar_cuenta(mov["cuenta"])

    for mov in data.get("caja_movimientos", []):
        mov["cuenta"] = migrar_cuenta(mov["cuenta"])

    for aj in data.get("ajustes", []):
        for mov in aj.get("movimientos", []):
            mov["cuenta"] = migrar_cuenta(mov["cuenta"])

    for prod_key in list(data.get("kardex_peps", {})):
        peps = data["kardex_peps"][prod_key]
        for lote in peps.get("lotes", []):
            lote["cuenta"] = migrar_cuenta(lote.get("cuenta", ""))

    data["cuentas"] = dict(CUENTAS_BASE)
    data = audit_log(data, "resetear_catalogo", "Catálogo restaurado a cuentas por defecto con migración")
    save_data(data)
    return redirect(url_for("catalogar.catalogar") + "?ok=cuenta_guardada")