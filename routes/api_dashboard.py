from flask import Blueprint, jsonify

from services.store import load_data
from services.calculos import (
    get_ventas_por_dia,
    get_ventas_por_mes,
    get_gastos_por_mes,
)


api_dashboard_bp = Blueprint("api_dashboard", __name__)


@api_dashboard_bp.route("/api/ventas_dia", endpoint="api_ventas_dia")
def api_ventas_dia():
    return jsonify(get_ventas_por_dia(load_data()))


@api_dashboard_bp.route("/api/ventas_mes", endpoint="api_ventas_mes")
def api_ventas_mes():
    return jsonify(get_ventas_por_mes(load_data()))


@api_dashboard_bp.route("/api/gastos_mes", endpoint="api_gastos_mes")
def api_gastos_mes():
    return jsonify(get_gastos_por_mes(load_data()))


@api_dashboard_bp.route("/api/stock", endpoint="api_stock")
def api_stock():
    data = load_data()
    stock = {}
    
    # Calculate stock from Kardex (the reliable source)
    for prod, movs in data.get("kardex", {}).items():
        if isinstance(movs, list):
            saldo = 0
            costo = 0
            for m in movs:
                cant = m.get("cantidad", 0)
                if m.get("tipo") == "entrada":
                    saldo += cant
                elif m.get("tipo") == "salida":
                    saldo -= cant
                costo = m.get("costo", 0)
            stock[prod] = {
                "stock": saldo,
                "costo": costo,
                "precio_venta": 0,
            }
    
    # Fill in price from productos/kardex_peps
    for prod, info in data.get("productos", {}).items():
        if prod in stock:
            stock[prod]["precio_venta"] = info.get("precio_venta", 0)
            if not stock[prod]["costo"]:
                stock[prod]["costo"] = info.get("costo_promedio", 0)
    
    for prod, info in data.get("kardex_peps", {}).items():
        if prod in stock:
            stock[prod]["precio_venta"] = info.get("precio_venta", 0) or stock[prod].get("precio_venta", 0)
            if not stock[prod]["costo"]:
                stock[prod]["costo"] = info.get("costo_promedio", 0)
        else:
            stock[prod] = {
                "stock": 0,
                "costo": info.get("costo_promedio", 0),
                "precio_venta": info.get("precio_venta", 0),
            }
    
    return jsonify(stock)


@api_dashboard_bp.route("/api/notificaciones", endpoint="api_notificaciones")
def api_notificaciones():
    data = load_data()
    notificaciones = []

    for nombre, peps in data.get("kardex_peps", {}).items():
        if isinstance(peps, dict):
            stock = peps.get("stock_total", 0)
            if stock <= 0:
                notificaciones.append(
                    {
                        "tipo": "critico",
                        "mensaje": f"Sin stock: {nombre}",
                        "valor": f"{stock} unid.",
                        "modulo": "kardex",
                    }
                )
            elif stock <= 5:
                notificaciones.append(
                    {
                        "tipo": "advertencia",
                        "mensaje": f"Stock bajo: {nombre}",
                        "valor": f"{stock} unid.",
                        "modulo": "kardex",
                    }
                )

    for cc in data.get("cuentas_cobrar", []):
        if cc.get("estado") == "Pendiente":
            notificaciones.append(
                {
                    "tipo": "advertencia",
                    "mensaje": f"Cobro pendiente: {cc.get('descripcion', '')}",
                    "valor": f"C$ {cc.get('monto', 0):.2f}",
                    "modulo": "cobrar",
                }
            )

    notificaciones.sort(key=lambda x: (0 if x["tipo"] == "critico" else 1))
    return jsonify({"notificaciones": notificaciones})