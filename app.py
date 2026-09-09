from flask import Flask, render_template, request, redirect, url_for, jsonify, g, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json, os, signal, sys, secrets, time, copy
from datetime import datetime, date
from collections import defaultdict
import kardex_peps
import db_internal
from decimal import Decimal, ROUND_HALF_UP

from services.helpers import get_next_id, ensure_ids, get_data_dir, DATA_FILE, tipo_saldo
from services.auth import AUTH_ENABLED, login_required, audit_log
from services.store import (
    _archivos_temp, _MAX_ARCHIVOS_TEMP, _data_cache_global, _DATA_CACHE_TTL,
    FORMAS_PAGO_VALIDAS, empty_data, _obtener_rango_fechas,
    _periodo_cerrado, _periodos_disponibles_por_tipo, _paginar,
    load_data, save_data,
)
from services.calculos import (
    calcular_mayor, calcular_balanza, calcular_estado_resultados,
    calcular_balance_general, calcular_balance_general_con_utilidad,
    get_ventas_por_dia, get_ventas_por_mes,
    get_gastos_por_mes,
    procesar_movimientos_periodo,
    calcular_movimientos_cierre,
    obtener_cuenta_capital_cierre,
    validar_cierre_posible,
    meses_disponibles
)

from routes.auth import auth_bp
from routes.comercializacion import comercializacion_bp
from routes.caja import caja_bp
from routes.cobrar import cobrar_bp
from routes.ajustes import ajustes_bp
from routes.reportes_core import reportes_core_bp
from routes.diario import diario_bp
from routes.api_dashboard import api_dashboard_bp
from routes.fiscales import fiscales_bp
from routes.catalogar import catalogar_bp
from routes.cierre_mensual import cierre_mensual_bp
from routes.reportes_pdf import reportes_pdf_bp
from routes.exportar_reporte import exportar_reporte_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.register_blueprint(auth_bp)
app.register_blueprint(comercializacion_bp)
app.register_blueprint(caja_bp)
app.register_blueprint(cobrar_bp)
app.register_blueprint(ajustes_bp)
app.register_blueprint(reportes_core_bp)
app.register_blueprint(diario_bp)
app.register_blueprint(api_dashboard_bp)
app.register_blueprint(fiscales_bp)
app.register_blueprint(catalogar_bp)
app.register_blueprint(cierre_mensual_bp)
app.register_blueprint(reportes_pdf_bp)
app.register_blueprint(exportar_reporte_bp)


@app.context_processor
def inject_globals():
    return {"auth_enabled": AUTH_ENABLED}


@app.before_request
def check_login():
    """Protege todas las rutas excepto login y static."""
    if not AUTH_ENABLED:
        if "user" not in session:
            session["user"] = "admin"
        g.user = session.get("user", "admin")
        return
    if request.endpoint in ("auth.login", "static"):
        return
    if "user" not in session:
        return redirect(url_for("auth.login"))


@app.route("/")
@login_required
def index():
    data = load_data()
    ventas_dia = get_ventas_por_dia(data)
    ventas_mes = get_ventas_por_mes(data)
    gastos_mes = get_gastos_por_mes(data)
    _, _, _, _, utilidad = calcular_estado_resultados(data)
    mayor = calcular_mayor(data)
    total_activo = 0
    total_pasivo = 0
    for c, info in data["cuentas"].items():
        d = mayor[c]["debe"] if c in mayor else 0
        h = mayor[c]["haber"] if c in mayor else 0
        ts = tipo_saldo(info["tipo"])
        saldo = (d - h) if ts == "Debe" else (h - d)
        if info["tipo"] == "Activo":
            total_activo += saldo
        elif info["tipo"] == "Pasivo":
            total_pasivo += saldo

    return render_template(
        "index.html",
        ventas_dia=ventas_dia,
        ventas_mes=ventas_mes,
        gastos_mes=gastos_mes,
        utilidad=utilidad,
        total_activo=total_activo,
        total_pasivo=total_pasivo,
        diario=data["diario"],
        cuentas=data["cuentas"],
    )


@app.route("/kardex")
def kardex():
    try:
        data = load_data()

        if "kardex" not in data:
            data["kardex"] = {}
        if "kardex_peps" not in data:
            data["kardex_peps"] = {}
        if "productos" not in data:
            data["productos"] = {}

        reporte_peps = {}
        try:
            if data.get("kardex") or data.get("productos"):
                reporte_peps = kardex_peps.generar_reporte_kardex_peps(data, max_lotes=5)
        except Exception as e:
            print(f"Error generando reporte PEPS: {e}")

        productos_list = list(data.get("kardex", {}).keys())

        margen_default = data.get("configuracion", {}).get("margen_default", 30)
        productos_data_dict = {}
        for p in productos_list:
            prod_info = data.get("productos", {}).get(p, {})
            if isinstance(prod_info, dict):
                productos_data_dict[p] = {
                    "precio_venta": prod_info.get("precio_venta", 0),
                    "margen": prod_info.get("margen", margen_default),
                    "costo_promedio": prod_info.get("costo_promedio", 0),
                }
            else:
                productos_data_dict[p] = {"precio_venta": 0, "margen": margen_default, "costo_promedio": 0}
            peps_info = data.get("kardex_peps", {}).get(p, {})
            if isinstance(peps_info, dict):
                if not productos_data_dict[p]["precio_venta"]:
                    productos_data_dict[p]["precio_venta"] = peps_info.get("precio_venta", 0)
                if not productos_data_dict[p]["margen"]:
                    productos_data_dict[p]["margen"] = peps_info.get("margen", margen_default)
                if not productos_data_dict[p]["costo_promedio"]:
                    productos_data_dict[p]["costo_promedio"] = peps_info.get("costo_promedio", 0)

        return render_template(
            "kardex.html",
            kardex=data.get("kardex", {}),
            productos=productos_list,
            reporte_peps=reporte_peps,
            productos_data=productos_data_dict,
            margen_default=data.get("configuracion", {}).get("margen_default", 30),
        )

    except Exception as e:
        print(f"ERROR EN /kardex: {e}")
        import traceback

        traceback.print_exc()
        return (
            f"""
        <html>
        <body style="font-family: Arial; padding: 40px; background: #1a1d2e; color: white;">
            <h1>❌ Error en Kardex</h1>
            <p>Ocurrió un error al cargar el Kardex:</p>
            <pre style="background: #2d3142; padding: 20px; border-radius: 8px;">{str(e)}</pre>
            <p><a href="/" style="color: #4f8cff;">← Volver al inicio</a></p>
        </body>
        </html>
        """,
            500,
        )


@app.route("/kardex/agregar_producto", methods=["POST"])
def agregar_producto_kardex():
    data = load_data()

    if "kardex" not in data:
        data["kardex"] = {}
    if "kardex_peps" not in data:
        data["kardex_peps"] = {}
    if "productos" not in data:
        data["productos"] = {}

    nombre = request.form.get("nombre", "").strip()
    try:
        precio_venta = float(request.form.get("precio_venta", 0) or 0)
        margen = float(request.form.get("margen", 30) or 30)
    except (ValueError, TypeError):
        precio_venta = 0
        margen = 30

    if not nombre:
        return redirect(url_for("kardex"))

    if nombre in data["kardex"]:
        return redirect(url_for("kardex") + "?error=producto_duplicado")

    data["kardex"][nombre] = []

    data["productos"][nombre] = {
        "nombre": nombre,
        "stock": 0,
        "costo_promedio": 0,
        "precio_venta": precio_venta,
        "margen": margen,
    }

    data["kardex_peps"][nombre] = {
        "lotes": [],
        "stock_total": 0,
        "costo_promedio": 0,
        "precio_venta": precio_venta,
        "margen": margen,
    }

    save_data(data)
    return redirect(url_for("kardex"))


