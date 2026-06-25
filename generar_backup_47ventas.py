import json, random, copy
from datetime import date, timedelta
import sqlite3

random.seed(42)

# ── read from SQLite ──
conn = sqlite3.connect('.colectivo_fg.db')
cur = conn.cursor()
cur.execute("SELECT value FROM app_data WHERE key='main_data'")
row = cur.fetchone()
data = json.loads(row[0])
conn.close()

# ── products with stock from kardex_peps ──
peps = data.get('kardex_peps', {})
productos_con_stock = []
for p, info in peps.items():
    max_rest = max((l.get('cantidad_restante', 0) for l in info.get('lotes', [])), default=0)
    if max_rest > 0:
        productos_con_stock.append((p, info, max_rest))

# Current max IDs
next_id = max(e['id'] for e in data.get('diario', [])) + 1 if data.get('diario') else 1
next_caja_id = max(e['id'] for e in data.get('caja_movimientos', [])) + 1 if data.get('caja_movimientos') else 1
next_ref = len(data.get('pos_historial', []))  # POS-0016 -> 16

# Spread 31 sales across 19 Oct – 31 Oct
start = date(2025, 10, 19)
end = date(2025, 10, 31)
total_days = (end - start).days + 1
sales_per_day = [0] * total_days
for _ in range(31):
    idx = random.randint(0, total_days - 1)
    sales_per_day[idx] += 1

for day_offset, num_sales in enumerate(sales_per_day):
    if num_sales == 0:
        continue
    d = start + timedelta(days=day_offset)
    fecha = d.isoformat()

    for _ in range(num_sales):
        next_ref += 1
        ref = f"POS-{next_ref:04d}"

        # pick 3–7 items
        num_items = random.randint(3, 7)
        candidates = [p for p in productos_con_stock if p[2] > 0]
        if not candidates or len(candidates) < 2:
            break
        selected = random.sample(candidates, min(num_items, len(candidates)))

        lineas = []
        total_venta = 0.0
        total_costo = 0.0
        for prod_name, prod_info, _ in selected:
            lotes = [l for l in prod_info.get('lotes', []) if l.get('cantidad_restante', 0) > 0]
            if not lotes:
                continue
            lote = lotes[0]
            max_q = lote['cantidad_restante']
            qty = random.randint(1, min(2, max_q))

            pv = prod_info.get('precio_venta', 0)
            cu = lote.get('costo_unitario', 0)
            subtotal = pv * qty
            costo_total_item = cu * qty

            lote['cantidad_restante'] -= qty
            prod_info['stock_total'] -= qty
            # update the max_rest in the candidate list
            for j, (cn, ci, _) in enumerate(productos_con_stock):
                if cn == prod_name:
                    productos_con_stock[j] = (cn, ci, max((ll.get('cantidad_restante', 0) for ll in ci.get('lotes', [])), default=0))
                    break

            lineas.append({
                "producto": prod_name,
                "cantidad": qty,
                "precio_unitario": pv,
                "subtotal": subtotal,
                "costo_unitario": cu,
                "costo_total": costo_total_item,
            })
            total_venta += subtotal
            total_costo += costo_total_item

        if not lineas:
            continue

        utilidad = total_venta - total_costo

        # pos_historial
        data.setdefault('pos_historial', []).append({
            "ref": ref,
            "fecha": fecha,
            "cliente": "Cliente general",
            "forma_pago": "Efectivo",
            "lineas": lineas,
            "total": total_venta,
            "costo": total_costo,
            "utilidad": utilidad,
        })

        # diario
        data.setdefault('diario', []).append({
            "id": next_id,
            "fecha": fecha,
            "descripcion": f"Venta POS - Cliente general (Efectivo)",
            "ref": ref,
            "movimientos": [
                {"cuenta": "1.1.01", "tipo": "Debe", "monto": total_venta},
                {"cuenta": "4.1.01", "tipo": "Haber", "monto": total_venta},
                {"cuenta": "5.1", "tipo": "Debe", "monto": total_costo},
                {"cuenta": "1.1.04", "tipo": "Haber", "monto": total_costo},
            ]
        })
        next_id += 1

        # kardex
        data.setdefault('kardex', {})
        for linea in lineas:
            pname = linea['producto']
            data['kardex'].setdefault(pname, [])
            saldo_actual = data['kardex'][pname][-1]['saldo'] if data['kardex'][pname] else 0
            new_saldo = saldo_actual - linea['cantidad']
            data['kardex'][pname].append({
                "fecha": fecha,
                "tipo": "salida",
                "cantidad": linea['cantidad'],
                "costo": linea['costo_unitario'],
                "precio_venta": linea['precio_unitario'],
                "total": linea['costo_total'],
                "saldo": new_saldo,
                "descripcion": f"Salida PEPS - 1 lote(s) usado(s)",
                "lotes_usados": [
                    {"fecha_entrada": "2025-10-01", "cantidad": linea['cantidad'],
                     "costo_unitario": linea['costo_unitario'], "costo_total": linea['costo_total']}
                ]
            })

        # caja_movimientos
        data.setdefault('caja_movimientos', []).append({
            "id": next_caja_id,
            "fecha": fecha,
            "descripcion": f"Venta POS - Cliente general",
            "tipo": "Debe",
            "monto": total_venta,
            "cuenta": "1.1.01",
            "ref_diario": next_id - 1,
        })
        next_caja_id += 1

# ── Save backup ──
output = 'backup_47ventas.json'
with open(output, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

pos_total = len(data['pos_historial'])
total_cs = sum(v['total'] for v in data['pos_historial'])
sell_count = sum(len(v['lineas']) for v in data['pos_historial'])
print(f"Backup guardado en {output}")
print(f"Ventas: {pos_total}")
print(f"Total ventas: C${total_cs:,.2f}")
print(f"Total items vendidos: {sell_count}")
