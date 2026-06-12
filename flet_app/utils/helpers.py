"""
══════════════════════════════════════════════════════════════════════════════
 Funciones Helper para la App
══════════════════════════════════════════════════════════════════════════════
"""

from collections import defaultdict


def format_money(amount: float) -> str:
    """Formatea un número como货币."""
    return f"C$ {amount:,.2f}"


def calcular_utilidad(data: dict) -> float:
    """Calcula la utilidad del período."""
    cuentas = data.get("cuentas", {})
    diario = data.get("diario", [])

    # Calcular ingresos y gastos desde el diario
    ingresos = 0
    gastos = 0

    for entry in diario:
        for mov in entry.get("movimientos", []):
            cuenta = mov.get("cuenta", "")
            monto = mov.get("monto", 0)
            tipo = mov.get("tipo", "")

            if cuenta in cuentas:
                info_cuenta = cuentas[cuenta]
                if info_cuenta.get("tipo") == "Ingreso" and tipo == "Haber":
                    ingresos += monto
                elif info_cuenta.get("tipo") == "Gasto" and tipo == "Debe":
                    gastos += monto

    return ingresos - gastos


def calcular_totales(data: dict) -> dict:
    """Calcula totales de ingresos, gastos, activos, pasivos."""
    cuentas = data.get("cuentas", {})
    diario = data.get("diario", [])

    totales = defaultdict(float)

    for entry in diario:
        for mov in entry.get("movimientos", []):
            cuenta = mov.get("cuenta", "")
            monto = mov.get("monto", 0)
            tipo = mov.get("tipo", "")

            if cuenta in cuentas:
                info_cuenta = cuentas[cuenta]
                cuenta_tipo = info_cuenta.get("tipo", "")

                if cuenta_tipo == "Ingreso" and tipo == "Haber":
                    totales["ingresos"] += monto
                elif cuenta_tipo == "Gasto" and tipo == "Debe":
                    totales["gastos"] += monto
                elif cuenta_tipo == "Activo":
                    if tipo == "Debe":
                        totales["activos"] += monto
                    else:
                        totales["activos"] -= monto
                elif cuenta_tipo == "Pasivo":
                    if tipo == "Haber":
                        totales["pasivos"] += monto
                    else:
                        totales["pasivos"] -= monto

    return dict(totales)


def get_next_id(data: dict, key: str) -> int:
    """Retorna el siguiente ID único para una lista."""
    if key not in data or not data[key]:
        return 1
    items = data[key]
    max_id = 0
    for item in items:
        if isinstance(item, dict) and "id" in item:
            if item["id"] > max_id:
                max_id = item["id"]
    return max_id + 1


def tipo_saldo(tipo_cuenta: str) -> str:
    """Retorna el tipo de saldo para una cuenta."""
    return "Debe" if tipo_cuenta in ["Activo", "Gasto"] else "Haber"


def calcular_mayor(data: dict) -> dict:
    """Calcula el libro mayor."""
    mayor = defaultdict(lambda: {"debe": 0, "haber": 0, "movimientos": []})

    for entry in data.get("diario", []):
        for mov in entry.get("movimientos", []):
            cuenta = mov.get("cuenta", "")
            monto = mov.get("monto", 0)
            tipo = mov.get("tipo", "")

            if tipo == "Debe":
                mayor[cuenta]["debe"] += monto
            else:
                mayor[cuenta]["haber"] += monto

            mayor[cuenta]["movimientos"].append(
                {
                    "fecha": entry.get("fecha", ""),
                    "descripcion": entry.get("descripcion", ""),
                    "tipo": tipo,
                    "monto": monto,
                }
            )

    return dict(mayor)


def calcular_balanza(data: dict) -> tuple:
    """Calcula la balanza de comprobación."""
    mayor = calcular_mayor(data)
    cuentas = data.get("cuentas", {})

    balanza = []
    total_debe = 0
    total_haber = 0

    for codigo in sorted(cuentas.keys()):
        info = cuentas[codigo]
        debe = mayor.get(codigo, {}).get("debe", 0)
        haber = mayor.get(codigo, {}).get("haber", 0)

        ts = tipo_saldo(info.get("tipo", ""))
        if ts == "Debe":
            saldo = debe - haber
        else:
            saldo = haber - debe

        balanza.append(
            {
                "codigo": codigo,
                "nombre": info.get("nombre", ""),
                "tipo": info.get("tipo", ""),
                "debe": debe,
                "haber": haber,
                "saldo": saldo,
            }
        )

        total_debe += debe
        total_haber += haber

    return balanza, total_debe, total_haber
