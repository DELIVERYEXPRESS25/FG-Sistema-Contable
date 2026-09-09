from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for

from services.auth import audit_log
from services.store import load_data, save_data, _paginar


cobrar_bp = Blueprint("cobrar", __name__)


@cobrar_bp.route("/cobrar", endpoint="cobrar")
def cobrar():
    data = load_data()
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    items = data["cuentas_cobrar"]
    indexed = list(enumerate(items))
    if search:
        sl = search.lower()
        indexed = [
            (i, item)
            for i, item in indexed
            if sl in item.get("descripcion", "").lower()
            or sl in item.get("fecha", "")
            or sl in item.get("estado", "").lower()
        ]
    items_pag, page, total_pages, total = _paginar([item for _, item in indexed], page, 50)
    paginated_indices = [indexed[idx][0] for idx in range(len(items_pag))]
    return render_template(
        "cobrar.html",
        cobrar=items_pag,
        page=page,
        total_pages=total_pages,
        total_entries=total,
        search=search,
        indices=paginated_indices,
    )


@cobrar_bp.route("/cobrar/pagar/<int:idx>", methods=["POST"], endpoint="pagar_cobro")
def pagar_cobro(idx):
    data = load_data()
    if 0 <= idx < len(data["cuentas_cobrar"]):
        data["cuentas_cobrar"][idx]["estado"] = "Cobrado"
        data["cuentas_cobrar"][idx]["fecha_cobro"] = date.today().isoformat()
    data = audit_log(data, "pagar_cobro", f"Cobro #{idx} pagado")
    save_data(data)
    return redirect(url_for("cobrar.cobrar"))


@cobrar_bp.route("/cobrar/eliminar/<int:idx>", methods=["POST"], endpoint="eliminar_cobro")
def eliminar_cobro(idx):
    data = load_data()
    if 0 <= idx < len(data["cuentas_cobrar"]):
        data["cuentas_cobrar"].pop(idx)
    data = audit_log(data, "eliminar_cobro", f"Cobro #{idx} eliminado")
    save_data(data)
    return redirect(url_for("cobrar.cobrar"))