@app.route("/kardex/movimiento", methods=["POST"])
def agregar_mov_kardex():
    try:
        data = load_data()
        producto = request.form.get("producto", "")
        fecha = request.form.get("fecha", date.today().isoformat())

        if _periodo_cerrado(data, fecha):
            return redirect(url_for("kardex") + "?error=periodo_cerrado")

        tipo = request.form.get("tipo", "entrada")
        cantidad = int(request.form.get("cantidad", 0))
        costo = float(request.form.get("costo", 0))
        precio_venta = float(request.form.get("precio_venta", 0))
        descripcion = request.form.get("descripcion", "")

        if not producto:
            print("Error: Producto vacío")
            return redirect(url_for("kardex"))

        if cantidad <= 0:
            print("Error: Cantidad debe ser mayor a 0")
            return redirect(url_for("kardex"))

        if "kardex" not in data:
            data["kardex"] = {}
        if "kardex_peps" not in data:
            data["kardex_peps"] = {}

        try:
            if tipo.lower() == "entrada":
                print(f"Agregando entrada PEPS: {producto}, {cantidad} unidades @ C$ {costo}")
                if precio_venta <= 0 and costo > 0:
                    prod_mg = data.get("productos", {}).get(producto, {}).get("margen", 0) or 0
                    if prod_mg <= 0:
                        prod_mg = data.get("kardex_peps", {}).get(producto, {}).get("margen", 30) or 30
                    precio_venta = round(costo / (1 - prod_mg / 100), 2)
                data = kardex_peps.agregar_entrada_peps(
                    data, producto, fecha, cantidad, costo, precio_venta
                )
                print("✓ Entrada agregada exitosamente")

            elif tipo.lower() == "salida":
                print(f"Procesando salida PEPS: {producto}, {cantidad} unidades")
                data, costo_total, lotes_usados = kardex_peps.procesar_salida_peps(
                    data, producto, fecha, cantidad
                )
                print(f"✓ Salida procesada. Costo total: C$ {costo_total}")

                forma_pago = request.form.get("forma_pago", "").strip()
                if forma_pago and forma_pago not in FORMAS_PAGO_VALIDAS:
                    forma_pago = "Efectivo"
                if forma_pago:
                    cliente = request.form.get("cliente", "Cliente general").strip()
                    pv = precio_venta if precio_venta > 0 else data.get("productos", {}).get(producto, {}).get("precio_venta", 0)
                    total_venta = cantidad * pv

                    if "diario" not in data:
                        data["diario"] = []

                    diario_id = get_next_id(data, "diario")
                    cuenta_cobro = "1.1.01" if forma_pago == "Efectivo" else ("1.1.02" if forma_pago == "Banco" else "1.1.03")

                    movs = [
                        {"cuenta": cuenta_cobro, "tipo": "Debe", "monto": total_venta},
                        {"cuenta": "4.1.01", "tipo": "Haber", "monto": total_venta},
                    ]
                    if costo_total > 0:
                        movs.append({"cuenta": "5.1", "tipo": "Debe", "monto": costo_total})
                        movs.append({"cuenta": "1.1.04", "tipo": "Haber", "monto": costo_total})

                    ref_kardex = f"KX-{diario_id:04d}"
                    entry = {
                        "id": diario_id,
                        "fecha": fecha,
                        "descripcion": f"Venta Kardex - {producto} - {cliente} ({forma_pago})",
                        "ref": ref_kardex,
                        "movimientos": movs,
                    }
                    data["diario"].append(entry)

                    if cuenta_cobro in ("1.1.01", "1.1.02"):
                        data.setdefault("caja_movimientos", [])
                        data["caja_movimientos"].append({
                            "id": get_next_id(data, "caja_movimientos"),
                            "fecha": fecha,
                            "descripcion": f"Venta Kardex - {producto} - {cliente}",
                            "tipo": "Debe",
                            "monto": total_venta,
                            "cuenta": cuenta_cobro,
                            "ref_diario": diario_id,
                        })

                    if cuenta_cobro == "1.1.03":
                        data.setdefault("cuentas_cobrar", [])
                        data["cuentas_cobrar"].append({
                            "id": get_next_id(data, "cuentas_cobrar"),
                            "fecha": fecha,
                            "descripcion": f"Venta Kardex - {producto} - {cliente}",
                            "monto": total_venta,
                            "estado": "Pendiente",
                            "ref_diario": diario_id,
                        })

                    if producto in data.get("kardex", {}):
                        k = data["kardex"][producto]
                        if k:
                            ultimo = k[-1]
                            ultimo["precio_venta"] = pv
                            ultimo["descripcion"] = f"Venta - {cliente} ({forma_pago})"
                            ultimo["ref_diario"] = diario_id

            elif tipo.lower() == "ajuste":
                if producto not in data["kardex"]:
                    data["kardex"][producto] = []

                saldo_anterior = (
                    data["kardex"][producto][-1]["saldo"]
                    if data["kardex"][producto]
                    else 0
                )

                data["kardex"][producto].append(
                    {
                        "fecha": fecha,
                        "tipo": "ajuste",
                        "cantidad": cantidad,
                        "costo": costo,
                        "precio_venta": precio_venta,
                        "total": cantidad * costo,
                        "saldo": cantidad,
                        "descripcion": descripcion or "Ajuste de inventario",
                    }
                )
                data = _reconstruir_peps(data, producto)

        except ValueError as e:
            print(f"Error controlado: {e}")
            return redirect(url_for("kardex") + "?error=" + str(e).replace(" ", "_"))

        except Exception as e:
            print(f"Error inesperado en movimiento: {e}")
            import traceback

            traceback.print_exc()
            return redirect(url_for("kardex"))

        save_data(data)
        print("✓ Datos guardados correctamente")

    except Exception as e:
        print(f"ERROR EN /kardex/movimiento: {e}")
        import traceback

        traceback.print_exc()

    return redirect(url_for("kardex"))


@app.route("/pos")
def pos():
    data = load_data()
    productos = []
    nombres = set(data.get("kardex", {}).keys())
    nombres.update(data.get("kardex_peps", {}).keys())

    for nombre in sorted(nombres):
        try:
            peps_info = data.get("kardex_peps", {}).get(nombre, {})
            prod_info = data.get("productos", {}).get(nombre, {})

            if isinstance(peps_info, dict) and peps_info.get("stock_total", 0) > 0:
                saldo = peps_info.get("stock_total", 0)
                costo = peps_info.get("costo_promedio", 0)
            else:
                k = data.get("kardex", {}).get(nombre, [])
                if isinstance(k, list) and k:
                    saldo = k[-1].get("saldo", 0)
                    costo = k[-1].get("costo", 0)
                elif isinstance(k, dict):
                    saldo = k.get("saldo_actual", k.get("saldo_inicial", 0))
                    costo = k.get("costo_unitario", 0)
                else:
                    continue

            pv = 0
            mg = 30
            if isinstance(prod_info, dict):
                pv = prod_info.get("precio_venta", 0) or 0
                mg = prod_info.get("margen", 30) or 30
            if not pv and isinstance(peps_info, dict):
                pv = peps_info.get("precio_venta", 0) or 0
                mg = peps_info.get("margen", 30) or 30
            if not pv:
                pv = round(costo / (1 - mg / 100), 2)

            productos.append({
                "nombre": nombre, "saldo": saldo,
                "costo": costo, "precio_venta": pv, "margen": mg,
            })
        except Exception as e:
            print(f"Error cargando producto {nombre}: {e}")
            continue

    historial = data.get("pos_historial", [])

    return render_template("pos.html", productos=productos, historial=historial)


