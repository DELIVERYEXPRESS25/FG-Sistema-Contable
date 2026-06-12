#!/bin/bash
# ============================================================
#   F & G — Sistema Contable
#   Instalador para macOS / Linux
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo "   F & G — Sistema Contable"
echo "   Instalador | Moneda: C\$ NIO"
echo "============================================================"
echo -e "${NC}"

# --- 1. Buscar Python ---
echo -e "${BOLD}[1/4] Buscando Python...${NC}"

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}  ✕  Python no encontrado.${NC}"
    echo ""
    echo "     Instala Python 3.9+:"
    echo "       macOS:  brew install python"
    echo "       Ubuntu: sudo apt install python3 python3-pip"
    echo "       Fedora: sudo dnf install python3 python3-pip"
    echo ""
    exit 1
fi

echo -e "${GREEN}  ✓  Python encontrado: $(which $PYTHON)${NC}"
$PYTHON --version
echo ""

# --- 2. Verificar versión ---
echo -e "${BOLD}[2/4] Verificando versión...${NC}"

$PYTHON -c "
import sys
if sys.version_info < (3, 9):
    print('  ✕  Se requiere Python 3.9+. Tienes:', '.'.join(map(str, sys.version_info[:3])))
    sys.exit(1)
else:
    print('  ✓  Versión OK:', '.'.join(map(str, sys.version_info[:3])))
"
if [ $? -ne 0 ]; then
    echo ""
    echo "     Actualiza Python a 3.9 o superior."
    exit 1
fi
echo ""

# --- 3. Instalar dependencias ---
echo -e "${BOLD}[3/4] Instalando dependencias...${NC}"

if $PYTHON -c "import flask" 2>/dev/null; then
    echo -e "${GREEN}  ✓  Dependencias ya instaladas (Flask detectado).${NC}"
else
    echo "  → Instalando paquetes..."
    # Intentar con --break-system-packages (Linux nuevos) y sin
    if $PYTHON -m pip install -r requirements.txt --quiet --break-system-packages 2>/dev/null; then
        echo -e "${GREEN}  ✓  Dependencias instaladas.${NC}"
    elif $PYTHON -m pip install -r requirements.txt --quiet 2>/dev/null; then
        echo -e "${GREEN}  ✓  Dependencias instaladas.${NC}"
    elif $PYTHON -m pip install -r requirements.txt --quiet --user 2>/dev/null; then
        echo -e "${GREEN}  ✓  Dependencias instaladas (modo usuario).${NC}"
    else
        echo -e "${RED}  ✕  Error instalando dependencias.${NC}"
        echo "     Intenta manualmente:"
        echo "       $PYTHON -m pip install -r requirements.txt"
        exit 1
    fi
fi
echo ""

# --- 4. Crear acceso directo ---
echo -e "${BOLD}[4/4] Creando acceso directo...${NC}"

# Script de lanzamiento
cat > "$SCRIPT_DIR/ejecutar_fg.sh" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec $PYTHON main.py
EOF
chmod +x "$SCRIPT_DIR/ejecutar_fg.sh"

# macOS .app bundle
if [[ "$(uname)" == "Darwin" ]]; then
    APP_BUNDLE="$HOME/Desktop/FG_Sistema_Contable.app"
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    cat > "$APP_BUNDLE/Contents/MacOS/FG" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
exec $PYTHON main.py
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/FG"

    cat > "$APP_BUNDLE/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleDisplayName</key><string>F&G Sistema Contable</string>
  <key>CFBundleExecutable</key><string>FG</string>
  <key>CFBundleIdentifier</key><string>com.fg.contable</string>
  <key>CFBundleName</key><string>FG Sistema Contable</string>
  <key>CFBundleVersion</key><string>1.0</string>
</dict></plist>
EOF
    echo -e "${GREEN}  ✓  App creada: ~/Desktop/FG_Sistema_Contable.app${NC}"

# Linux .desktop shortcut
else
    DESKTOP_FILE="$HOME/Desktop/FG_Sistema_Contable.desktop"
    mkdir -p "$HOME/Desktop"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=F&G Sistema Contable
Comment=Sistema Contable - Moneda C\$ NIO
Exec=$SCRIPT_DIR/ejecutar_fg.sh
Path=$SCRIPT_DIR
Terminal=true
EOF
    chmod +x "$DESKTOP_FILE"
    echo -e "${GREEN}  ✓  Acceso directo: ~/Desktop/FG_Sistema_Contable.desktop${NC}"
fi
echo ""

# --- RESUMEN ---
echo -e "${CYAN}${BOLD}"
echo "============================================================"
echo -e "  ${GREEN}✓  Instalación completada${NC}${CYAN}${BOLD}"
echo "============================================================"
echo -e "${NC}"
echo "  Archivos:"
echo "    • ejecutar_fg.sh       — Lanzador manual (terminal)"
echo "    • main.py              — Punto de entrada Python"
echo "    • Escritorio           — Acceso directo creado"
echo ""
echo "  Para iniciar:"
echo "    → Doble clic en el acceso directo, o"
echo "    → ./ejecutar_fg.sh"
echo ""
echo "  El navegador se abre automáticamente en:"
echo "    http://127.0.0.1:5000"
echo ""
echo "============================================================"

# --- Ofrecer lanzamiento ---
echo ""
read -p "  ¿Lanzar el sistema ahora? (s/n): " LAUNCH
if [[ "$LAUNCH" =~ ^[SsYy]$ ]]; then
    echo ""
    echo -e "${GREEN}  Iniciando F & G...${NC}"
    $PYTHON "$SCRIPT_DIR/main.py" &
    echo -e "${GREEN}  ✓  Sistema iniciado. El navegador se abrirá en segundos.${NC}"
    echo ""
else
    echo ""
    echo "  ¡Instalación lista! ¡Hasta la próxima!"
    echo ""
fi

exit 0
