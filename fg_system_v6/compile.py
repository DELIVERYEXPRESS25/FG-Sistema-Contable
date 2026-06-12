"""
============================================================
  F & G — Sistema Contable
  COMPILADOR  →  Genera el ejecutable .exe con PyInstaller
============================================================

  Uso:
      pip install pyinstaller
      python compile.py

  Icono (.ico):
      • Si hay un archivo .ico en la carpeta (cualquier nombre)
        → lo usa automáticamente.
      • Si no hay ninguno → genera uno con el logo F&G solo.
      • Nombres reconocidos con prioridad:
          icon.ico, logo.ico, fg.ico, o cualquier otra.ico

  Resultado:
      dist/FG_Sistema_Contable.exe       ← un solo archivo (por defecto)
      
  Nota:
      El .exe incluye TODO: Python, Flask, templates, datos, lib/.
      Tarda 1-3 minutos en compilar.
      El .exe pesa ~40-50 MB pero es 100% portable.
============================================================
"""

import sys
import os
import subprocess
import math

# ── Configuración ──────────────────────────────────────────
APP_NAME       = "FG_Sistema_Contable"
SCRIPT_ENTRY   = "main.py"
ONE_FILE       = True        # True → un solo .exe | False → carpeta
HIDE_CONSOLE   = True        # True → sin ventana de consola (GUI)

EXTRA_DATA = [
    ("templates",      "templates"),
    ("static",         "static"),
    ("data.json",      "."),
    ("requirements.txt", "."),
]

# ══════════════════════════════════════════════════════════════
# ICONO — buscar automáticamente o generar
# ══════════════════════════════════════════════════════════════
def find_icon():
    """
    Escanea la carpeta actual buscando cualquier .ico.
    Si no hay ninguno, genera uno automáticamente.
    """
    icos = [f for f in os.listdir(".") if f.lower().endswith(".ico")]

    if icos:
        # Prioridad por nombre conocido
        for nombre in ["icon.ico", "Icon.ico", "logo.ico", "Logo.ico",
                        "fg.ico",   "FG.ico",   "FG_icon.ico"]:
            if nombre in icos:
                print(f"  ✓  Icono encontrado: {nombre}")
                return nombre
        # Si no coincide con ningún nombre conocido, usar el primero
        print(f"  ✓  Icono encontrado: {icos[0]}")
        return icos[0]

    # Ningún .ico → generar
    print("  → No se encontró .ico en la carpeta.")
    print("    Generando icono automáticamente...")
    return generate_icon()


