from datetime import datetime
from collections import deque


class LotePEPS:
    """Representa un lote de inventario con fecha de entrada."""
    def __init__(self, fecha, cantidad, costo_unitario):
        self.fecha = fecha
        self.cantidad = cantidad
        self.costo_unitario = costo_unitario
        self.cantidad_restante = cantidad
    
    def to_dict(self):
        return {
            'fecha': self.fecha,
            'cantidad': self.cantidad,
            'costo_unitario': self.costo_unitario,
            'cantidad_restante': self.cantidad_restante
        }
    
    @staticmethod
    def from_dict(data):
        lote = LotePEPS(
            data['fecha'],
            data['cantidad'],
            data['costo_unitario']
        )
        lote.cantidad_restante = data.get('cantidad_restante', data['cantidad'])
        return lote


def agregar_entrada_peps(data, producto_codigo, fecha, cantidad, costo_unitario, precio_venta=0):
    """
    Agrega una entrada al inventario PEPS.
    
    Args:
        data: Diccionario completo de datos
        producto_codigo: Código del producto
        fecha: Fecha de entrada (YYYY-MM-DD)
        cantidad: Cantidad que entra
        costo_unitario: Costo por unidad
    
    Returns:
        dict: Data actualizado
    """
    if 'kardex_peps' not in data:
        data['kardex_peps'] = {}
    
    if producto_codigo not in data['kardex_peps']:
        data['kardex_peps'][producto_codigo] = {
            'lotes': [],
            'stock_total': 0,
            'costo_promedio': 0,
            'precio_venta': precio_venta,
            'margen': 30,
        }
    elif precio_venta > 0:
        data['kardex_peps'][producto_codigo]['precio_venta'] = precio_venta

    if precio_venta > 0 and 'productos' in data and producto_codigo in data['productos']:
        prod = data['productos'][producto_codigo]
        if isinstance(prod, dict):
            if not prod.get('precio_venta'):
                prod['precio_venta'] = precio_venta
            if not prod.get('margen') and data['kardex_peps'][producto_codigo].get('margen'):
                prod['margen'] = data['kardex_peps'][producto_codigo]['margen']
    
    lote = LotePEPS(fecha, cantidad, costo_unitario)
    data['kardex_peps'][producto_codigo]['lotes'].append(lote.to_dict())
    
    data['kardex_peps'][producto_codigo]['stock_total'] += cantidad
    
    data = recalcular_costo_promedio(data, producto_codigo)
    
    if 'kardex' not in data:
        data['kardex'] = {}
    if producto_codigo not in data['kardex']:
        data['kardex'][producto_codigo] = []
    
    saldo = (data['kardex'][producto_codigo][-1]['saldo'] if data['kardex'][producto_codigo] else 0) + cantidad
    
    data['kardex'][producto_codigo].append({
        'fecha': fecha,
        'tipo': 'entrada',
        'cantidad': cantidad,
        'costo': costo_unitario,
        'precio_venta': precio_venta,
        'total': cantidad * costo_unitario,
        'saldo': saldo,
        'descripcion': f'Entrada - Lote {len(data["kardex_peps"][producto_codigo]["lotes"])}'
    })
    
    return data

def procesar_salida_peps(data, producto_codigo, fecha, cantidad_solicitada):
    """
    Procesa una salida usando PEPS.
    
    Returns:
        tuple: (data actualizado, costo_total, lista de lotes usados)
    """
    if 'kardex_peps' not in data or producto_codigo not in data['kardex_peps']:
        raise ValueError(f"Producto {producto_codigo} no tiene inventario PEPS")
    
    producto_peps = data['kardex_peps'][producto_codigo]
    
    if producto_peps['stock_total'] < cantidad_solicitada:
        raise ValueError(f"Stock insuficiente. Disponible: {producto_peps['stock_total']}, Solicitado: {cantidad_solicitada}")
    
    cantidad_pendiente = cantidad_solicitada
    costo_total = 0
    lotes_usados = []
    
    for lote_dict in producto_peps['lotes']:
        if cantidad_pendiente <= 0:
            break
        
        if lote_dict['cantidad_restante'] > 0:
            cantidad_tomar = min(cantidad_pendiente, lote_dict['cantidad_restante'])
            
            costo_lote = cantidad_tomar * lote_dict['costo_unitario']
            costo_total += costo_lote
            
            lote_dict['cantidad_restante'] -= cantidad_tomar
            
            lotes_usados.append({
                'fecha_entrada': lote_dict['fecha'],
                'cantidad': cantidad_tomar,
                'costo_unitario': lote_dict['costo_unitario'],
                'costo_total': costo_lote
            })
            
            cantidad_pendiente -= cantidad_tomar
    
    producto_peps['stock_total'] -= cantidad_solicitada
    
    data = recalcular_costo_promedio(data, producto_codigo)
    
    if producto_codigo not in data['kardex']:
        data['kardex'][producto_codigo] = []
    
    saldo = (data['kardex'][producto_codigo][-1]['saldo'] if data['kardex'][producto_codigo] else 0) - cantidad_solicitada
    
    costo_unitario_promedio = costo_total / cantidad_solicitada if cantidad_solicitada > 0 else 0
    
    data['kardex'][producto_codigo].append({
        'fecha': fecha,
        'tipo': 'salida',
        'cantidad': cantidad_solicitada,
        'costo': costo_unitario_promedio,
        'precio_venta': 0,
        'total': costo_total,
        'saldo': saldo,
        'descripcion': f'Salida PEPS - {len(lotes_usados)} lote(s) usado(s)',
        'lotes_usados': lotes_usados
    })
    
    producto_peps['lotes'] = [
        l for l in producto_peps['lotes']
        if l.get('cantidad_restante', 0) > 0
    ]
    
    return data, costo_total, lotes_usados

