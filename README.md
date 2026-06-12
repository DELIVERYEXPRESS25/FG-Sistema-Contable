# 🏦 F & G — Sistema Contable
**Moneda:** C$ NIO (Córdoba Nicaragüense)

---

## 📦 Contenido de la carpeta

| Archivo / Carpeta | Descripción |
|---|---|
| `Instalar_FG.bat` | **Instalador Windows** — ejecuta esto primero |
| `instalar_fg.sh` | **Instalador macOS / Linux** |
| `Ejecutar_FG.bat` | Lanzador manual Windows |
| `ejecutar_fg.sh` | Lanzador manual macOS/Linux (se crea al instalar) |
| `main.py` | Punto de entrada compilado — inicia servidor + abre navegador |
| `app.py` | Lógica del servidor Flask |
| `lib/` | Dependencias empaquetadas (Flask, Jinja2, Werkzeug…) |
| `templates/` | Plantillas HTML del sistema |
| `data.json` | Base de datos (se crea automáticamente) |
| `requirements.txt` | Lista de paquetes para pip |

---

## 🚀 Instalación rápida

### Windows
```
1. Doble clic en:  Instalar_FG.bat
2. Sigue las instrucciones en pantalla
3. El instalador crea un acceso directo en tu escritorio
```
> Si no tienes Python, el instalador te indica dónde descargarlo.

### macOS / Linux
```bash
chmod +x instalar_fg.sh
./instalar_fg.sh
```

---

## ⚡ Ejecutar sin instalar (desarrollo)

Si ya tienes Python 3.9+ y las dependencias instaladas:

```bash
python main.py
```

El servidor inicia en **http://127.0.0.1:5000** y el navegador se abre solo.

---

## 📦 ¿Qué es la carpeta `lib/`?

Contiene todas las dependencias de Flask **empaquetadas** dentro del proyecto.
`main.py` las agrega al `sys.path` automáticamente, así que el sistema puede
funcionar sin necesidad de instalar nada extra si Python ya está disponible.

---

## 🗺️ Módulos

| Módulo | Descripción |
|---|---|
| 🏠 Dashboard | KPIs, gráficos ventas diarias/mensuales |
| 🧾 Libro Diario | Registro de transacciones |
| 📝 Asientos de Ajuste | Depreciaciones y correcciones |
| 📗 Libro Mayor | Cuentas T automáticas |
| ⚖️ Balanza de Comprobación | Verificación D = H |
| 📊 Estado de Resultados | Ingresos − Gastos = Utilidad |
| 🏦 Balance General | Activos = Pasivos + Capital |
| 📦 Tarjetas Kardex | Control de inventario |
| 💳 Cuentas por Cobrar | Seguimiento de cobros |
| 💰 Auxiliar de Caja | Flujo de efectivo |
| 🛒 Ventas POS | Punto de venta con carrito |

---

## ⏻ Apagar el servidor

Botón **"Apagar Servidor"** en la barra lateral → la pestaña se cierra automáticamente.
