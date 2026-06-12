"""
════════════════════════════════════════════════════════════════════════════
 Colectivo FG - Kardex PEPS Mejorado (Formato Tabla Profesional)
════════════════════════════════════════════════════════════════════════════

Sistema completo de Kardex con método PEPS siguiendo el formato estándar:
- INGRESOS (Compras): Cantidad, Costo Unitario, Total
- EGRESOS (Ventas): Cantidad, Costo Unitario, Total
- SALDO: Cantidad, Costo Unitario, Total
"""

from datetime import datetime

class KardexPEPS:
    """Clase para manejar Kardex con método PEPS profesional."""
    
    def __init__(self, producto_codigo, producto_nombre):
        self.producto_codigo = producto_codigo
        self.producto_nombre = producto_nombre
        self.movimientos = []
        self.lotes = []  # Lista de lotes disponibles
        
    def agregar_saldo_inicial(self, fecha, cantidad, costo_unitario):
        """Agrega saldo inicial al Kardex."""
        total = cantidad * costo_unitario
        
        movimiento = {
            'fecha': fecha,
            'concepto': 'Saldo inicial',
            'tipo': 'saldo_inicial',
            'ingresos': {'cantidad': '', 'costo_unitario': '', 'total': ''},
            'egresos': {'cantidad': '', 'costo_unitario': '', 'total': ''},
            'saldo': {'cantidad': cantidad, 'costo_unitario': costo_unitario, 'total': total},
            'peps_info': ''
        }
        
        self.movimientos.append(movimiento)
        
        # Crear lote inicial
        if cantidad > 0:
            self.lotes.append({
                'fecha': fecha,
                'cantidad_original': cantidad,
                'cantidad_disponible': cantidad,
                'costo_unitario': costo_unitario
            })
    
    def agregar_compra(self, fecha, cantidad, costo_unitario, concepto='Compra'):
        """Agrega una compra (ingreso) al Kardex."""
        total_ingreso = cantidad * costo_unitario
        
        # Calcular nuevo saldo
        saldo_anterior = self.movimientos[-1]['saldo'] if self.movimientos else {'cantidad': 0, 'costo_unitario': 0, 'total': 0}
        
        nueva_cantidad = saldo_anterior['cantidad'] + cantidad
        nuevo_total = saldo_anterior['total'] + total_ingreso
        nuevo_costo_promedio = nuevo_total / nueva_cantidad if nueva_cantidad > 0 else 0
        
        movimiento = {
            'fecha': fecha,
            'concepto': concepto,
            'tipo': 'compra',
            'ingresos': {'cantidad': cantidad, 'costo_unitario': costo_unitario, 'total': total_ingreso},
            'egresos': {'cantidad': '', 'costo_unitario': '', 'total': ''},
            'saldo': {'cantidad': nueva_cantidad, 'costo_unitario': nuevo_costo_promedio, 'total': nuevo_total},
            'peps_info': ''
        }
        
        self.movimientos.append(movimiento)
        
        # Agregar nuevo lote
        self.lotes.append({
            'fecha': fecha,
            'cantidad_original': cantidad,
            'cantidad_disponible': cantidad,
            'costo_unitario': costo_unitario
        })
    
    def agregar_venta(self, fecha, cantidad, concepto='Ventas'):
        """Agrega una venta (egreso) usando PEPS."""
        if self._stock_disponible() < cantidad:
            raise ValueError(f"Stock insuficiente. Disponible: {self._stock_disponible()}, Solicitado: {cantidad}")
        
        # Procesar salida PEPS
        cantidad_restante = cantidad
        costo_total_egreso = 0
        lotes_usados = []
        
        for lote in self.lotes:
            if cantidad_restante <= 0:
                break
                
            if lote['cantidad_disponible'] > 0:
                cantidad_a_tomar = min(cantidad_restante, lote['cantidad_disponible'])
                costo_lote = cantidad_a_tomar * lote['costo_unitario']
                
                lote['cantidad_disponible'] -= cantidad_a_tomar
                cantidad_restante -= cantidad_a_tomar
                costo_total_egreso += costo_lote
                
                lotes_usados.append({
                    'fecha_lote': lote['fecha'],
                    'cantidad': cantidad_a_tomar,
                    'costo_unitario': lote['costo_unitario']
                })
        
        costo_unitario_promedio = costo_total_egreso / cantidad if cantidad > 0 else 0
        
        # Calcular nuevo saldo
        saldo_anterior = self.movimientos[-1]['saldo']
        nueva_cantidad = saldo_anterior['cantidad'] - cantidad
        nuevo_total = saldo_anterior['total'] - costo_total_egreso
        nuevo_costo_promedio = nuevo_total / nueva_cantidad if nueva_cantidad > 0 else 0
        
        # Generar texto PEPS
        peps_text = self._generar_texto_peps(lotes_usados)
        
        movimiento = {
            'fecha': fecha,
            'concepto': concepto,
            'tipo': 'venta',
            'ingresos': {'cantidad': '', 'costo_unitario': '', 'total': ''},
            'egresos': {'cantidad': cantidad, 'costo_unitario': costo_unitario_promedio, 'total': costo_total_egreso},
            'saldo': {'cantidad': nueva_cantidad, 'costo_unitario': nuevo_costo_promedio, 'total': nuevo_total},
            'peps_info': peps_text,
            'lotes_usados': lotes_usados
        }
        
        self.movimientos.append(movimiento)
        
        return costo_total_egreso, lotes_usados
    
    def agregar_ajuste_inventario(self, fecha, cantidad_ajustada, costo_unitario, concepto='Inventario de mercadería'):
        """Agrega un ajuste de inventario (puede ser positivo o negativo)."""
        saldo_anterior = self.movimientos[-1]['saldo'] if self.movimientos else {'cantidad': 0, 'costo_unitario': 0, 'total': 0}
        
        diferencia = cantidad_ajustada - saldo_anterior['cantidad']
        
        if diferencia > 0:
            # Ajuste positivo (entrada)
            total_ajuste = diferencia * costo_unitario
            nueva_cantidad = cantidad_ajustada
            nuevo_total = saldo_anterior['total'] + total_ajuste
            nuevo_costo_promedio = nuevo_total / nueva_cantidad if nueva_cantidad > 0 else 0
            
            movimiento = {
                'fecha': fecha,
                'concepto': concepto,
                'tipo': 'ajuste_entrada',
                'ingresos': {'cantidad': diferencia, 'costo_unitario': costo_unitario, 'total': total_ajuste},
                'egresos': {'cantidad': '', 'costo_unitario': '', 'total': ''},
                'saldo': {'cantidad': nueva_cantidad, 'costo_unitario': nuevo_costo_promedio, 'total': nuevo_total},
                'peps_info': ''
            }
            
            # Agregar lote para el ajuste
            self.lotes.append({
                'fecha': fecha,
                'cantidad_original': diferencia,
                'cantidad_disponible': diferencia,
                'costo_unitario': costo_unitario
            })
        
        else:
            # Ajuste negativo (salida)
            cantidad_salida = abs(diferencia)
            
            # Usar PEPS para el ajuste negativo
            try:
                costo_total, lotes_usados = self.agregar_venta(fecha, cantidad_salida, concepto)
                # La venta ya agregó el movimiento
                return
            except ValueError:
                raise ValueError(f"No se puede ajustar negativamente. Stock insuficiente.")
        
        self.movimientos.append(movimiento)
    
    def _stock_disponible(self):
        """Calcula stock disponible sumando lotes."""
        return sum(lote['cantidad_disponible'] for lote in self.lotes)
    
    def _generar_texto_peps(self, lotes_usados):
        """Genera texto descriptivo de los lotes usados en PEPS."""
        if not lotes_usados:
            return ""
        
        textos = []
        for lote in lotes_usados:
            textos.append(f"{lote['cantidad']} @ C${lote['costo_unitario']:.2f} ({lote['fecha_lote']})")
        
        return " + ".join(textos)
    
    def obtener_lotes_disponibles(self):
        """Retorna lista de lotes que aún tienen stock."""
        return [lote for lote in self.lotes if lote['cantidad_disponible'] > 0]
    
    def to_dict(self):
        """Convierte el Kardex a diccionario para guardar."""
        return {
            'producto_codigo': self.producto_codigo,
            'producto_nombre': self.producto_nombre,
            'movimientos': self.movimientos,
            'lotes': self.lotes
        }
    
    @staticmethod
    def from_dict(data):
        """Crea un Kardex desde un diccionario."""
        kardex = KardexPEPS(data['producto_codigo'], data['producto_nombre'])
        kardex.movimientos = data.get('movimientos', [])
        kardex.lotes = data.get('lotes', [])
        return kardex
