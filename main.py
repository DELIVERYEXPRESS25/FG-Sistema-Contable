"""
F & G — Sistema Contable
Punto de entrada del ejecutable compilado.
Agrega lib/ al path para usar las dependencias empaquetadas,
luego inicia el servidor Flask y abre el navegador automáticamente.
"""
import sys, os, time, threading, webbrowser

# ── 1. Determinar la carpeta base ──
# Cuando está compilado con PyInstaller --onefile, los archivos se extraen
# a una carpeta temporal en sys._MEIPASS. 
# En desarrollo, usa la carpeta donde está este archivo.
if getattr(sys, 'frozen', False):
    # Compilado: usar la carpeta temporal donde PyInstaller extrajo todo
    BASE = sys._MEIPASS
else:
    # Desarrollo: carpeta donde está main.py
    BASE = os.path.dirname(os.path.abspath(__file__))

# ── 2. Agregar lib/ al inicio del path para las dependencias empaquetadas ──
LIB = os.path.join(BASE, 'lib')
if os.path.isdir(LIB):
    sys.path.insert(0, LIB)

# ── 3. Cambiar working directory a BASE ──
# Esto permite que data.json, templates/, reportes/ funcionen correctamente
os.chdir(BASE)

# ── 4. Importar la app Flask (DESPUÉS de ajustar el path) ──
from app import app

# ── 5. Abrir navegador después de 1.2s (le da tiempo al servidor de iniciar) ──
def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:5000')

t = threading.Thread(target=open_browser, daemon=True)
t.start()

# ── 6. Iniciar servidor ──
if __name__ == '__main__':
    print("=" * 48)
    print("  🏦  F & G  —  Sistema Contable")
    print("  Servidor iniciando en http://127.0.0.1:5000")
    print("=" * 48)
    app.run(debug=False, host='0.0.0.0', port=5000)
