"""
Script para inicializar/resetear cuentas del sistema.
"""
import db_internal

print("═══════════════════════════════════════════")
print("  Inicializando Cuentas del Sistema")
print("═══════════════════════════════════════════")
print()

# Inicializar BD
db_internal.init_database()

# Cargar datos
data = db_internal.load_data()

# Si no hay cuentas, agregar las por defecto
if not data.get('cuentas') or len(data['cuentas']) == 0:
    print("Agregando cuentas por defecto...")
    
    data['cuentas'] = {
        "1001": {"nombre": "Efectivo", "tipo": "Activo", "saldo": 0},
        "1002": {"nombre": "Bancos", "tipo": "Activo", "saldo": 0},
        "1003": {"nombre": "Cuentas por Cobrar", "tipo": "Activo", "saldo": 0},
        "1004": {"nombre": "Inventario", "tipo": "Activo", "saldo": 0},
        "2001": {"nombre": "Cuentas por Pagar", "tipo": "Pasivo", "saldo": 0},
        "2002": {"nombre": "Proveedores", "tipo": "Pasivo", "saldo": 0},
        "3001": {"nombre": "Capital", "tipo": "Capital", "saldo": 0},
        "4001": {"nombre": "Ventas", "tipo": "Ingreso", "saldo": 0},
        "4002": {"nombre": "Otros Ingresos", "tipo": "Ingreso", "saldo": 0},
        "5001": {"nombre": "Costo de Ventas", "tipo": "Gasto", "saldo": 0},
        "5002": {"nombre": "Gastos Operativos", "tipo": "Gasto", "saldo": 0},
        "5003": {"nombre": "Gastos Administrativos", "tipo": "Gasto", "saldo": 0}
    }
    
    db_internal.save_data(data)
    print("✓ Cuentas agregadas exitosamente")
else:
    print(f"Ya existen {len(data['cuentas'])} cuentas")

print()
print("Cuentas disponibles:")
for codigo, info in sorted(data['cuentas'].items()):
    nombre = info.get('nombre', info) if isinstance(info, dict) else info
    tipo = info.get('tipo', '') if isinstance(info, dict) else ''
    print(f"  {codigo} - {nombre} ({tipo})")

print()
print("═══════════════════════════════════════════")
print("  ✓ Inicialización Completada")
print("═══════════════════════════════════════════")
