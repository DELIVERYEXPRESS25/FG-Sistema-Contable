#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Script para ejecutar FG Sistema en Docker
# ═══════════════════════════════════════════════════════════════════════

echo "🐳 FG Sistema Contable - Docker"

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    exit 1
fi

# Verificar si docker-compose está instalado
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose no está instalado"
    exit 1
fi

# Verificar si existe .env
if [ ! -f .env ]; then
    echo "⚠️  No existe .env, creando desde .env.example..."
    cp .env.example .env
fi

# Menú de opciones
case "${1:-}" in
    up)
        echo "🚀 Iniciando contenedor..."
        docker-compose up -d
        echo "✅ Sistema iniciado en http://localhost:5000"
        ;;
    down)
        echo "🛑 Deteniendo contenedor..."
        docker-compose down
        ;;
    restart)
        echo "🔄 Reiniciando contenedor..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    build)
        echo "🔨 Construyendo imagen..."
        docker-compose build --no-cache
        ;;
    clean)
        echo "🧹 Limpiando contenedores y volúmenes..."
        docker-compose down -v
        ;;
    shell)
        echo "🐚 Entrando al contenedor..."
        docker-compose exec app bash
        ;;
    *)
        echo "Usage: $0 {up|down|restart|logs|build|clean|shell}"
        echo ""
        echo "Comandos:"
        echo "  up      - Iniciar el contenedor"
        echo "  down    - Detener el contenedor"
        echo "  restart - Reiniciar el contenedor"
        echo "  logs    - Ver logs en tiempo real"
        echo "  build   - Reconstruir la imagen"
        echo "  clean   - Eliminar contenedores y volúmenes"
        echo "  shell   - Entrar al contenedor"
        exit 1
        ;;
esac