def generate_icon():
    """
    Genera icon.ico con el logo F&G.
    Azul-purpura con texto blanco, multi-tamaño (256 → 16).
    Instala Pillow automáticamente si no está.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  → Instalando Pillow...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "Pillow", "--quiet"]
        )
        from PIL import Image, ImageDraw, ImageFont

    sizes  = [256, 128, 64, 48, 32, 16]
    frames = []

    for size in sizes:
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad = max(int(size * 0.08), 1)
        r   = max(int(size * 0.18), 2)   # radio esquinas

        # ── Sombra ──
        so = max(int(size * 0.03), 1)
        draw.rounded_rectangle(
            [pad+so, pad+so, size-pad+so, size-pad+so],
            radius=r, fill=(0, 0, 0, 60)
        )

        # ── Fondo gradiente azul → purpura ──
        top_c    = (60, 120, 240)
        bottom_c = (100, 70, 220)
        inner_h  = max(size - 2 * pad, 1)

        for y in range(pad, size - pad):
            t  = (y - pad) / inner_h
            rc = int(top_c[0] + (bottom_c[0] - top_c[0]) * t)
            gc = int(top_c[1] + (bottom_c[1] - top_c[1]) * t)
            bc = int(top_c[2] + (bottom_c[2] - top_c[2]) * t)

            # Márgenes por redondeo de esquinas
            dt = y - pad
            db = (size - pad) - y
            ml = mr = 0
            if dt < r:
                ml = int(r - math.sqrt(max(r*r - (r - dt)**2, 0)))
            if db < r:
                mr = int(r - math.sqrt(max(r*r - (r - db)**2, 0)))

            draw.line(
                [(pad + ml, y), (size - pad - mr, y)],
                fill=(rc, gc, bc, 255)
            )

        # ── Texto "F&G" centrado ──
        font_size = max(int(size * 0.48), 6)
        font = None
        # Buscar fuentes del sistema (Windows primero, Linux segundo)
        try:
            for fn in ["arialbd.ttf", "arial.ttf", "segoeui.ttf", "calibrib.ttf"]:
                fp = os.path.join(
                    os.environ.get("WINDIR", "C:\\Windows"), "Fonts", fn
                )
                if os.path.isfile(fp):
                    font = ImageFont.truetype(fp, font_size)
                    break
        except Exception:
            pass
        if not font:
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    font_size
                )
            except Exception:
                font = ImageFont.load_default()

        # Centrar texto
        bbox = draw.textbbox((0, 0), "F&G", font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        tx   = (size - tw) // 2 - bbox[0]
        ty   = (size - th) // 2 - bbox[1]

        # Sombra del texto
        sc = max(int(size * 0.02), 1)
        draw.text((tx + sc, ty + sc), "F&G", font=font, fill=(0, 0, 0, 120))
        # Texto principal
        draw.text((tx, ty), "F&G", font=font, fill=(255, 255, 255, 255))

        frames.append(img)

    # ── Guardar .ico manualmente (formato binario ICO) ──
    # Pillow 12+ no soporta format="ICO" en save_all,
    # así que escribimos el contenedor ICO a mano (es muy simple).
    import struct
    from io import BytesIO

    ico_path = "icon.ico"

    # Cada frame se guarda como PNG dentro del .ico
    png_chunks = []
    for frame in frames:
        buf = BytesIO()
        frame.save(buf, format="PNG")
        png_chunks.append(buf.getvalue())

    num_images = len(png_chunks)

    # Header ICO: reserved(2) + type(2) + count(2)
    header = struct.pack("<HHH", 0, 1, num_images)

    # Calcular offset donde empieza la primera imagen
    # Cada entrada del directorio = 16 bytes
    dir_size   = 16 * num_images
    data_offset = 6 + dir_size          # 6 bytes de header + directorio

    directory  = b""
    image_data = b""
    current_offset = data_offset

    for i, png in enumerate(png_chunks):
        w = sizes[i]
        h = sizes[i]
        # En ICO, 0 significa 256
        w_byte = 0 if w == 256 else w
        h_byte = 0 if h == 256 else h

        # Entrada directorio: w, h, colors, reserved, planes, bpp, size, offset
        directory += struct.pack(
            "<BBBBHHII",
            w_byte,     # ancho
            h_byte,     # alto
            0,          # colores (0 = sin paleta)
            0,          # reservado
            1,          # planes
            32,         # bits por pixel
            len(png),   # tamaño datos
            current_offset
        )
        image_data    += png
        current_offset += len(png)

    # Escribir archivo
    with open(ico_path, "wb") as f:
        f.write(header)
        f.write(directory)
        f.write(image_data)

    print(f"  ✓  Icono generado: {ico_path}  (tamaños: {sizes})")
    return ico_path


# ══════════════════════════════════════════════════════════════
# Verificaciones
# ══════════════════════════════════════════════════════════════
def check_python():
    v = sys.version_info
    if v < (3, 9):
        print(f"\n  ✕  Se requiere Python 3.9+. Tienes {v.major}.{v.minor}.{v.micro}")
        sys.exit(1)
    print(f"  ✓  Python {v.major}.{v.minor}.{v.micro}")

def install_pyinstaller():
    try:
        import PyInstaller
        print(f"  ✓  PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  → Instalando PyInstaller...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"]
        )
        print("  ✓  PyInstaller instalado")

def check_entry():
    if not os.path.isfile(SCRIPT_ENTRY):
        print(f"\n  ✕  No se encontró '{SCRIPT_ENTRY}'.")
        print(f"     Ejecuta compile.py desde la carpeta raíz del proyecto.")
        sys.exit(1)
    print(f"  ✓  Entry point: {SCRIPT_ENTRY}")


# ══════════════════════════════════════════════════════════════
# Construir comando PyInstaller
# ══════════════════════════════════════════════════════════════
def build_pyinstaller_cmd(icon_path):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        SCRIPT_ENTRY,
        "--name",      APP_NAME,
        "--clean",
        "--noconfirm",
        "--log-level", "WARN",
    ]

    cmd.append("--onefile" if ONE_FILE else "--onedir")

    if HIDE_CONSOLE:
        cmd.append("--windowed")

    # ── Icono (siempre presente, find_icon lo garantiza) ──
    cmd.extend(["--icon", icon_path])

    # Datos extra
    for src, dst in EXTRA_DATA:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src};{dst}"])

    if os.path.isdir("lib"):
        cmd.extend(["--add-data", "lib;lib"])

    return cmd


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════
def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print()
    print("=" * 56)
    print("  🏦  F & G — Sistema Contable")
    print("  COMPILADOR PyInstaller")
    print("=" * 56)
    print()

    print("  [1/5] Verificando entorno...")
    check_python()
    check_entry()
    print()

    print("  [2/5] Verificando PyInstaller...")
    install_pyinstaller()
    print()

    print("  [3/5] Buscando icono...")
    icon_path = find_icon()
    print()

    print("  [4/5] Compilando aplicación...")
    print(f"         Modo:    {'Un solo archivo (.exe)' if ONE_FILE else 'Carpeta'}")
    print(f"         Consola: {'Oculta' if HIDE_CONSOLE else 'Visible'}")
    print(f"         Icono:   {icon_path}")
    print()

    cmd = build_pyinstaller_cmd(icon_path)
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("  ✕  La compilación falló.")
        print("     Revisa los mensajes de error arriba.")
        print("     Trucos comunes:")
        print("       • Cierra cualquier otra instancia de la app")
        print("       • Asegúrate de estar en la carpeta raíz")
        print("       • Ejecuta desde cmd como administrador")
        sys.exit(1)

    # Ubicación del resultado
    if ONE_FILE:
        out = os.path.join("dist", APP_NAME + ".exe")
    else:
        out = os.path.join("dist", APP_NAME)

    # Calcular tamaño
    if ONE_FILE:
        total = os.path.getsize(out)
    else:
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(out)
            for f in files
        )

    print()
    print("  [5/5] ¡Compilación exitosa!")
    print()
    print("  " + "─" * 50)
    print(f"  📦  Resultado : {out}")
    print(f"  🖼   Icono     : {icon_path}")
    print(f"  📏  Tamaño    : {total / (1024*1024):.1f} MB")
    print("  " + "─" * 50)
    print()
    print("  Para ejecutar:")
    if ONE_FILE:
        print(f"    → Doble clic en  {out}")
    else:
        print(f"    → Doble clic en  {out}\\{APP_NAME}.exe")
    print()
    print("=" * 56)


if __name__ == "__main__":
    main()