def recalcular_costo_promedio(data, producto_codigo):
    """Recalcula el costo promedio ponderado del producto."""
    if producto_codigo not in data.get('kardex_peps', {}):
        return data
    
    producto_peps = data['kardex_peps'][producto_codigo]
    
    if producto_peps['stock_total'] == 0:
        producto_peps['costo_promedio'] = 0
        return data
    
    valor_total = 0
    cantidad_total = 0
    
    for lote_dict in producto_peps['lotes']:
        if lote_dict['cantidad_restante'] > 0:
            valor_total += lote_dict['cantidad_restante'] * lote_dict['costo_unitario']
            cantidad_total += lote_dict['cantidad_restante']
    
    producto_peps['costo_promedio'] = valor_total / cantidad_total if cantidad_total > 0 else 0
    
    return data

def obtener_lotes_disponibles(data, producto_codigo, max_lotes=None):
    """
    Obtiene lista de lotes disponibles para un producto.
    
    Args:
        max_lotes: límite de lotes a retornar (None = todos).
    
    Returns:
        list: Lista de diccionarios con info de cada lote
    """
    if producto_codigo not in data.get('kardex_peps', {}):
        return []
    
    lotes = []
    for lote_dict in data['kardex_peps'][producto_codigo]['lotes']:
        if lote_dict['cantidad_restante'] > 0:
            lotes.append({
                'fecha': lote_dict['fecha'],
                'cantidad_original': lote_dict['cantidad'],
                'cantidad_disponible': lote_dict['cantidad_restante'],
                'costo_unitario': lote_dict['costo_unitario'],
                'valor_total': lote_dict['cantidad_restante'] * lote_dict['costo_unitario']
            })
            if max_lotes is not None and len(lotes) >= max_lotes:
                break
    
    return lotes

def obtener_info_producto_peps(data, producto_codigo, max_lotes=None):
    """
    Obtiene información completa del producto en PEPS.
    
    Args:
        max_lotes: si se especifica, limita la cantidad de lotes retornados.
    
    Returns:
        dict: {
            'stock_total': int,
            'costo_promedio': float,
            'lotes_disponibles': list,
            'valor_inventario': float
        }
    """
    if producto_codigo not in data.get('kardex_peps', {}):
        return {
            'stock_total': 0,
            'costo_promedio': 0,
            'lotes_disponibles': [],
            'valor_inventario': 0
        }
    
    producto_peps = data['kardex_peps'][producto_codigo]
    lotes = obtener_lotes_disponibles(data, producto_codigo, max_lotes=max_lotes)
    
    valor_inventario = sum(lote['valor_total'] for lote in lotes)
    
    return {
        'stock_total': producto_peps['stock_total'],
        'costo_promedio': producto_peps['costo_promedio'],
        'lotes_disponibles': lotes,
        'valor_inventario': valor_inventario
    }

def generar_reporte_kardex_peps(data, producto_codigo=None, max_lotes=None):
    """
    Genera datos para reporte de Kardex PEPS.
    
    Args:
        producto_codigo: Si se especifica, solo ese producto. Si es None, todos.
        max_lotes: límite de lotes por producto (None = todos).
    
    Returns:
        dict: Datos organizados para el reporte
    """
    if not data:
        return {}
    
    if 'kardex_peps' not in data:
        data['kardex_peps'] = {}
    
    if 'productos' not in data:
        data['productos'] = {}
    
    if 'kardex' not in data:
        data['kardex'] = {}
    
    if producto_codigo:
        productos = [producto_codigo] if producto_codigo in data.get('kardex_peps', {}) else []
    else:
        productos_kardex = set(data.get('kardex', {}).keys())
        productos_peps = set(data.get('kardex_peps', {}).keys())
        productos = list(productos_kardex | productos_peps)
    
    reporte = {}
    
    for codigo in productos:
        try:
            info = obtener_info_producto_peps(data, codigo, max_lotes=max_lotes)
            
            nombre = codigo  # Default: usar el código
            
            if codigo in data.get('productos', {}):
                producto_info = data['productos'][codigo]
                if isinstance(producto_info, dict):
                    nombre = producto_info.get('nombre', codigo)
                elif isinstance(producto_info, str):
                    nombre = producto_info
            
            peps_prod = data.get('kardex_peps', {}).get(codigo, {})
            productos_info = data.get('productos', {}).get(codigo, {})
            if isinstance(productos_info, dict):
                pv = productos_info.get('precio_venta', 0) or peps_prod.get('precio_venta', 0)
            else:
                pv = peps_prod.get('precio_venta', 0)

            reporte[codigo] = {
                'nombre': nombre,
                'stock': info['stock_total'],
                'costo_promedio': info['costo_promedio'],
                'valor_inventario': info['valor_inventario'],
                'precio_venta': pv,
                'lotes': info['lotes_disponibles'],
                'movimientos': data.get('kardex', {}).get(codigo, [])
            }
        except Exception as e:
            print(f"Error procesando producto {codigo}: {e}")
            continue
    
    return reporte
