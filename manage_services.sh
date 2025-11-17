#!/bin/bash

# Script para gerenciar serviços do Sistema Mr Baruch
# Uso: ./manage_services.sh [start|stop|restart|status|logs]

SERVICES="nginx gunicorn"
PROJECT_DIR="/home/mrbaruch/sistemaMrBaruchProjeto"
VENV_PATH="/home/mrbaruch/venv"
USER="mrbaruch"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[SISTEMA MR BARUCH]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Função para reiniciar Django (Gunicorn)
restart_django() {
    print_status "Reiniciando Django (Gunicorn)..."

    # Ativar venv e executar migrações se necessário
    sudo -u $USER bash -c "source $VENV_PATH/bin/activate && cd $PROJECT_DIR && python manage.py check --deploy"

    # Reiniciar Gunicorn
    sudo systemctl restart gunicorn
    sleep 2

    # Verificar status
    if sudo systemctl is-active --quiet gunicorn; then
        print_success "Django (Gunicorn) reiniciado com sucesso"
    else
        print_error "Falha ao reiniciar Django (Gunicorn)"
        sudo systemctl status gunicorn
        return 1
    fi
}

# Função para reiniciar Nginx
restart_nginx() {
    print_status "Reiniciando Nginx..."

    # Testar configuração
    sudo nginx -t
    if [ $? -eq 0 ]; then
        sudo systemctl restart nginx
        sleep 2

        if sudo systemctl is-active --quiet nginx; then
            print_success "Nginx reiniciado com sucesso"
        else
            print_error "Falha ao reiniciar Nginx"
            sudo systemctl status nginx
            return 1
        fi
    else
        print_error "Configuração Nginx inválida. Corrija antes de reiniciar."
        return 1
    fi
}

# Função para reiniciar tudo
restart_all() {
    print_status "REINICIANDO TODOS OS SERVIÇOS..."
    echo "=========================================="

    restart_django
    if [ $? -eq 0 ]; then
        restart_nginx
    else
        print_error "Parando execução devido a erro no Django"
        return 1
    fi

    echo "=========================================="
    print_success "Todos os serviços reiniciados com sucesso!"
}

# Função para parar todos os serviços
stop_all() {
    print_status "Parando todos os serviços..."
    sudo systemctl stop nginx gunicorn
    print_success "Serviços parados"
}

# Função para iniciar todos os serviços
start_all() {
    print_status "Iniciando todos os serviços..."
    sudo systemctl start gunicorn nginx
    sleep 3
    print_success "Serviços iniciados"
}

# Função para verificar status
show_status() {
    print_status "STATUS DOS SERVIÇOS:"
    echo "------------------------------------------"

    for service in $SERVICES; do
        if sudo systemctl is-active --quiet $service; then
            echo -e "${GREEN}● $service${NC} - $(sudo systemctl is-active $service)"
        else
            echo -e "${RED}● $service${NC} - $(sudo systemctl is-active $service)"
        fi
    done

    echo "------------------------------------------"

    # Verificar portas
    print_status "PORTAS EM USO:"
    sudo netstat -tulpn | grep -E ':(80|443|8000)' || echo "Nenhuma porta relevante encontrada"

    # Verificar socket Gunicorn
    if [ -S "$PROJECT_DIR/gunicorn.sock" ]; then
        print_success "Socket Gunicorn: OK ($PROJECT_DIR/gunicorn.sock)"
    else
        print_error "Socket Gunicorn não encontrado"
    fi
}

# Função para mostrar logs
show_logs() {
    print_status "ÚLTIMOS LOGS (Ctrl+C para sair):"
    echo "------------------------------------------"

    # Perguntar qual serviço ver logs
    echo "1 - Nginx"
    echo "2 - Gunicorn"
    echo "3 - Ambos (seguir)"
    echo "4 - Logs Django personalizados"
    read -p "Escolha (1-4): " log_choice

    case $log_choice in
        1)
            sudo journalctl -u nginx -f --lines=50
            ;;
        2)
            sudo journalctl -u gunicorn -f --lines=50
            ;;
        3)
            sudo journalctl -f -u nginx -u gunicorn --lines=30
            ;;
        4)
            # Logs personalizados do Django
            if [ -f "$PROJECT_DIR/logs/auth.log" ]; then
                sudo tail -f $PROJECT_DIR/logs/auth.log
            else
                print_warning "Arquivo de logs Django não encontrado"
            fi
            ;;
        *)
            print_error "Opção inválida"
            ;;
    esac
}

# Função para recarregar configurações
reload_configs() {
    print_status "Recarregando configurações..."

    # Recarregar systemd
    sudo systemctl daemon-reload

    # Recarregar Nginx (sem reiniciar - zero downtime)
    sudo nginx -t && sudo systemctl reload nginx

    # Recarregar Gunicorn (com graceful restart)
    sudo systemctl reload gunicorn 2>/dev/null || sudo systemctl restart gunicorn
    
    print_success "Configurações recarregadas"
}

# Menu principal
case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    reload)
        reload_configs
        ;;
    django-only)
        restart_django
        ;;
    nginx-only)
        restart_nginx
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|reload|django-only|nginx-only}"
        echo ""
        echo "Comandos disponíveis:"
        echo "  start       - Iniciar todos os serviços"
        echo "  stop        - Parar todos os serviços"
        echo "  restart     - Reiniciar todos os serviços"
        echo "  status      - Verificar status dos serviços"
        echo "  logs        - Mostrar logs em tempo real"
        echo "  reload      - Recarregar configurações (zero downtime)"
        echo "  django-only - Reiniciar apenas Django/Gunicorn"
        echo "  nginx-only  - Reiniciar apenas Nginx"
        exit 1
esac
