"""
Script para inicializar/resetear cuentas del sistema.
"""
import db_internal

from app import CUENTAS_BASE

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

    data['cuentas'] = dict(CUENTAS_BASE)

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