@app.route("/pos/venta", methods=["POST"])
def pos_venta():
    try:
        data = load_data()
        fecha = request.form.get("fecha", date.today().isoformat())

        if _periodo_cerrado(data, fecha):
            return redirect(url_for("pos") + "?error=periodo_cerrado")

        cliente = request.form.get("cliente", "Cliente general")
        forma_pago = request.form.get("forma_pago", "Efectivo")
        if forma_pago not in FORMAS_PAGO_VALIDAS:
            forma_pago = "Efectivo"
        productos_nombres = request.form.getlist("producto")
        cantidades = request.form.getlist("cantidad")
        precios = request.form.getlist("precio")

        lineas = []
        total_venta = 0
        total_costo = 0
        productos_sin_stock = []

        for i in range(len(productos_nombres)):
            nombre = productos_nombres[i]
            cantidad = round(float(cantidades[i])) if cantidades[i] else 0
            precio = float(precios[i]) if precios[i] else 0

            if nombre and cantidad > 0 and precio > 0:
                stock_disp = (data.get("kardex_peps", {})
                              .get(nombre, {}).get("stock_total", 0))
                if stock_disp <= 0:
                    k = data.get("kardex", {}).get(nombre, [])
                    if isinstance(k, list) and k:
                        stock_disp = k[-1].get("saldo", 0)
                    elif isinstance(k, dict):
                        stock_disp = k.get("saldo_actual", 0)
                if stock_disp <= 0:
                    productos_sin_stock.append(nombre)
                    continue
                if cantidad > stock_disp:
                    productos_sin_stock.append(f"{nombre} (solo {int(stock_disp)} disp.)")
                    continue

                subtotal = cantidad * precio

                costo_u = 0
                costo_total = 0
                peps_disponible = stock_disp
                if peps_disponible >= cantidad:
                    try:
                        data, costo_total, _ = kardex_peps.procesar_salida_peps(
                            data, nombre, fecha, cantidad)
                        costo_u = costo_total / cantidad if cantidad else 0
                        if nombre in data.get("kardex", {}):
                            kx = data["kardex"][nombre]
                            if kx:
                                kx[-1]["precio_venta"] = precio
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        costo_total = 0
                        costo_u = 0
                else:
                    if nombre in data.get("kardex", {}):
                        k = data["kardex"][nombre]
                        if isinstance(k, list) and k:
                            costo_u = k[-1].get("costo", 0)
                            saldo_anterior = k[-1]["saldo"] if k else 0
                            nuevo_saldo = saldo_anterior - cantidad
                            k.append({
                                "fecha": fecha, "tipo": "salida",
                                "cantidad": cantidad, "costo": costo_u,
                                "precio_venta": precio,
                                "total": cantidad * costo_u,
                                "saldo": nuevo_saldo,
                                "descripcion": f"Venta POS - {cliente}",
                            })
                        elif isinstance(k, dict):
                            if "movimientos" not in k:
                                k["movimientos"] = []
                            k["movimientos"].append({
                                "fecha": fecha, "tipo": "Salida",
                                "cantidad": cantidad,
                                "costo_unitario": costo_u,
                                "precio_venta": precio,
                                "descripcion": f"Venta POS - {cliente}",
                            })
                            saldo = k.get("saldo_inicial", 0)
                            for m in k["movimientos"]:
                                if m["tipo"] == "Entrada":
                                    saldo += m["cantidad"]
                                else:
                                    saldo -= m["cantidad"]
                            k["saldo_actual"] = saldo
                    costo_total = cantidad * costo_u

                lineas.append(
                    {
                        "producto": nombre,
                        "cantidad": cantidad,
                        "precio_unitario": precio,
                        "subtotal": subtotal,
                        "costo_unitario": costo_u,
                        "costo_total": costo_total,
                    }
                )

                total_venta += subtotal
                total_costo += costo_total

        if not lineas and not productos_sin_stock:
            return redirect(url_for("pos"))

        if not lineas:
            return redirect(url_for("pos"))

        if productos_sin_stock:
            nombres_str = ", ".join(productos_sin_stock)
            return redirect(url_for("pos") + f"?error=sin_stock&productos={nombres_str}")

        if "diario" not in data:
            data["diario"] = []

        diario_id = get_next_id(data, "diario")
        cuenta_cobro = (
            "1.1.01"
            if forma_pago == "Efectivo"
            else ("1.1.02" if forma_pago == "Banco" else "1.1.03")
        )

        movimientos_diario = [
            {"cuenta": cuenta_cobro, "tipo": "Debe", "monto": total_venta},
            {"cuenta": "4.1.01", "tipo": "Haber", "monto": total_venta},
        ]

        if total_costo > 0:
            movimientos_diario.append(
                {"cuenta": "5.1", "tipo": "Debe", "monto": total_costo}
            )
            movimientos_diario.append(
                {"cuenta": "1.1.04", "tipo": "Haber", "monto": total_costo}
            )

        ref_pos = f"POS-{len(data.get('pos_historial', [])) + 1:04d}"

        entry = {
            "id": diario_id,
            "fecha": fecha,
            "descripcion": f"Venta POS - {cliente} ({forma_pago})",
            "ref": ref_pos,
            "movimientos": movimientos_diario,
        }
        data["diario"].append(entry)

        if cuenta_cobro in ("1.1.01", "1.1.02"):
            data.setdefault("caja_movimientos", [])
            data["caja_movimientos"].append(
                {
                    "id": get_next_id(data, "caja_movimientos"),
                    "fecha": fecha,
                    "descripcion": f"Venta POS - {cliente}",
                    "tipo": "Debe",
                    "monto": total_venta,
                    "cuenta": cuenta_cobro,
                    "ref_diario": diario_id,
                }
            )

        if cuenta_cobro == "1.1.03":
            if "cuentas_cobrar" not in data:
                data["cuentas_cobrar"] = []

            data["cuentas_cobrar"].append(
                {
                    "id": get_next_id(data, "cuentas_cobrar"),
                    "fecha": fecha,
                    "descripcion": f"Venta POS - {cliente}",
                    "monto": total_venta,
                    "estado": "Pendiente",
                    "ref_diario": diario_id,
                }
            )

        if "pos_historial" not in data:
            data["pos_historial"] = []

        data["pos_historial"].append(
            {
                "ref": ref_pos,
                "fecha": fecha,
                "cliente": cliente,
                "forma_pago": forma_pago,
                "lineas": lineas,
                "total": total_venta,
                "costo": total_costo,
                "utilidad": total_venta - total_costo,
            }
        )

        data = audit_log(data, "pos_venta", f"Venta {ref_pos} — C${total_venta:.2f}")
        save_data(data)
        return redirect(url_for("pos"))

    except Exception as e:
        print(f"ERROR EN /pos/venta: {e}")
        import traceback

        traceback.print_exc()
        return redirect(url_for("pos"))


@app.route("/pos/anular/<ref>", methods=["POST"])
def pos_anular(ref):
    """Anula una venta POS: revierte kardex, diario, caja y marca como anulada."""
    data = load_data()
    historial = data.get("pos_historial", [])

    venta = None
    venta_idx = None
    for i, v in enumerate(historial):
        if v.get("ref") == ref:
            venta = v
            venta_idx = i
            break

    if not venta:
        return redirect(url_for("pos"))

    try:
        for linea in venta.get("lineas", []):
            nombre = linea["producto"]
            cantidad_vendida = linea["cantidad"]

            if nombre in data.get("kardex", {}):
                kx = data["kardex"][nombre]
                if isinstance(kx, list):
                    for j in range(len(kx) - 1, -1, -1):
                        mov = kx[j]
                        es_venta_pos = mov.get("descripcion", "").startswith("Venta POS")
                        es_salida_peps = mov.get("descripcion", "").startswith("Salida PEPS")
                        if (mov.get("tipo") == "salida" and
                            (es_venta_pos or es_salida_peps) and
                            abs(mov.get("cantidad", 0) - cantidad_vendida) < 0.01):
                            if j > 0:
                                kx[j - 1]["saldo"] = kx[j - 1].get("saldo", 0) + cantidad_vendida
                            del kx[j]
                            break

            peps = data.get("kardex_peps", {}).get(nombre, {})
            if isinstance(peps, dict) and peps.get("lotes"):
                for lote in reversed(peps["lotes"]):
                    lote["cantidad_restante"] = lote.get("cantidad_restante", 0) + cantidad_vendida
                    peps["stock_total"] = peps.get("stock_total", 0) + cantidad_vendida
                    break
                if peps.get("stock_total", 0) < 0:
                    peps["stock_total"] = 0

        ref_original = venta.get("ref", "")
        diario = data.get("diario", [])
        diario_id = None
        for e in diario:
            if e.get("ref") == ref_original:
                diario_id = e.get("id")
                break
        data["diario"] = [e for e in diario if e.get("ref") != ref_original]

        if diario_id:
            caja = data.get("caja_movimientos", [])
            data["caja_movimientos"] = [c for c in caja if c.get("ref_diario") != diario_id]

        if diario_id:
            cc = data.get("cuentas_cobrar", [])
            data["cuentas_cobrar"] = [c for c in cc if c.get("ref_diario") != diario_id]

        new_id = get_next_id(data, "diario")
        total_venta = venta.get("total", 0)
        total_costo = venta.get("costo", 0)
        forma_pago = venta.get("forma_pago", "Efectivo")
        cliente = venta.get("cliente", "")

        cuenta_cobro = (
            "1.1.01" if forma_pago == "Efectivo"
            else ("1.1.02" if forma_pago == "Banco" else "1.1.03")
        )
        movimientos_reversion = [
            {"cuenta": "4.1.01", "tipo": "Debe", "monto": total_venta},
            {"cuenta": cuenta_cobro, "tipo": "Haber", "monto": total_venta},
        ]
        if total_costo > 0:
            movimientos_reversion.append({"cuenta": "1.1.04", "tipo": "Debe", "monto": total_costo})
            movimientos_reversion.append({"cuenta": "5.1", "tipo": "Haber", "monto": total_costo})

        entry = {
            "id": new_id,
            "fecha": venta.get("fecha", ""),
            "descripcion": f"ANULACIÓN Venta POS {ref} — {cliente}",
            "ref": f"ANUL-{ref}",
            "movimientos": movimientos_reversion,
        }
        data["diario"].append(entry)

        data["pos_historial"][venta_idx]["anulada"] = True
        data["pos_historial"][venta_idx]["motivo_anulacion"] = f"Anulada el {date.today().isoformat()}"

        data = audit_log(data, "pos_anular", f"Venta {ref} anulada — C${total_venta:.2f}")
        save_data(data)

    except Exception as e:
        import traceback
        traceback.print_exc()

    return redirect(url_for("pos"))


