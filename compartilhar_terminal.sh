#!/bin/bash
echo "=========================================================="
echo "      Iniciando Compartilhamento do SoyTerminal           "
echo "=========================================================="
echo "Porta local: 5006"
echo "Pressione CTRL+C a qualquer momento para fechar o túnel."
echo "=========================================================="
echo ""
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:localhost:5006 nokey@localhost.run
