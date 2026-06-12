"""
Script de optimización de base de datos SQLite.
Ejecutar periódicamente para mantener rendimiento óptimo.
"""
import db_internal

print("═══════════════════════════════════════")
print("  Optimizando Base de Datos SQLite")
print("═══════════════════════════════════════")
print()

try:
    db_internal.init_database()
    print("✓ Base de datos inicializada")
    
    db_internal.optimize_database()
    print("✓ VACUUM ejecutado")
    print("✓ ANALYZE ejecutado")
    print("✓ Índices optimizados")
    
    print()
    print("═══════════════════════════════════════")
    print("  ✓ Optimización Completada")
    print("═══════════════════════════════════════")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