@app.route("/pos/editar/<ref>", methods=["GET", "POST"])
def pos_editar(ref):
    data = load_data()
    historial = data.get("pos_historial", [])

    venta = None
    venta_idx = None
    for i, v in enumerate(historial):
        if v.get("ref") == ref:
            venta = v
            venta_idx = i
            break

    if not venta:
        return redirect(url_for("pos"))

    if request.method == "GET":
        return render_template("pos_editar.html", venta=venta, productos=data.get("kardex_peps", {}))

    try:
        fecha = request.form.get("fecha", venta["fecha"])
        cliente = request.form.get("cliente", venta["cliente"])
        forma_pago = request.form.get("forma_pago", venta["forma_pago"])

        if forma_pago not in FORMAS_PAGO_VALIDAS:
            forma_pago = "Efectivo"

        productos_nombres = request.form.getlist("producto")
        cantidades = request.form.getlist("cantidad")
        precios = request.form.getlist("precio")

        for linea in venta.get("lineas", []):
            nombre = linea["producto"]
            cantidad_vendida = linea["cantidad"]

            if nombre in data.get("kardex", {}):
                kx = data["kardex"][nombre]
                if isinstance(kx, list):
                    for j in range(len(kx) - 1, -1, -1):
                        mov = kx[j]
                        es_venta_pos = mov.get("descripcion", "").startswith("Venta POS")
                        es_salida_peps = mov.get("descripcion", "").startswith("Salida PEPS")
                        if (mov.get("tipo") == "salida" and
                            (es_venta_pos or es_salida_peps) and
                            abs(mov.get("cantidad", 0) - cantidad_vendida) < 0.01):
                            if j > 0:
                                kx[j - 1]["saldo"] = kx[j - 1].get("saldo", 0) + cantidad_vendida
                            del kx[j]
                            break

            peps = data.get("kardex_peps", {}).get(nombre, {})
            if isinstance(peps, dict) and peps.get("lotes"):
                cantidad_por_devolver = cantidad_vendida
                for lote in reversed(peps["lotes"]):
                    if cantidad_por_devolver <= 0:
                        break
                    lote["cantidad_restante"] = lote.get("cantidad_restante", 0) + cantidad_por_devolver
                    peps["stock_total"] = peps.get("stock_total", 0) + cantidad_por_devolver
                    break  # PEPS: devolver al último lote usado
                if peps.get("stock_total", 0) < 0:
                    peps["stock_total"] = 0

        ref_original = venta.get("ref", "")
        diario = data.get("diario", [])
        diario_original_id = diario_id_for_ref(diario, ref_original)
        data["diario"] = [e for e in diario if e.get("ref") != ref_original]

        caja = data.get("caja_movimientos", [])
        data["caja_movimientos"] = [c for c in caja if c.get("ref_diario") != ref_original
                                     and c.get("ref_diario") != diario_original_id]

        cc = data.get("cuentas_cobrar", [])
        data["cuentas_cobrar"] = [c for c in cc if c.get("ref_diario") != ref_original
                                    and c.get("ref_diario") != diario_original_id]

        lineas = []
        total_venta = 0
        total_costo = 0

        for i in range(len(productos_nombres)):
            nombre = productos_nombres[i]
            cantidad = round(float(cantidades[i])) if cantidades[i] else 0
            precio = float(precios[i]) if precios[i] else 0

            if nombre and cantidad > 0 and precio > 0:
                subtotal = cantidad * precio

                costo_u = 0
                costo_total = 0
                peps_disponible = (data.get("kardex_peps", {})
                                   .get(nombre, {}).get("stock_total", 0))
                if peps_disponible >= cantidad:
                    try:
                        data, costo_total, _ = kardex_peps.procesar_salida_peps(
                            data, nombre, fecha, cantidad)
                        costo_u = costo_total / cantidad if cantidad else 0
                        if nombre in data.get("kardex", {}):
                            kx = data["kardex"][nombre]
                            if kx:
                                kx[-1]["precio_venta"] = precio
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        costo_total = 0
                        costo_u = 0
                else:
                    if nombre in data.get("kardex", {}):
                        k = data["kardex"][nombre]
                        if isinstance(k, list) and k:
                            costo_u = k[-1].get("costo", 0)
                            saldo_anterior = k[-1]["saldo"] if k else 0
                            nuevo_saldo = saldo_anterior - cantidad
                            k.append({
                                "fecha": fecha, "tipo": "salida",
                                "cantidad": cantidad, "costo": costo_u,
                                "precio_venta": precio,
                                "total": cantidad * costo_u,
                                "saldo": nuevo_saldo,
                                "descripcion": f"Venta POS - {cliente}",
                            })
                        costo_total = cantidad * costo_u

                lineas.append({
                    "producto": nombre,
                    "cantidad": cantidad,
                    "precio_unitario": precio,
                    "subtotal": subtotal,
                    "costo_unitario": costo_u,
                    "costo_total": costo_total,
                })
                total_venta += subtotal
                total_costo += costo_total

        if not lineas:
            return redirect(url_for("pos"))

        diario_id = get_next_id(data, "diario")
        cuenta_cobro = (
            "1.1.01" if forma_pago == "Efectivo"
            else ("1.1.02" if forma_pago == "Banco" else "1.1.03")
        )
        movimientos_diario = [
            {"cuenta": cuenta_cobro, "tipo": "Debe", "monto": total_venta},
            {"cuenta": "4.1.01", "tipo": "Haber", "monto": total_venta},
        ]
        if total_costo > 0:
            movimientos_diario.append({"cuenta": "5.1", "tipo": "Debe", "monto": total_costo})
            movimientos_diario.append({"cuenta": "1.1.04", "tipo": "Haber", "monto": total_costo})

        entry = {
            "id": diario_id,
            "fecha": fecha,
            "descripcion": f"Venta POS - {cliente} ({forma_pago})",
            "ref": ref,
            "movimientos": movimientos_diario,
        }
        data["diario"].append(entry)

        if cuenta_cobro in ("1.1.01", "1.1.02"):
            data.setdefault("caja_movimientos", [])
            data["caja_movimientos"].append({
                "id": get_next_id(data, "caja_movimientos"),
                "fecha": fecha,
                "descripcion": f"Venta POS - {cliente}",
                "tipo": "Debe",
                "monto": total_venta,
                "cuenta": cuenta_cobro,
                "ref_diario": diario_id,
            })

        if cuenta_cobro == "1.1.03":
            data.setdefault("cuentas_cobrar", [])
            data["cuentas_cobrar"].append({
                "id": get_next_id(data, "cuentas_cobrar"),
                "fecha": fecha,
                "descripcion": f"Venta POS - {cliente}",
                "monto": total_venta,
                "estado": "Pendiente",
                "ref_diario": diario_id,
            })

        data["pos_historial"][venta_idx] = {
            "ref": ref,
            "fecha": fecha,
            "cliente": cliente,
            "forma_pago": forma_pago,
            "lineas": lineas,
            "total": total_venta,
            "costo": total_costo,
            "utilidad": total_venta - total_costo,
        }

        data = audit_log(data, "pos_editar", f"Venta {ref} editada — C${total_venta:.2f}")
        save_data(data)
        return redirect(url_for("pos"))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return redirect(url_for("pos"))


def diario_id_for_ref(diario, ref):
    for e in diario:
        if e.get("ref") == ref:
            return e.get("id")
    return None




