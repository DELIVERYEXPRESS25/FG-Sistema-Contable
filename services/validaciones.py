"""
Validaciones para movimientos del kardex.
Previene: fechas futuras, stock insuficiente, datos faltantes.
"""

from datetime import date, datetime


def validar_fecha(fecha_str):
    """
    Valida que la fecha no sea futura.
    Retorna True si es válida, lanza ValueError si no.
    """
    if not fecha_str:
        raise ValueError("La fecha es obligatoria")
    try:
        fecha_mov = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Formato de fecha inválido: {fecha_str}. Use YYYY-MM-DD")
    if fecha_mov > date.today():
        raise ValueError(f"La fecha {fecha_str} es futura. No se permiten fechas posteriores a hoy ({date.today().isoformat()})")
    return True


def validar_cantidad(cantidad):
    """Valida que la cantidad sea positiva."""
    if not isinstance(cantidad, (int, float)):
        raise ValueError("La cantidad debe ser un número")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a cero")
    return True


def validar_stock_para_salida(data, producto, cantidad):
    """
    Valida que haya stock suficiente para una salida.
    """
    peps = data.get("kardex_peps", {}).get(producto, {})
    stock = peps.get("stock_total", 0)
    if stock < cantidad:
        raise ValueError(
            f"Stock insuficiente para {producto}. "
            f"Disponible: {int(stock)}, Solicitado: {int(cantidad)}"
        )
    return True


def validar_entrada(data, producto, fecha, cantidad):
    """Validación completa para una entrada al kardex."""
    validar_fecha(fecha)
    validar_cantidad(cantidad)
    return True


def validar_salida(data, producto, fecha, cantidad):
    """Validación completa para una salida del kardex."""
    validar_fecha(fecha)
    validar_cantidad(cantidad)
    validar_stock_para_salida(data, producto, cantidad)
    return True
