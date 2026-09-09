import sys
import os
import time
import threading
import webbrowser

if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

LIB = os.path.join(BASE, 'lib')
if os.path.isdir(LIB):
    sys.path.insert(0, LIB)

os.chdir(BASE)

from app import app


def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:5000')


t = threading.Thread(target=open_browser, daemon=True)
t.start()

if __name__ == '__main__':
    print("=" * 48)
    print("  🏦  F & G  —  Sistema Contable")
    print("  Servidor iniciando en http://127.0.0.1:5000")
    print("=" * 48)
    app.run(debug=False, host='0.0.0.0', port=5000)
