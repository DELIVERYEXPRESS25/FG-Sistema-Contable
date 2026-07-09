"""
Importar backup JSON a la base de datos SQLite.
Uso: python importar_backup.py [archivo.json]
"""
import json
import sys
import os

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

from db_internal import get_db_path, get_connection, init_database

def importar_backup(archivo_json):
    """Importa un archivo JSON de backup a la base de datos."""
    
    # Leer JSON
    print(f"Leyendo {archivo_json}...")
    with open(archivo_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Verificar estructura
    required_keys = ['cuentas', 'diario', 'productos', 'kardex', 'kardex_peps', 'pos_historial']
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"Advertencia: Faltan claves: {missing}")
    
    # Estadísticas
    print(f"\n=== Datos encontrados ===")
    print(f"Cuentas: {len(data.get('cuentas', {}))}")
    print(f"Diario: {len(data.get('diario', []))} asientos")
    print(f"Productos: {len(data.get('productos', {}))}")
    print(f"Kardex: {len(data.get('kardex', {}))} productos")
    print(f"Kardex PEPS: {len(data.get('kardex_peps', {}))} productos")
    print(f"POS Historial: {len(data.get('pos_historial', []))} ventas")
    print(f"Caja movimientos: {len(data.get('caja_movimientos', []))}")
    
    # Guardar en SQLite
    print(f"\nGuardando en base de datos...")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO app_data (key, value, updated_at) VALUES (?, ?, datetime("now"))',
            ("main_data", json.dumps(data, ensure_ascii=False))
        )
        conn.commit()
    
    print("¡Importación completada!")
    
    # Verificar
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_data WHERE key = 'main_data'")
        row = cursor.fetchone()
        if row:
            saved = json.loads(row[0])
            print(f"\nVerificación:")
            print(f"  Diario: {len(saved.get('diario', []))} asientos")
            print(f"  POS: {len(saved.get('pos_historial', []))} ventas")
            print(f"  Kardex: {len(saved.get('kardex', {}))} productos")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_backup.py <archivo.json>")
        sys.exit(1)
    
    archivo = sys.argv[1]
    if not os.path.exists(archivo):
        print(f"Error: No se encontró {archivo}")
        sys.exit(1)
    
    importar_backup(archivo)