@app.route("/kardex/exportar_peps", methods=["POST"])
def exportar_kardex_peps():
    """Exporta el Kardex completo con método PEPS a Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({"ok": False, "error": "openpyxl no está instalado"}), 500

    data = load_data()
    producto_codigo = request.form.get("producto", None)

    reporte = kardex_peps.generar_reporte_kardex_peps(data, producto_codigo)

    wb = Workbook()

    for idx, (codigo, info) in enumerate(reporte.items()):
        if idx == 0:
            ws = wb.active
            ws.title = codigo[:31]  # Excel limita a 31 caracteres
        else:
            ws = wb.create_sheet(codigo[:31])

        ws.sheet_properties.tabColor = "4F8CFF"

        ws.append(["F&G - Sistema Contable"])
        ws.merge_cells("A1:I1")
        ws["A1"].font = Font(size=16, bold=True, color="1A1D2E")
        ws["A1"].alignment = Alignment(horizontal="center")

        ws.append([f"KARDEX - {info['nombre']}"])
        ws.merge_cells("A2:I2")
        ws["A2"].font = Font(size=14, bold=True, color="4F8CFF")
        ws["A2"].alignment = Alignment(horizontal="center")

        ws.append([f"Código: {codigo}"])
        ws.merge_cells("A3:I3")
        ws["A3"].font = Font(size=10, color="7a7f99")
        ws["A3"].alignment = Alignment(horizontal="center")

        ws.append([f"Generado: {date.today().isoformat()}"])
        ws.merge_cells("A4:I4")
        ws["A4"].font = Font(size=10, color="7a7f99")
        ws["A4"].alignment = Alignment(horizontal="center")

        ws.append([])  # Línea vacía

        ws.append(["RESUMEN"])
        ws["A6"].font = Font(size=12, bold=True)

        ws.append(["Stock Actual:", info["stock"], "unidades"])
        ws.append(["Costo Promedio:", f"C$ {info['costo_promedio']:.2f}", "por unidad"])
        ws.append(["Valor Inventario:", f"C$ {info['valor_inventario']:.2f}", ""])

        ws.append([])  # Línea vacía

        ws.append(
            ["LOTES DISPONIBLES (Método PEPS - Primeras Entradas, Primeras Salidas)"]
        )
        ws["A11"].font = Font(size=12, bold=True, color="2ECC71")
        ws.merge_cells("A11:E11")

        headers_lotes = [
            "Fecha Entrada",
            "Cant. Original",
            "Cant. Disponible",
            "Costo Unit.",
            "Valor Total",
        ]
        ws.append(headers_lotes)

        for cell in ws[12]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color="2ECC71", end_color="2ECC71", fill_type="solid"
            )
            cell.alignment = Alignment(horizontal="center")

        if info["lotes"]:
            for lote in info["lotes"]:
                ws.append(
                    [
                        lote["fecha"],
                        lote["cantidad_original"],
                        lote["cantidad_disponible"],
                        lote["costo_unitario"],
                        lote["valor_total"],
                    ]
                )

                last_row = ws.max_row
                ws.cell(last_row, 4).number_format = "#,##0.00"
                ws.cell(last_row, 5).number_format = "#,##0.00"
        else:
            ws.append(["Sin lotes disponibles", "", "", "", ""])

        ws.append([])  # Línea vacía

        ws.append(["HISTORIAL DE MOVIMIENTOS"])
        ws[f"A{ws.max_row}"].font = Font(size=12, bold=True, color="E74C3C")
        ws.merge_cells(f"A{ws.max_row}:I{ws.max_row}")

        headers_mov = [
            "Fecha",
            "Tipo",
            "Cantidad",
            "Costo Unit.",
            "Total",
            "Saldo",
            "Descripción",
        ]
        ws.append(headers_mov)

        header_row_mov = ws.max_row
        for cell in ws[header_row_mov]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color="E74C3C", end_color="E74C3C", fill_type="solid"
            )
            cell.alignment = Alignment(horizontal="center")

        if info["movimientos"]:
            for mov in reversed(info["movimientos"]):  # Más reciente primero
                tipo_emoji = (
                    "📥"
                    if mov["tipo"] == "entrada"
                    else "📤"
                    if mov["tipo"] == "salida"
                    else "🔄"
                )
                ws.append(
                    [
                        mov["fecha"],
                        f"{tipo_emoji} {mov['tipo'].title()}",
                        mov["cantidad"],
                        mov.get("costo", 0),
                        mov.get("total", 0),
                        mov["saldo"],
                        mov.get("descripcion", ""),
                    ]
                )

                last_row = ws.max_row
                ws.cell(last_row, 4).number_format = "#,##0.00"
                ws.cell(last_row, 5).number_format = "#,##0.00"

                if mov["tipo"] == "entrada":
                    ws.cell(last_row, 2).font = Font(color="2ECC71")
                elif mov["tipo"] == "salida":
                    ws.cell(last_row, 2).font = Font(color="E74C3C")
        else:
            ws.append(["Sin movimientos registrados", "", "", "", "", "", ""])

        ws.column_dimensions["A"].width = 12
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 10
        ws.column_dimensions["G"].width = 40

    from io import BytesIO
    from flask import send_file

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Kardex_PEPS_{timestamp}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/kardex/detectar_hojas", methods=["POST"])
def detectar_hojas():
    """Recibe un Excel y devuelve sus hojas con una vista previa de columnas."""
    from io import BytesIO

    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return jsonify({"ok": False, "error": "No se recibió archivo"})

    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xls"):
        return jsonify(
            {
                "ok": True,
                "tipo": "csv",
                "hojas": [{"nombre": "Hoja única (CSV)", "filas": 0, "columnas": []}],
            }
        )

    try:
        import openpyxl

        contenido = archivo.read()
        wb = openpyxl.load_workbook(BytesIO(contenido), data_only=True, read_only=True)
        hojas = []
        for nombre_hoja in wb.sheetnames:
            ws = wb[nombre_hoja]
            headers = []
            filas_con_datos = 0
            primera = True
            for row in ws.iter_rows(max_row=200, values_only=True):
                if any(c for c in row if c is not None):
                    if primera:
                        headers = [str(c).strip() if c is not None else "" for c in row]
                        primera = False
                    else:
                        filas_con_datos += 1
            hojas.append(
                {
                    "nombre": nombre_hoja,
                    "filas": filas_con_datos,
                    "columnas": headers[:8],  # max 8 para mostrar
                }
            )
        wb.close()
        import base64, time

        token = str(int(time.time() * 1000))
        if len(_archivos_temp) >= _MAX_ARCHIVOS_TEMP:
            _archivos_temp.clear()
        _archivos_temp[token] = {
            "contenido": contenido,
            "filename": archivo.filename,
            "ext": ext,
        }
        return jsonify({"ok": True, "tipo": "xlsx", "hojas": hojas, "token": token})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/kardex/plantilla")
def descargar_plantilla_inventario():
    """Genera y descarga un .xlsx de ejemplo para importar inventario."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from io import BytesIO

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventario"

        headers = ["producto", "cantidad", "costo", "fecha", "descripcion"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                start_color="4F8CFF", end_color="4F8CFF", fill_type="solid"
            )
            cell.alignment = Alignment(horizontal="center")

        ejemplos = [
            ["Collar de Plata", 50, 120.00, "2026-01-15", "Stock inicial"],
            ["Aretes Dorados", 30, 85.50, "2026-01-15", "Stock inicial"],
            ["Pulsera de Oro", 20, 250.00, "2026-01-20", "Compra proveedor"],
            ["Anillo de Plata", 15, 95.00, "", ""],
        ]
        for fila in ejemplos:
            ws.append(fila)

        for col, w in zip("ABCDE", [25, 12, 12, 14, 28]):
            ws.column_dimensions[chr(64 + list("ABCDE").index(col) + 1)].width = w

        ws2 = wb.create_sheet("Instrucciones")
        instrucciones = [
            ("📋 INSTRUCCIONES DE IMPORTACIÓN", True),
            ("", False),
            ("1. Llena la hoja 'Inventario' con tus productos.", False),
            ("2. La columna 'producto' es obligatoria.", False),
            ("3. La columna 'cantidad' debe ser un número entero positivo.", False),
            ("4. La columna 'costo' es el costo unitario en C$.", False),
            ("5. La columna 'fecha' es opcional (formato YYYY-MM-DD).", False),
            ("   Si se omite, se usa la fecha actual.", False),
            ("6. La columna 'descripcion' es opcional.", False),
            ("", False),
            ("⚠️  No borres la fila de encabezados (fila 1).", False),
            (
                "⚠️  Si el producto ya existe en el Kardex, se agrega como nueva entrada.",
                False,
            ),
            ("⚠️  Productos con cantidad 0 o negativa se ignoran.", False),
        ]
        for i, (texto, bold) in enumerate(instrucciones, 1):
            cell = ws2.cell(row=i, column=1, value=texto)
            cell.font = Font(bold=bold, size=11 if bold else 10)
        ws2.column_dimensions["A"].width = 70

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from flask import send_file

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="Plantilla_Importar_Inventario.xlsx",
        )
    except ImportError:
        return "openpyxl no está instalado", 500



def _leer_excel_inventario(contenido, hoja_nombre):
    filas, headers_originales = [], []
    try:
        import openpyxl
        from io import BytesIO
        wb = openpyxl.load_workbook(BytesIO(contenido), data_only=True)
        if hoja_nombre and hoja_nombre in wb.sheetnames:
            ws = wb[hoja_nombre]
        else:
            ws = wb.active
        primera_fila = None
        for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
            if any(c for c in row if c is not None):
                primera_fila = row
                break
        if primera_fila is None:
            return [], [], f"La hoja '{ws.title}' está vacía."
        headers_originales = [str(c).strip() if c is not None else "" for c in primera_fila]
        headers_lower = [h.lower() for h in headers_originales]
        fila_inicio = None
        for idx, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
            if list(row) == list(primera_fila):
                fila_inicio = idx + 1
                break
        for row in ws.iter_rows(min_row=fila_inicio or 2, values_only=True):
            if any(c for c in row if c is not None):
                filas.append(dict(zip(headers_lower, row)))
    except Exception as e:
        return [], [], f"No se pudo leer el Excel: {e}"
    return filas, headers_originales, None


def _leer_csv_inventario(contenido):
    import csv, io
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = contenido.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = contenido.decode("latin-1", errors="replace")
    primera_linea = text.split("\n")[0] if text else ""
    sep = (";" if primera_linea.count(";") > primera_linea.count(",")
            else "\t" if primera_linea.count("\t") > primera_linea.count(",")
            else ",")
    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    headers_originales = reader.fieldnames or []
    filas = [{k.strip().lower(): v for k, v in row.items() if k} for row in reader]
    return filas, headers_originales, None


NOMBRES_PRODUCTO = {"producto","product","nombre","name","articulo","item",
    "descripcion_producto","art","codigo","code","referencia","ref",
    "mercaderia","mercancía","mercancia"}
NOMBRES_CANTIDAD = {"cantidad","qty","quantity","unidades","units","stock",
    "existencia","existencias","cant","inventario","piezas","pcs"}
NOMBRES_COSTO = {"costo","cost","precio","price","costo_unitario","unit_cost",
    "value","costo_unit","precio_unitario","pu","p.u.","c/u"}
NOMBRES_FECHA = {"fecha","date","fecha_entrada","fecha_compra","entry_date"}
NOMBRES_DESC = {"descripcion","description","desc","detalle","detail","nota","observacion"}


def _encontrar_columna(keys, nombres_set):
    for k in keys:
        if k in nombres_set:
            return k
    for k in keys:
        for n in nombres_set:
            if n in k or k in n:
                return k
    return None


