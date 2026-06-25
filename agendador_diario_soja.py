import os
import sys
import json
import time
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Add directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gerar_pdf_soja import gerar_pdf_diario, fetch_quotes

def ler_config_email():
    """Reads email configuration from env vars, local config file or fallback."""
    # Prioritize environment variables (useful for GitHub Actions / cloud deployment)
    env_sender = os.environ.get("SENDER_EMAIL")
    env_password = os.environ.get("SENDER_PASSWORD")
    
    if env_sender and env_password:
        dest_simone = os.environ.get("RECIPIENT_SIMONE", "simone.santos@agrofoods.ind.br")
        dest_aldenor = os.environ.get("RECIPIENT_ALDENOR", "aldenor.filho@agrofoods.ind.br")
        dest_rodrigo = os.environ.get("RECIPIENT_RODRIGO", "rodrigooctavioramos@gmail.com")
        
        return {
            "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
            "sender_email": env_sender,
            "sender_password": env_password,
            "use_tls": os.environ.get("USE_TLS", "true").lower() == "true",
            "destinatarios": {
                "3100 - SIMONE MONTEIRO DOS SANTOS": dest_simone,
                "3300 - ALDENOR OLIVEIRA": dest_aldenor,
                "3700 - RODRIGO OCTAVIO DE CAMPOS RAMOS": dest_rodrigo
            }
        }

    # Fallback to local config files
    local_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'config_email.json')
    sales_config = '/Users/rodrigoramos/.gemini/antigravity/scratch/analise-vendas/dados/config_email.json'
    
    config_path = local_config if os.path.exists(local_config) else sales_config
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler config_email.json: {e}")
            
    # Default fallback
    return {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "seu-email@empresa.com.br",
        "sender_password": "sua-senha",
        "destinatarios": {
            "time_vendas": "vendas.foodservice@empresa.com.br",
            "admin": "rodrigo.ramos@empresa.com.br"
        }
    }

def enviar_email_diario(pdf_path, config):
    """Sends the daily PDF report via email (or simulates if credentials are mock)."""
    sender_email = config.get('sender_email')
    sender_password = config.get('sender_password')
    
    # Destinatarios setup
    destinatarios = config.get('destinatarios', {})
    dest_list = [v for k, v in destinatarios.items() if k != 'admin']
    
    # Também inclui o próprio remetente nos destinatários para ele receber e confirmar
    if sender_email and sender_email not in dest_list:
        dest_list.append(sender_email)
        
    admin_email = None
    
    is_mock = (
        not sender_email or 
        "seu-email" in sender_email or 
        "sua-senha" in sender_password
    )
    
    assunto = f"DIÁRIO DE MERCADO AGROFOODS - SOJA & ENERGIA - {datetime.datetime.now().strftime('%d/%m/%Y')}"
    
    corpo = f"""Olá Equipe de Vendas Food Service,

Segue em anexo o **Diário de Mercado Agrofoods | Soja, Óleos & Energia** de hoje, {datetime.datetime.now().strftime('%d/%m/%Y')}.

Neste informe você encontrará:
1. Cotações atualizadas: Óleo de Soja CBOT, Soja Grão, Dólar, Petróleo WTI e Brent.
2. Análise técnica e fundamentada da dinâmica de biocombustíveis.
3. Cenários e Diretrizes Comerciais para negociação no campo.
4. Notícias críticas e ações sugeridas ("Action Today").

Utilizem as informações técnicas para agregar valor comercial nas abordagens diárias com nossos clientes!

Atenciosamente,
Rodrigo Ramos | Head Comercial Food Service
"Rodrigo Ramos - Desenvolvendo pessoas e fortalecendo negócios"
"""

    if is_mock:
        mock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'relatorios', f"mock_email_diario_mercado.txt")
        try:
            with open(mock_path, 'w', encoding='utf-8') as f:
                f.write(f"De: {sender_email or 'sistema@agrofoods.com.br'}\n")
                f.write(f"Para: {', '.join(dest_list)}\n")
                if admin_email:
                    f.write(f"Cc: {admin_email}\n")
                f.write(f"Assunto: {assunto}\n")
                f.write(f"Anexo: {os.path.basename(pdf_path)}\n")
                f.write("-" * 50 + "\n")
                f.write(corpo)
            print(f"[MOCK] SMTP não configurado. E-mail diário simulado salvo em: {mock_path}")
            return True
        except Exception as e:
            print(f"Erro ao salvar mock de e-mail diário: {e}")
            return False

    # Real SMTP Send
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(dest_list)
        if admin_email:
            msg['Cc'] = admin_email
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(pdf_path)}"')
                msg.attach(part)
        else:
            print(f"Arquivo PDF não encontrado para anexar: {pdf_path}")
            return False
            
        server = smtplib.SMTP(config.get('smtp_server', 'smtp.gmail.com'), config.get('smtp_port', 587))
        if config.get('use_tls', True):
            server.starttls()
            
        server.login(sender_email, sender_password)
        
        all_recipients = dest_list.copy()
        if admin_email:
            all_recipients.append(admin_email)
            
        server.sendmail(sender_email, all_recipients, msg.as_string())
        server.quit()
        
        print(f"E-mail diário enviado com sucesso para a equipe ({', '.join(dest_list)})")
        return True
    except Exception as e:
        print(f"Falha ao enviar e-mail real do Diário de Mercado: {e}")
        return False

def executar_agendamento_diario():
    print(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando automação Diário de Mercado Soja...")
    config = ler_config_email()
    
    # 1. Generate PDF
    # Save a dated version in the archive
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    archive_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'relatorios', f"diario_soja_{today_str}.pdf")
    
    # Generate main PDF
    gerar_pdf_diario(archive_pdf_path)
    
    # Copy to the standard location for email attachment
    standard_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'relatorios', 'diario_soja.pdf')
    import shutil
    try:
        shutil.copy2(archive_pdf_path, standard_pdf_path)
    except Exception as e:
        print("Erro ao copiar para local padrão:", e)
        
    # 2. Send email
    if os.path.exists(standard_pdf_path):
        enviar_email_diario(standard_pdf_path, config)
    else:
        print("Erro: Diário de Mercado em PDF não pôde ser gerado.")
        
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Automação Diário de Mercado concluída!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agendador de relatórios diários de Soja & Energia")
    parser.add_argument('--now', action='store_true', help="Executa e envia o relatório diário imediatamente")
    parser.add_argument('--loop', action='store_true', help="Inicia o loop contínuo de verificação de horários")
    
    args = parser.parse_args()
    
    if args.now:
        executar_agendamento_diario()
    elif args.loop:
        print("Iniciando loop do agendador diário em background. Pressione CTRL+C para parar.")
        ja_enviado_hoje = False
        
        while True:
            agora = datetime.datetime.now()
            hora_atual = agora.strftime("%H:%M")
            
            # Execute daily at 08:00 AM
            if hora_atual == "08:00" and not ja_enviado_hoje:
                executar_agendamento_diario()
                ja_enviado_hoje = True
            elif hora_atual != "08:00":
                ja_enviado_hoje = False
                
            time.sleep(30) # check every 30 seconds
    else:
        # Default behavior: run immediate test
        print("Nenhum argumento fornecido. Executando envio imediato do Diário de Mercado...")
        executar_agendamento_diario()
