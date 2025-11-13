#!/bin/bash
# Script para ajustar timeout do Gunicorn para sincronizações longas

echo "🔧 Ajustando timeout do Gunicorn para sincronizações longas..."

# Backup do arquivo atual
sudo cp /etc/systemd/system/gunicorn.service /etc/systemd/system/gunicorn.service.backup

# Criar novo arquivo de serviço com timeout maior
sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<EOF
[Unit]
Description=gunicorn daemon para Sistema Mr Baruch
After=network.target

[Service]
User=mrbaruch
Group=www-data
WorkingDirectory=/home/mrbaruch/sistemaMrBaruchProjeto
ExecStart=/home/mrbaruch/venv/bin/gunicorn \\
          --access-logfile - \\
          --workers 3 \\
          --timeout 300 \\
          --graceful-timeout 300 \\
          --bind unix:/run/gunicorn.sock \\
          sistemaMrBaruchProjeto.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Arquivo de serviço atualizado com timeout de 300 segundos (5 minutos)"

# Recarregar systemd
echo "🔄 Recarregando systemd..."
sudo systemctl daemon-reload

# Reiniciar Gunicorn
echo "🔄 Reiniciando Gunicorn..."
sudo systemctl restart gunicorn

# Verificar status
echo "📊 Status do Gunicorn:"
sudo systemctl status gunicorn --no-pager

echo ""
echo "✅ Configuração concluída!"
echo "O Gunicorn agora aguarda até 5 minutos antes de matar processos longos."