def _mapear_columnas_inventario(headers_originales, filas):
    keys = list(filas[0].keys()) if filas else []
    col_producto = _encontrar_columna(keys, NOMBRES_PRODUCTO)
    col_cantidad = _encontrar_columna(keys, NOMBRES_CANTIDAD)
    col_costo = _encontrar_columna(keys, NOMBRES_COSTO)
    col_fecha = _encontrar_columna(keys, NOMBRES_FECHA)
    col_desc = _encontrar_columna(keys, NOMBRES_DESC)
    modo_auto = False
    if not col_producto and len(keys) >= 1:
        col_producto = keys[0]
        modo_auto = True
    if not col_cantidad and len(keys) >= 2:
        col_cantidad = keys[1]
        modo_auto = True
    if not col_costo and len(keys) >= 3:
        col_costo = keys[2]
    msg = None
    if not col_producto:
        msg = (f"No se encontró columna de producto. "
               f"Columnas en tu archivo: {', '.join(headers_originales)}. "
               f"Renómbralas como: producto, cantidad, costo")
    return col_producto, col_cantidad, col_costo, col_fecha, col_desc, modo_auto, msg


def _val_fila(fila, col):
    if not col:
        return None
    val = fila.get(col)
    if val is None:
        return None
    s = str(val).strip()
    return s if s not in ("", "None", "nan", "NaN", "-") else None


def _parsear_cantidad(raw):
    try:
        return int(float(raw.replace(",", "").replace(" ", "").replace("'", "")))
    except Exception:
        return 0


def _parsear_costo(raw):
    try:
        return float(raw.replace(",", "").replace(" ", "")
                     .replace("C$", "").replace("$", "").strip())
    except Exception:
        return 0.0


def _parsear_fecha(raw, hoy):
    if "/" in raw:
        parts = raw.split("/")
        try:
            if len(parts) == 3:
                d, m, a = parts
                if len(a) == 2:
                    a = "20" + a
                return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            pass
    return hoy


def _importar_filas_inventario(data, filas, col_producto, col_cantidad, col_costo, col_fecha, col_desc):
    from datetime import date as _date
    import kardex_peps
    hoy = _date.today().isoformat()
    importados, omitidos = 0, 0
    for fila in filas:
        producto = _val_fila(fila, col_producto)
        if not producto:
            omitidos += 1
            continue
        cantidad = _parsear_cantidad(_val_fila(fila, col_cantidad) or "0")
        costo = _parsear_costo(_val_fila(fila, col_costo) or "0")
        fecha = _parsear_fecha(_val_fila(fila, col_fecha) or "", hoy)
        if producto not in data["kardex"]:
            data["kardex"][producto] = []
            data["productos"][producto] = {"nombre": producto, "stock": 0, "costo_promedio": 0, "precio_venta": 0, "margen": 0}
            data["kardex_peps"][producto] = {"lotes": [], "stock_total": 0, "costo_promedio": 0, "precio_venta": 0, "margen": 0}
        if cantidad > 0:
            data = kardex_peps.agregar_entrada_peps(data, producto, fecha, cantidad, costo)
        importados += 1
    return data, importados, omitidos


@app.route("/kardex/importar", methods=["POST"])
def importar_inventario():
    from io import BytesIO
    import urllib.parse

    token = request.form.get("token", "")
    hoja_nombre = request.form.get("hoja_nombre", "")
    ext = request.form.get("ext", "")
    contenido = None

    if token and token in _archivos_temp:
        entrada = _archivos_temp.pop(token)
        contenido, ext = entrada["contenido"], entrada["ext"]
    else:
        archivo = request.files.get("archivo")
        if not archivo or archivo.filename == "":
            return redirect(url_for("kardex"))
        ext = archivo.filename.rsplit(".", 1)[-1].lower()
        contenido = archivo.read()

    if ext in ("xlsx", "xls"):
        filas, headers_originales, error_lectura = _leer_excel_inventario(contenido, hoja_nombre)
    elif ext == "csv":
        filas, headers_originales, error_lectura = _leer_csv_inventario(contenido)
    else:
        error_lectura = f"Formato '{ext}' no soportado. Usa .xlsx o .csv"
        filas, headers_originales = [], []

    if error_lectura:
        return redirect(url_for("kardex") + "?error=" + urllib.parse.quote(error_lectura))
    if not filas:
        msg = (f"La hoja seleccionada no tiene datos. Columnas detectadas: "
               f"{', '.join(headers_originales) or 'ninguna'}")
        return redirect(url_for("kardex") + "?error=" + urllib.parse.quote(msg))

    mapeo = _mapear_columnas_inventario(headers_originales, filas)
    col_producto, col_cantidad, col_costo, col_fecha, col_desc, modo_auto, error_col = mapeo
    if error_col:
        return redirect(url_for("kardex") + "?error=" + urllib.parse.quote(error_col))

    data = load_data()
    data.setdefault("kardex", {})
    data.setdefault("kardex_peps", {})
    data.setdefault("productos", {})
    data, importados, omitidos = _importar_filas_inventario(
        data, filas, col_producto, col_cantidad, col_costo, col_fecha, col_desc)
    save_data(data)

    qs = f"importados={importados}&errores={omitidos}"
    if modo_auto:
        qs += "&auto=1"
    return redirect(url_for("kardex") + "?" + qs)




@app.route("/kardex/eliminar_producto", methods=["POST"])
def eliminar_producto_kardex():
    """Elimina un producto y todos sus movimientos del Kardex."""
    data = load_data()
    nombre = request.form.get("producto", "").strip()
    if nombre:
        data["kardex"].pop(nombre, None)
        data.get("kardex_peps", {}).pop(nombre, None)
        data.get("productos", {}).pop(nombre, None)
        save_data(data)
    return redirect(url_for("kardex"))


@app.route("/kardex/renombrar_producto", methods=["POST"])
def renombrar_producto_kardex():
    """Renombra un producto manteniendo todos sus movimientos."""
    data = load_data()
    nombre_old = request.form.get("nombre_old", "").strip()
    nombre_new = request.form.get("nombre_new", "").strip()
    if (
        nombre_old
        and nombre_new
        and nombre_old in data["kardex"]
        and nombre_new not in data["kardex"]
    ):
        for seccion in ("kardex", "kardex_peps", "productos"):
            d = data.get(seccion, {})
            if nombre_old in d:
                d[nombre_new] = d.pop(nombre_old)
        save_data(data)
    return redirect(url_for("kardex"))


@app.route("/kardex/editar_movimiento", methods=["POST"])
def editar_movimiento_kardex():
    """Edita un movimiento individual del Kardex (fecha, descripcion, cantidad, costo)."""
    data = load_data()
    producto = request.form.get("producto", "").strip()
    try:
        idx = int(request.form.get("idx", -1) or -1)
    except (ValueError, TypeError):
        return redirect(url_for("kardex"))
    k = data["kardex"].get(producto, [])
    if 0 <= idx < len(k):
        mov = k[idx]
        mov["fecha"] = request.form.get("fecha", mov.get("fecha", ""))
        mov["descripcion"] = request.form.get("descripcion", mov.get("descripcion", ""))
        nuevo_pv = mov.get("precio_venta", 0)
        try:
            nueva_cant = int(
                float(request.form.get("cantidad", mov.get("cantidad", 0)))
            )
            nuevo_costo = float(request.form.get("costo", mov.get("costo", 0)))
            nuevo_pv = float(request.form.get("precio_venta", mov.get("precio_venta", 0)))
            mov["cantidad"] = nueva_cant
            mov["costo"] = nuevo_costo
            mov["precio_venta"] = nuevo_pv
            mov["total"] = nueva_cant * nuevo_costo
        except (ValueError, TypeError):
            pass
        
        data["kardex"][producto] = k
        if nuevo_pv > 0:
            peps = data.get("kardex_peps", {}).get(producto, {})
            if peps:
                peps["precio_venta"] = nuevo_pv
            prod = data.get("productos", {}).get(producto, {})
            if isinstance(prod, dict):
                prod["precio_venta"] = nuevo_pv
        data = _reconstruir_peps(data, producto)
        save_data(data)
    return redirect(url_for("kardex"))


@app.route("/kardex/eliminar_movimiento", methods=["POST"])
def eliminar_movimiento_kardex():
    """Elimina un movimiento individual y recalcula saldos."""
    data = load_data()
    producto = request.form.get("producto", "").strip()
    try:
        idx = int(request.form.get("idx", -1) or -1)
    except (ValueError, TypeError):
        return redirect(url_for("kardex"))
    k = data["kardex"].get(producto, [])
    if 0 <= idx < len(k):
        k.pop(idx)
        data["kardex"][producto] = k
        data = _reconstruir_peps(data, producto)
        save_data(data)
    return redirect(url_for("kardex"))


