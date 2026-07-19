import os
import sys
import json
import time
import datetime
import pytz
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
    env_sender = os.environ.get("SENDER_EMAIL") or "rodrigooctavioramos@gmail.com"
    env_password = os.environ.get("SENDER_PASSWORD")
    
    if env_password:
        dest_simone = os.environ.get("RECIPIENT_SIMONE") or "simone.santos@agrofoods.ind.br"
        dest_aldenor = os.environ.get("RECIPIENT_ALDENOR") or "aldenor.filho@agrofoods.ind.br"
        dest_rodrigo = os.environ.get("RECIPIENT_RODRIGO") or "rodrigooctavioramos@gmail.com"
        
        return {
            "smtp_server": os.environ.get("SMTP_SERVER") or "smtp.gmail.com",
            "smtp_port": int(os.environ.get("SMTP_PORT") or 587),
            "sender_email": env_sender,
            "sender_password": env_password,
            "use_tls": (os.environ.get("USE_TLS") or "true").lower() == "true",
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

def build_html_email(quotes, now_br):
    """Constructs a premium HTML email body representing the daily market dashboard."""
    # Load manual.json data
    manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'manual.json')
    manual_data = {}
    if os.path.exists(manual_path):
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                manual_data = json.load(f)
        except Exception as e:
            print(f"Error loading manual.json: {e}")
            
    today_str = now_br.strftime('%d/%m/%Y')
    
    # 1. Gather variables
    zl = quotes.get("soja_oleo", {})
    cepea = quotes.get("cepea_sp", {})
    arg = quotes.get("argentina_fob", {})
    palm = quotes.get("malaysia_palm", {})
    dolar = quotes.get("dolar", {})
    brent = quotes.get("petroleo_brent", {})
    
    # Chicago CBOT (ZL) format
    zl_price = f"{zl.get('price', 0.0):.2f} ¢/lb" if 'price' in zl else "N/D"
    zl_change_pct = zl.get('pct_change', 0.0)
    zl_color = '#1b4332' if zl_change_pct >= 0 else '#9c4221'
    zl_arrow = '▲' if zl_change_pct >= 0 else '▼'
    zl_sign = '+' if zl_change_pct >= 0 else ''
    if 'usd_ton' in zl:
        zl_price += f" (USD {zl['usd_ton']:.1f}/t)"
    
    # Brent format
    brent_price = f"USD {brent.get('price', 0.0):.2f}" if 'price' in brent else "N/D"
    brent_change_pct = brent.get('pct_change', 0.0)
    brent_color = '#1b4332' if brent_change_pct >= 0 else '#9c4221'
    brent_arrow = '▲' if brent_change_pct >= 0 else '▼'
    brent_sign = '+' if brent_change_pct >= 0 else ''
    
    # Dolar format
    dolar_price = f"R$ {dolar.get('price', 0.0):.4f}" if 'dolar' in locals() and 'price' in dolar else "N/D"
    dolar_change_pct = dolar.get('pct_change', 0.0)
    dolar_color = '#1b4332' if dolar_change_pct >= 0 else '#9c4221'
    dolar_arrow = '▲' if dolar_change_pct >= 0 else '▼'
    dolar_sign = '+' if dolar_change_pct >= 0 else ''
    
    # Palma format
    palm_change_pct = palm.get('pct_change', 0.0)
    palm_color = '#1b4332' if palm_change_pct >= 0 else '#9c4221'
    palm_arrow = '▲' if palm_change_pct >= 0 else '▼'
    palm_sign = '+' if palm_change_pct >= 0 else ''
    
    # Headline format
    headline = manual_data.get("headline_dia", {})
    headline_title = headline.get("title", "N/D")
    headline_summary = headline.get("summary", "N/D")
    
    # Dynamic Takeaways based on CBOT Soybean Oil status
    trend_oleo = zl.get("trend", "Alta")
    if trend_oleo == "Alta":
        takeaway_points = [
            "<b>Ativo Energético:</b> O óleo de soja continua operando descolado da dinâmica alimentar tradicional, respondendo diretamente ao piso dos combustíveis renováveis (biodiesel no Brasil e renewable diesel nos EUA).",
            "<b>Esmagamento e Demanda:</b> A forte demanda doméstica para o mandato B15 a B16 no Brasil limita a disponibilidade de óleo para exportação e mantém os prêmios portuários nacionais extremamente firmes.",
            "<b>Câmbio Protetor:</b> A volatilidade cambial atua como colchão para os preços físicos no porto, atenuando flutuações intradiárias da CBOT.",
            "<b>Narrativa de Vendas B2B:</b> O time comercial não deve vender o balde baseado apenas em preço por quilo. O foco deve ser o <b>custo por fritura produzida</b>, rendimento e estabilidade do produto em alta temperatura."
        ]
    else:
        takeaway_points = [
            "<b>Pressão de Safra:</b> O ritmo avançado da colheita sul-americana e a perspectiva de grande área plantada de soja nos EUA trazem pressão técnica para os grãos na bolsa de Chicago.",
            "<b>Arbitragem de Importação:</b> O esmagamento acelerado nos EUA gera abundância local de óleo vegetal, reduzindo temporariamente os prêmios de exportação na América do Norte.",
            "<b>Janela de Oportunidade:</b> Correções pontuais na CBOT e no dólar devem ser aproveitadas para <b>reforçar estoques táticos</b> de óleo de soja bruto refinado, garantindo posições antes de novos gatilhos logísticos.",
            "<b>Defesa de Mix no Campo:</b> Diante da pressão de preço das commodities, acelerar a venda do mix de <b>Margarinas Especiais (margem de 20,28%)</b> para compensar a compressão temporária de margem em óleos puros."
        ]
        
    takeaways_html = "".join([f"<li style='margin-bottom: 8px;'>{pt}</li>" for pt in takeaway_points])

    html_content = f"""
    <html>
    <body style="font-family:Calibri,Arial,sans-serif;background:#F7F5F0;padding:24px;color:#212529;margin:0;">
      <div style="max-width:680px;margin:0 auto;background:#FCFBF8;border:1px solid #DDD8CC;box-shadow:0 4px 8px rgba(0,0,0,0.05);">
        <!-- HEADER -->
        <div style="background:#1b4332;color:#F7F5F0;padding:20px 24px;border-bottom:4px solid #d4a373;">
          <table width="100%" style="border-collapse:collapse;">
            <tr>
              <td>
                <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#d4a373;font-weight:bold;">Agrofoods · Inteligência de Mercado</div>
                <div style="font-family:Georgia,serif;font-size:22px;font-weight:normal;margin-top:4px;">Óleo de Soja Global & Energia</div>
              </td>
              <td align="right" valign="bottom" style="font-size:12px;color:#d8f3dc;line-height:1.5;">
                <b>DATA-BASE:</b> {today_str}<br/>
                <b>RELATÓRIO DIÁRIO</b>
              </td>
            </tr>
          </table>
        </div>
        
        <!-- CONTENT -->
        <div style="padding:24px;">
          <!-- INTRO -->
          <p style="margin-top:0;font-size:14px;color:#4A4A44;line-height:1.6;">
            Olá Equipe de Vendas Food Service,<br/><br/>
            Abaixo estão as cotações de fechamento consolidadas, destaques estratégicos e diretrizes para atuação comercial em campo hoje. O relatório completo em PDF está anexado a este e-mail.
          </p>

          <!-- TICKET GRID (2 COLUMNS TABLE) -->
          <h3 style="color:#1b4332;border-bottom:1px solid #d8f3dc;padding-bottom:6px;font-size:15px;margin-top:24px;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">Painel de Indicadores Globais</h3>
          <table width="100%" style="border-collapse:collapse;margin-bottom:24px;font-size:13px;">
            <tr>
              <!-- Chicago ZL -->
              <td width="50%" style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Chicago (CBOT ZL)</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{zl_price}</div>
                <div style="font-size:11px;color:{zl_color};font-weight:bold;">
                  {zl_arrow} {zl_sign}{zl_change_pct:.2f}% <span style="font-weight:normal;color:#8A8272;">(Ref: {zl.get('date', '')})</span>
                </div>
              </td>
              <!-- Brasil Cepea -->
              <td width="50%" style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Brasil (Cepea SP)</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{cepea.get('price_str', 'N/D')}</div>
                <div style="font-size:11px;color:#4A4A44;font-weight:bold;">
                  Estável <span style="font-weight:normal;color:#8A8272;">(Ref: {cepea.get('date', '')})</span>
                </div>
              </td>
            </tr>
            <tr>
              <!-- Argentina FOB -->
              <td style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Argentina FOB (Rosario)</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{arg.get('price_str', 'N/D')}</div>
                <div style="font-size:11px;color:#4A4A44;font-weight:bold;">
                  Estável <span style="font-weight:normal;color:#8A8272;">(Ref: {arg.get('date', '')})</span>
                </div>
              </td>
              <!-- Malásia Palma -->
              <td style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Malásia Palma (Bursa)</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{palm.get('price_str', 'N/D')}</div>
                <div style="font-size:11px;color:{palm_color};font-weight:bold;">
                  {palm_arrow} {palm_sign}{palm_change_pct:.2f}% <span style="font-weight:normal;color:#8A8272;">(Ref: {palm.get('date', '')})</span>
                </div>
              </td>
            </tr>
            <tr>
              <!-- Dólar -->
              <td style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Dólar Comercial</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{dolar_price}</div>
                <div style="font-size:11px;color:{dolar_color};font-weight:bold;">
                  {dolar_arrow} {dolar_sign}{dolar_change_pct:.2f}% <span style="font-weight:normal;color:#8A8272;">(Ref: {dolar.get('date', '')})</span>
                </div>
              </td>
              <!-- Brent -->
              <td style="padding:12px;border:1px solid #DDD8CC;background:#FCFBF8;" valign="top">
                <div style="font-size:10px;color:#8A8272;text-transform:uppercase;font-weight:bold;">Petróleo Brent (ICE)</div>
                <div style="font-family:Consolas,monospace;font-size:18px;font-weight:bold;margin:4px 0 2px;color:#1b4332;">{brent_price}</div>
                <div style="font-size:11px;color:{brent_color};font-weight:bold;">
                  {brent_arrow} {brent_sign}{brent_change_pct:.2f}% <span style="font-weight:normal;color:#8A8272;">(Ref: {brent.get('date', '')})</span>
                </div>
              </td>
            </tr>
          </table>

          <!-- DESTAQUES / TAKEAWAYS -->
          <h3 style="color:#1b4332;border-bottom:1px solid #d8f3dc;padding-bottom:6px;font-size:15px;margin-top:24px;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">Destaques Estratégicos</h3>
          <ul style="padding-left:20px;font-size:13.5px;color:#333;line-height:1.6;margin-top:0;">
            {takeaways_html}
          </ul>

          <!-- CENÁRIOS PROJETADOS -->
          <h3 style="color:#1b4332;border-bottom:1px solid #d8f3dc;padding-bottom:6px;font-size:15px;margin-top:24px;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">Cenários & Projeções (Próximos 15-30 dias)</h3>
          <table width="100%" style="border-collapse:collapse;margin-bottom:24px;font-size:12.5px;">
            <tr style="background:#2d6a4f;color:#FCFBF8;font-weight:bold;">
              <td style="padding:8px;border:1px solid #DDD8CC;">Cenário</td>
              <td align="center" style="padding:8px;border:1px solid #DDD8CC;width:75px;">Prob.</td>
              <td style="padding:8px;border:1px solid #DDD8CC;">Diretriz de Ação Comercial Sugerida</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>Cenário Base (Firme)</b><br/>ZL no canal de 73-78 ¢/lb.</td>
              <td align="center" style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>55%</b></td>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;color:#4A4A44;">Defender margens contratuais, evitar posições curtas de estoque e focar no mix de valor agregado (margarinas especiais/ Sina Cheff).</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>Cenário Altista (Pressão)</b><br/>Quebras nos EUA ou Brent acima de US$ 88.</td>
              <td align="center" style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>30%</b></td>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;color:#4A4A44;">Disparar gatilhos rápidos de repasse de preço semanais e reduzir o prazo de cotações comerciais para no máximo 3 dias.</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>Cenário de Correção</b><br/>Clima ideal nos EUA e aumento de esmagamento.</td>
              <td align="center" style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;"><b>15%</b></td>
              <td style="padding:8px;border:1px solid #DDD8CC;background:#FCFBF8;color:#4A4A44;">Aproveitar realizações técnicas em Chicago para compra de matéria-prima e fechamento de contratos táticos com distribuidores.</td>
            </tr>
          </table>

          <!-- RADAR DE NOTÍCIAS / MANCHETE -->
          <h3 style="color:#1b4332;border-bottom:1px solid #d8f3dc;padding-bottom:6px;font-size:15px;margin-top:24px;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px;">Radar de Notícias do Setor</h3>
          <div style="background:#f8f9fa;border-left:4px solid #d4a373;padding:12px 16px;margin-bottom:16px;font-size:13.5px;">
            <div style="font-weight:bold;color:#1b4332;margin-bottom:4px;">Destaque do Dia: {headline_title}</div>
            <div style="color:#4A4A44;line-height:1.5;">{headline_summary}</div>
          </div>

          <!-- ACTION TODAY PANEL -->
          <div style="background:#d8f3dc;border:1px solid #2d6a4f;padding:16px;margin-top:24px;border-radius:4px;">
            <div style="font-weight:bold;color:#1b4332;font-size:14px;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">Action Today | Diretriz de Campo para Vendas:</div>
            <ol style="margin:0;padding-left:20px;font-size:13px;color:#1b4332;line-height:1.6;">
              <li>Apresentar aos clientes de fritura o rendimento em ciclos de fritura em vez de preço por quilo.</li>
              <li>Priorizar a venda cruzada de <b>Margarinas Especiais Sina Cheff (margem de 20,28%)</b> em padarias de alta rotação.</li>
              <li>Monitorar: óleo CBOT sustentado acima de 75 c/lb e taxa cambial USD/BRL acima de R$ 5,05 como gatilho de reajuste automático.</li>
            </ol>
          </div>
        </div>
        
        <!-- FOOTER -->
        <div style="padding:16px 24px;font-size:11px;color:#8a8272;background:#f8f9fa;border-top:1px solid #DDD8CC;line-height:1.5;">
          Atenciosamente,<br/>
          <b>Rodrigo Ramos | Head Comercial Food Service</b><br/>
          <i>"Rodrigo Ramos - Desenvolvendo pessoas e fortalecendo negócios"</i><br/><br/>
          Gerado automaticamente via Agrofoods Inteligência de Mercado. Fontes: Yahoo Finance, BCR Rosario, Trading Economics.
        </div>
      </div>
    </body>
    </html>
    """
    return html_content

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
        
    admin_email = destinatarios.get('admin')
    
    is_mock = (
        not sender_email or 
        "seu-email" in sender_email or 
        "sua-senha" in sender_password
    )
    
    now_br = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    assunto = f"Radar Óleo de Soja — {now_br.strftime('%d/%m/%Y')}"
    
    # Fetch latest quotes to construct HTML email
    quotes = fetch_quotes()
    html_corpo = build_html_email(quotes, now_br)
    
    if is_mock:
        mock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'relatorios', f"mock_email_diario_mercado.html")
        try:
            with open(mock_path, 'w', encoding='utf-8') as f:
                f.write(html_corpo)
            print(f"[MOCK] SMTP não configurado. E-mail diário simulado em HTML salvo em: {mock_path}")
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
        msg.attach(MIMEText(html_corpo, 'html', 'utf-8'))
        
        # PDF attachment restored per user request
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
    now_br = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    print(f"\n[{now_br.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando automação Diário de Mercado Soja...")
    config = ler_config_email()
    
    # 1. Generate PDF
    # Save a dated version in the archive
    today_str = now_br.strftime('%Y-%m-%d')
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
        
    now_br_end = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    print(f"[{now_br_end.strftime('%Y-%m-%d %H:%M:%S')}] Automação Diário de Mercado concluída!")

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
            agora = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
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
