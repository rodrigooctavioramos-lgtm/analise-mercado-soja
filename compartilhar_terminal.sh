#!/bin/bash
echo "=========================================================="
echo "      Iniciando Compartilhamento do SoyTerminal           "
echo "=========================================================="
echo "Porta local: 5006"
echo "Pressione CTRL+C a qualquer momento para fechar o túnel."
echo "=========================================================="
echo ""
while true; do
    ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:localhost:5006 serveo.net
    echo "Conexão interrompida. Tentando reconectar em 10 segundos..."
    sleep 10
done