def _reconstruir_peps(data, producto):
    """
    Reconstruye los lotes PEPS de un producto a partir de su historial kardex.
    Procesa entradas, salidas y ajustes de forma correcta.
    """
    try:
        movs = list(data["kardex"].get(producto, []))  # ← copia para evitar loop infinito
        len_original = len(data["kardex"].get(producto, []))

        old_peps = data.get("kardex_peps", {}).get(producto, {})
        old_prod = data.get("productos", {}).get(producto, {})
        if isinstance(old_prod, dict):
            pv = old_peps.get("precio_venta", 0) or old_prod.get("precio_venta", 0)
            mg = old_peps.get("margen", 30) or old_prod.get("margen", 30)
        else:
            pv = old_peps.get("precio_venta", 0)
            mg = old_peps.get("margen", 30)

        if "kardex_peps" not in data:
            data["kardex_peps"] = {}
        data["kardex_peps"][producto] = {
            "lotes": [],
            "stock_total": 0,
            "costo_promedio": 0,
            "precio_venta": pv,
            "margen": mg,
        }

        if producto in data["kardex"]:
            del data["kardex"][producto][:]

        saldo_acum = 0

        for m in movs:
            if m.get("tipo") == "entrada" and m.get("cantidad", 0) > 0:
                cant = m["cantidad"]
                data = kardex_peps.agregar_entrada_peps(
                    data, producto,
                    m.get("fecha", ""), cant,
                    m.get("costo", 0), m.get("precio_venta", 0),
                )
                saldo_acum += cant
            elif m.get("tipo") == "salida" and m.get("cantidad", 0) > 0:
                try:
                    data, _, _ = kardex_peps.procesar_salida_peps(
                        data, producto, m.get("fecha", ""), m.get("cantidad", 0)
                    )
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                saldo_acum -= m["cantidad"]
            elif m.get("tipo") == "ajuste" and m.get("cantidad", 0) > 0:
                stock_actual = data["kardex_peps"][producto]["stock_total"]
                delta = m["cantidad"] - stock_actual
                if delta > 0:
                    data = kardex_peps.agregar_entrada_peps(
                        data, producto, m.get("fecha", ""), delta,
                        m.get("costo", 0), m.get("precio_venta", 0),
                    )
                elif delta < 0:
                    try:
                        data, _, _ = kardex_peps.procesar_salida_peps(
                            data, producto, m.get("fecha", ""), abs(delta),
                        )
                    except Exception:
                        pass
                saldo_acum = m["cantidad"]

        data["kardex"][producto] = movs
        saldo = 0
        for mov in data["kardex"][producto]:
            c = mov.get("cantidad", 0)
            if mov.get("tipo") in ("entrada",):
                saldo += c
            elif mov.get("tipo") in ("salida",):
                saldo -= c
            elif mov.get("tipo") == "ajuste":
                saldo = c
            mov["saldo"] = saldo
            mov["total"] = mov.get("cantidad", 0) * mov.get("costo", 0)
    except Exception as e:
        if "kardex_peps" not in data:
            data["kardex_peps"] = {}
        if producto not in data["kardex_peps"]:
            data["kardex_peps"][producto] = {
                "lotes": [],
                "stock_total": 0,
                "costo_promedio": 0,
            }
    
    return data


@app.route("/apagar", methods=["POST"])
def apagar():
    import threading
    from flask import make_response

    def shutdown():
        import time

        time.sleep(0.6)
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception:
            os._exit(0)

    t = threading.Thread(target=shutdown, daemon=True)
    t.start()

    resp = make_response(render_template("apagar.html"))
    resp.headers["Connection"] = "close"
    return resp




@app.route("/api/backup_json")
def api_backup_json():
    """Exporta los datos actuales como archivo JSON"""
    data = load_data()
    from flask import make_response
    import json

    json_str = json.dumps(data, indent=2, default=str)
    resp = make_response(json_str)
    resp.headers["Content-Disposition"] = "attachment; filename=fg_backup.json"
    resp.headers["Content-Type"] = "application/json"
    return resp


@app.route("/api/copia_db")
def api_copia_db():
    """Crea una copia de la base de datos SQLite"""
    import shutil
    from flask import make_response
    from io import BytesIO

    db_path = db_internal.get_db_path()
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            data = f.read()
        resp = make_response(data)
        resp.headers["Content-Disposition"] = "attachment; filename=fg_db_backup.db"
        resp.headers["Content-Type"] = "application/octet-stream"
        return resp
    return jsonify({"ok": False, "error": "Base de datos no encontrada"}), 404


