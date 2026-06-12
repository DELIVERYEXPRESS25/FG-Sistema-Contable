"""
Genera el icono .ico desde el logo JPEG
"""
try:
    from PIL import Image
    
    # Abrir logo
    img = Image.open('logo_fg.jpg')
    
    # Convertir a RGBA si no lo está
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Crear icono en múltiples tamaños
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    # Guardar como .ico
    img.save('fg_icon.ico', format='ICO', sizes=icon_sizes)
    
    print("✓ Icono generado: fg_icon.ico")
    
except ImportError:
    print("⚠️ PIL/Pillow no está instalado")
    print("   Instalando...")
    import subprocess
    subprocess.run(['pip', 'install', 'Pillow', '--break-system-packages'], check=True)
    print("   Ejecuta el script de nuevo")
except Exception as e:
    print(f"❌ Error: {e}")