@app.route("/api/importar_json", methods=["POST"])
def api_importar_json():
    """Importa un JSON de backup y reemplaza los datos actuales"""
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"ok": False, "error": "No se recibió archivo"})
    try:
        data = json.loads(archivo.read().decode("utf-8"))
        required = ["cuentas", "diario", "productos", "kardex", "kardex_peps", "pos_historial"]
        for key in required:
            if key not in data:
                data[key] = {} if key in ("kardex", "kardex_peps", "productos", "cuentas") else []
        save_data(data)
        return jsonify({"ok": True, "message": f"Importado: {len(data.get('diario', []))} asientos, {len(data.get('pos_historial', []))} ventas"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/importar_db", methods=["POST"])
def api_importar_db():
    """Importa una base de datos SQLite"""
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"ok": False, "error": "No se recibió archivo"})

    db_path = db_internal.get_db_path()
    try:
        archivo.save(db_path)
        return jsonify({"ok": True, "message": "Base de datos importada"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ver_db")
def api_ver_db():
    """Muestra el contenido de la base de datos como HTML"""
    import sqlite3

    db_path = db_internal.get_db_path()

    html = "<html><head><title>Ver DB</title><style>"
    html += "body{font-family:monospace;background:#1a1d2e;color:#e2e4eb;padding:20px}"
    html += "table{border-collapse:collapse;width:100%}"
    html += "th,td{border:1px solid #2a2d42;padding:8px;text-align:left}"
    html += "th{background:#2a2d42}"
    html += "</style></head><body>"
    html += "<h1>Contenido de Base de Datos</h1>"

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()

        for tabla in tablas:
            nombre_tabla = tabla[0]
            html += f"<h2>Tabla: {nombre_tabla}</h2>"
            cursor.execute(f"SELECT * FROM {nombre_tabla} LIMIT 100")
            rows = cursor.fetchall()

            if rows:
                html += "<table><tr>"
                for col in rows[0].keys():
                    html += f"<th>{col}</th>"
                html += "</tr>"

                for row in rows:
                    html += "<tr>"
                    for col in row:
                        html += f"<td>{col}</td>"
                    html += "</tr>"
                html += "</table>"
            else:
                html += "<p>Sin datos</p>"

        conn.close()
    except Exception as e:
        html += f"<p>Error: {e}</p>"

    html += "</body></html>"
    return html


@app.route("/api/restaurar_json", methods=["POST"])
def api_restaurar_json():
    """Restaura los datos desde un archivo JSON"""
    try:
        data_json = request.get_data(as_text=True)
        data = json.loads(data_json)

        if "cuentas" not in data:
            return jsonify({"ok": False, "error": "Archivo JSON inválido"}), 400

        save_data(data)
        return jsonify({"ok": True, "message": "Datos restaurados correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/borrar_todo", methods=["POST"])
def api_borrar_todo():
    """Borra todos los datos (reset completo)"""
    try:
        data_vacio = empty_data()
        data_vacio = audit_log(data_vacio, "borrar_todo", "Todos los datos fueron eliminados")
        save_data(data_vacio)
        return jsonify({"ok": True, "message": "Todos los datos han sido borrados"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/saldos_periodo")
def api_saldos_periodo():
    """Calcula saldo inicial, movimientos del período y saldo final para todas las cuentas."""
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    if not hasta:
        return jsonify({"error": "Se requiere 'hasta'"}), 400

    data = load_data()
    cuentas = data["cuentas"]

    saldo_inicial = defaultdict(lambda: {"debe": 0, "haber": 0})
    movimientos_periodo = defaultdict(lambda: {"debe": 0, "haber": 0})

    for entry in data.get("diario", []):
        fecha = entry.get("fecha", "")
        for mov in entry.get("movimientos", []):
            cuenta = mov["cuenta"]
            monto = mov["monto"]
            if mov["tipo"] == "Debe":
                if not desde or fecha < desde:
                    saldo_inicial[cuenta]["debe"] += monto
                if desde and desde <= fecha <= hasta:
                    movimientos_periodo[cuenta]["debe"] += monto
                if not desde and fecha <= hasta:
                    saldo_inicial[cuenta]["debe"] += monto
            else:
                if not desde or fecha < desde:
                    saldo_inicial[cuenta]["haber"] += monto
                if desde and desde <= fecha <= hasta:
                    movimientos_periodo[cuenta]["haber"] += monto
                if not desde and fecha <= hasta:
                    saldo_inicial[cuenta]["haber"] += monto

    for aj in data.get("ajustes", []):
        fecha = aj.get("fecha", "")
        for mov in aj.get("movimientos", []):
            cuenta = mov["cuenta"]
            monto = mov["monto"]
            if mov["tipo"] == "Debe":
                if not desde or fecha < desde:
                    saldo_inicial[cuenta]["debe"] += monto
                if desde and desde <= fecha <= hasta:
                    movimientos_periodo[cuenta]["debe"] += monto
                if not desde and fecha <= hasta:
                    saldo_inicial[cuenta]["debe"] += monto
            else:
                if not desde or fecha < desde:
                    saldo_inicial[cuenta]["haber"] += monto
                if desde and desde <= fecha <= hasta:
                    movimientos_periodo[cuenta]["haber"] += monto
                if not desde and fecha <= hasta:
                    saldo_inicial[cuenta]["haber"] += monto

    resultado = []
    for cod in sorted(cuentas.keys()):
        info = cuentas[cod]
        tipo = info.get("tipo", "")
        ts = tipo_saldo(tipo)

        si = saldo_inicial[cod]
        mp = movimientos_periodo[cod]
        sf_debe = si["debe"] + mp["debe"]
        sf_haber = si["haber"] + mp["haber"]

        saldo_ini = (si["debe"] - si["haber"]) if ts == "Debe" else (si["haber"] - si["debe"])
        saldo_mov = (mp["debe"] - mp["haber"]) if ts == "Debe" else (mp["haber"] - mp["debe"])
        saldo_fin = (sf_debe - sf_haber) if ts == "Debe" else (sf_haber - sf_debe)

        if si["debe"] or si["haber"] or mp["debe"] or mp["haber"]:
            resultado.append({
                "codigo": cod,
                "nombre": info.get("nombre", cod),
                "tipo": tipo,
                "saldo_inicial": round(saldo_ini, 2),
                "mov_debe": round(mp["debe"], 2),
                "mov_haber": round(mp["haber"], 2),
                "movimientos": round(saldo_mov, 2),
                "saldo_final": round(saldo_fin, 2),
            })

    return jsonify({
        "desde": desde,
        "hasta": hasta,
        "cuentas": resultado,
    })


@app.route("/api/comparar_periodos")
def api_comparar_periodos():
    """Compara dos períodos y retorna totales de ingresos, gastos, utilidad y asientos."""
    desde1 = request.args.get("desde1", "")
    hasta1 = request.args.get("hasta1", "")
    desde2 = request.args.get("desde2", "")
    hasta2 = request.args.get("hasta2", "")

    if not hasta1 or not hasta2:
        return jsonify({"error": "Se requieren ambas fechas 'hasta'"}), 400

    data = load_data()
    cuentas = data["cuentas"]

    def _calcular_periodo(d, h):
        ing = 0
        gas = 0
        asientos = 0
        cuentas_detalle = defaultdict(lambda: {"debe": 0, "haber": 0})

        for entry in data.get("diario", []):
            fecha = entry.get("fecha", "")
            if d <= fecha <= h:
                asientos += 1
                for mov in entry.get("movimientos", []):
                    cuenta = mov["cuenta"]
                    monto = mov["monto"]
                    if mov["tipo"] == "Debe":
                        cuentas_detalle[cuenta]["debe"] += monto
                    else:
                        cuentas_detalle[cuenta]["haber"] += monto

                    info = cuentas.get(cuenta, {})
                    tipo = info.get("tipo", "")
                    if tipo == "Ingreso" and mov["tipo"] == "Haber":
                        ing += monto
                    elif tipo == "Gasto" and mov["tipo"] == "Debe":
                        gas += monto

        for aj in data.get("ajustes", []):
            fecha = aj.get("fecha", "")
            if d <= fecha <= h:
                for mov in aj.get("movimientos", []):
                    cuenta = mov["cuenta"]
                    monto = mov["monto"]
                    if mov["tipo"] == "Debe":
                        cuentas_detalle[cuenta]["debe"] += monto
                    else:
                        cuentas_detalle[cuenta]["haber"] += monto

                    info = cuentas.get(cuenta, {})
                    tipo = info.get("tipo", "")
                    if tipo == "Ingreso" and mov["tipo"] == "Haber":
                        ing += monto
                    elif tipo == "Gasto" and mov["tipo"] == "Debe":
                        gas += monto

        return {
            "ingresos": round(ing, 2),
            "gastos": round(gas, 2),
            "utilidad": round(ing - gas, 2),
            "asientos": asientos,
            "cuentas": dict(cuentas_detalle),
        }

    p1 = _calcular_periodo(desde1, hasta1)
    p2 = _calcular_periodo(desde2, hasta2)

    todas_cuentas = set(list(p1["cuentas"].keys()) + list(p2["cuentas"].keys()))
    comparacion_cuentas = []

    for cod in sorted(todas_cuentas):
        info = cuentas.get(cod, {})
        tipo = info.get("tipo", "")
        ts = tipo_saldo(tipo)

        c1 = p1["cuentas"].get(cod, {"debe": 0, "haber": 0})
        c2 = p2["cuentas"].get(cod, {"debe": 0, "haber": 0})

        saldo1 = (c1["debe"] - c1["haber"]) if ts == "Debe" else (c1["haber"] - c1["debe"])
        saldo2 = (c2["debe"] - c2["haber"]) if ts == "Debe" else (c2["haber"] - c2["debe"])

        diff = saldo1 - saldo2
        porcentaje = ((diff / abs(saldo2) * 100) if saldo2 != 0 else (100 if diff > 0 else 0))

        comparacion_cuentas.append({
            "codigo": cod,
            "nombre": info.get("nombre", cod),
            "tipo": tipo,
            "periodo1": round(saldo1, 2),
            "periodo2": round(saldo2, 2),
            "diferencia": round(diff, 2),
            "porcentaje": round(porcentaje, 1),
        })

    return jsonify({
        "periodo1": {"desde": desde1, "hasta": hasta1, **p1},
        "periodo2": {"desde": desde2, "hasta": hasta2, **p2},
        "cuentas": comparacion_cuentas,
    })


@app.route("/api/vista_previa")
def api_vista_previa():
    """Retorna datos reales para la vista previa de exportación."""
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    hojas = request.args.getlist("hojas")

    data = load_data()
    if not hasta:
        hasta = "9999-12-31"

    diario_filtrado = [e for e in data.get("diario", []) if (not desde or desde <= e.get("fecha", "")) and e.get("fecha", "") <= hasta]
    ajustes_filtrados = [a for a in data.get("ajustes", []) if (not desde or desde <= a.get("fecha", "")) and a.get("fecha", "") <= hasta]

    import copy
    data_filtrada = copy.deepcopy(data)
    data_filtrada["diario"] = diario_filtrado
    data_filtrada["ajustes"] = ajustes_filtrados

    resultado = {}

    if "balanza" in hojas:
        try:
            from services.calculos import calcular_balanza
            balanza, td, th, tsd, tsh = calcular_balanza(data_filtrada)
            resultado["balanza"] = {
                "total_debe": round(td, 2),
                "total_haber": round(th, 2),
                "cuentas": len(balanza),
                "diferencia": round(abs(td - th), 2),
            }
        except:
            pass

    if "er" in hojas:
        try:
            from services.calculos import calcular_estado_resultados
            di, ti, dg, tg, util = calcular_estado_resultados(data_filtrada)
            resultado["er"] = {
                "ingresos": round(ti, 2),
                "gastos": round(tg, 2),
                "utilidad": round(util, 2),
            }
        except:
            pass

    if "bg" in hojas:
        try:
            from services.calculos import calcular_balance_general
            activos, ta, pasivos, tp, capital, tc = calcular_balance_general(data_filtrada)
            resultado["bg"] = {
                "activos": round(ta, 2),
                "pasivos": round(tp, 2),
                "capital": round(tc, 2),
                "verificacion": abs(ta - (tp + tc)) < 0.01,
            }
        except:
            pass

    if "diario" in hojas:
        resultado["diario"] = {
            "count": len(diario_filtrado),
            "primero": diario_filtrado[0].get("fecha", "-") if diario_filtrado else "-",
            "ultimo": diario_filtrado[-1].get("fecha", "-") if diario_filtrado else "-",
        }

    if "pos" in hojas:
        pos = [v for v in data.get("pos_historial", []) if (not desde or desde <= v.get("fecha", "")) and v.get("fecha", "") <= hasta]
        total_pos = sum(v.get("total", 0) for v in pos)
        util_pos = sum(v.get("utilidad", 0) for v in pos)
        resultado["pos"] = {
            "count": len(pos),
            "total": round(total_pos, 2),
            "utilidad": round(util_pos, 2),
        }

    if "kardex" in hojas:
        kardex = data.get("kardex", {})
        valor_total = 0
        for prod, regs in kardex.items():
            if regs:
                ultimo = regs[-1]
                valor_total += ultimo.get("saldo_costo_total", 0)
        resultado["kardex"] = {
            "count": len(kardex),
            "valor": round(valor_total, 2),
        }

    return jsonify(resultado)


@app.route("/api/rango_fechas")
def api_rango_fechas():
    """Retorna la primera y última fecha de registros en el sistema."""
    data = load_data()
    
    todas_fechas = []
    
    for entry in data.get("diario", []):
        f = entry.get("fecha", "")
        if f:
            todas_fechas.append(f)
    
    for aj in data.get("ajustes", []):
        f = aj.get("fecha", "")
        if f:
            todas_fechas.append(f)
    
    for v in data.get("pos_historial", []):
        f = v.get("fecha", "")
        if f:
            todas_fechas.append(f)
    
    for mov in data.get("caja_movimientos", []):
        f = mov.get("fecha", "")
        if f:
            todas_fechas.append(f)
    
    if todas_fechas:
        todas_fechas.sort()
        return jsonify({
            "primera": todas_fechas[0],
            "ultima": todas_fechas[-1],
            "total_registros": len(todas_fechas),
        })
    else:
        return jsonify({
            "primera": "",
            "ultima": "",
            "total_registros": 0,
        })


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
