import os
import sys
import datetime
import pytz
import yfinance as yf
import urllib.request
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Agribusiness Palette Colors
DARK_GREEN = colors.HexColor("#1b4332")   # Primary - Forest Green
LEAF_GREEN = colors.HexColor("#2d6a4f")   # Secondary - Deep Leaf Green
LIGHT_GREEN = colors.HexColor("#d8f3dc")  # Backgrounds - Light Green Mint
GOLD = colors.HexColor("#d4a373")         # Accent - Soybean Gold
DARK_TEXT = colors.HexColor("#212529")    # Body Text - Charcoal
LIGHT_TEXT = colors.HexColor("#f8f9fa")   # Light Text - Cool Grey
RED_DOWN = colors.HexColor("#d90429")     # Down Variance - Red
GREEN_UP = colors.HexColor("#38b000")     # Up Variance - Green

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to calculate the total page count dynamically.
    For a one-page dashboard, it keeps it perfect.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(DARK_TEXT)
        # Draw a line at the footer
        self.setStrokeColor(colors.HexColor("#ccc"))
        self.setLineWidth(0.5)
        self.line(36, 45, A4[0] - 36, 45)
        
        # Left-aligned shortened footer text
        self.drawString(36, 30, "AGROFOODS COMERCIAL")
        
        # Center-aligned Signature Phrase
        self.setFont("Helvetica-Oblique", 7.5)
        signature = '"Rodrigo Ramos - Desenvolvendo pessoas e fortalecendo negócios"'
        self.drawCentredString(A4[0]/2.0, 30, signature)
        
        # Right-aligned page number
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[0] - 36, 30, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()

def fetch_noticias_agricolas():
    """Scrapes the latest news articles from Noticias Agricolas Soybean section."""
    url = 'https://www.noticiasagricolas.com.br/noticias/soja/'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    news = []
    try:
        print("Scraping live agricultural news from Noticias Agricolas...")
        with urllib.request.urlopen(req) as r:
            html = r.read()
        soup = BeautifulSoup(html, 'html.parser')
        
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and ('/noticias/soja/' in href) and href.endswith('.html'):
                full_url = f"https://www.noticiasagricolas.com.br{href}"
                if full_url not in [l[0] for l in links]:
                    h2 = link.find('h2')
                    title = h2.text.strip() if h2 else link.text.strip()
                    if '\n' in title:
                        title = title.split('\n')[-1].strip()
                    if len(title) > 20:
                        links.append((full_url, title))
                        if len(links) >= 3:
                            break
                            
        for full_url, title in links:
            art_req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(art_req) as art_r:
                    art_html = art_r.read()
                art_soup = BeautifulSoup(art_html, 'html.parser')
                desc = ""
                for p in art_soup.find_all('p'):
                    p_text = p.text.strip()
                    if len(p_text) > 80 and not p_text.startswith("Se inscreva") and not p_text.startswith("Quer receber"):
                        desc = p_text
                        break
                if desc:
                    if len(desc) > 200:
                        desc = desc[:197].strip() + "..."
                    news.append((title, desc))
            except Exception as e:
                print(f"Error fetching article details for {full_url}: {e}")
    except Exception as e:
        print(f"Error scraping news index: {e}")
        
    return news

def fetch_quotes():
    """Fetches market quotes for the report, using the last completed day's data."""
    tickers = {
        "soja_grao": "ZS=F",        # CBOT Soybean Grain Futures
        "soja_oleo": "ZL=F",        # CBOT Soybean Oil Futures
        "dolar": "USDBRL=X",        # USD/BRL Exchange Rate
        "petroleo_wti": "CL=F",     # WTI Crude Oil
        "petroleo_brent": "BZ=F",   # Brent Crude Oil
    }
    
    data = {}
    print("Fetching live soybean and energy quotes...")
    
    # Get current Brazil date to identify today's in-progress bar
    tz = pytz.timezone('America/Sao_Paulo')
    today_str = datetime.datetime.now(tz).strftime('%Y-%m-%d')
    
    for key, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="30d")
            if not hist.empty:
                # Find the last completed trading day
                last_row_date = hist.index[-1].strftime('%Y-%m-%d')
                if last_row_date >= today_str and len(hist) > 2:
                    last_row = hist.iloc[-2]
                    prev_row = hist.iloc[-3]
                    date_used = hist.index[-2]
                elif len(hist) > 1:
                    last_row = hist.iloc[-1]
                    prev_row = hist.iloc[-2]
                    date_used = hist.index[-1]
                else:
                    last_row = hist.iloc[-1]
                    prev_row = last_row
                    date_used = hist.index[-1]
                
                price = float(last_row["Close"])
                prev_price = float(prev_row["Close"])
                change = price - prev_price
                pct_change = (change / prev_price) * 100
                
                # Calculate 30-day trend
                price_30d_ago = float(hist.iloc[0]["Close"])
                pct_change_30d = ((price - price_30d_ago) / price_30d_ago) * 100
                if pct_change_30d > 2.0:
                    trend = "Alta"
                elif pct_change_30d < -2.0:
                    trend = "Baixa"
                else:
                    trend = "Estável"
                
                print(f"Fetched {symbol} ({key}): price={price:.4f}, change={change:.4f}, pct_change={pct_change:.2f}%, last_date={date_used.strftime('%Y-%m-%d')}")
                data[key] = {
                    "symbol": symbol,
                    "price": price,
                    "change": change,
                    "pct_change": pct_change,
                    "high": float(last_row["High"]),
                    "low": float(last_row["Low"]),
                    "trend": trend,
                    "date": date_used.strftime('%d/%m')
                }
            else:
                print(f"Empty history for {symbol} ({key}). Using fallback.")
                data[key] = get_fallback_quote(key)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}. Using fallback.")
            data[key] = get_fallback_quote(key)
            
    # Calculate B3 Soybean bag price: ((CBOT Soybean + 80 Premium) / 100) * 2.20462 * USD/BRL
    if "soja_grao" in data and "dolar" in data:
        cbot_grain = data["soja_grao"]["price"]
        usd_brl = data["dolar"]["price"]
        b3_price = ((cbot_grain + 80.0) / 100.0) * 2.20462 * usd_brl
        
        # Calculate exact B3 change
        grain_change = data["soja_grao"]["change"]
        usd_change = data["dolar"]["change"]
        
        cbot_prev = cbot_grain - grain_change
        usd_prev = usd_brl - usd_change
        
        b3_prev = ((cbot_prev + 80.0) / 100.0) * 2.20462 * usd_prev
        b3_change = b3_price - b3_prev
        b3_pct = (b3_change / b3_prev) * 100 if b3_prev != 0 else 0
        
        data["soja_b3"] = {
            "symbol": "SJC (Calc)",
            "price": b3_price,
            "change": b3_change,
            "pct_change": b3_pct,
            "trend": data["soja_grao"].get("trend", "Alta"),
            "date": data["soja_grao"].get("date", "")
        }
    
    # Calculate Soybean oil price in USD/ton: ZL=F (cents/lb) * 22.0462
    if "soja_oleo" in data:
        cbot_oil_cents = data["soja_oleo"]["price"]
        oil_usd_ton = cbot_oil_cents * 22.0462
        data["soja_oleo"]["usd_ton"] = oil_usd_ton
        
    return data

def get_fallback_quote(key):
    """Fallback values representing realistic market data in case of fetch errors."""
    defaults = {
        "soja_grao": {"symbol": "ZS=F", "price": 1188.50, "change": 4.5, "pct_change": 0.38, "high": 1195.0, "low": 1182.0, "trend": "Alta"},
        "soja_oleo": {"symbol": "ZL=F", "price": 75.32, "change": 1.12, "pct_change": 1.51, "high": 76.10, "low": 74.20, "trend": "Alta"},
        "dolar": {"symbol": "USDBRL=X", "price": 5.0245, "change": 0.0125, "pct_change": 0.25, "high": 5.0450, "low": 4.9980, "trend": "Estável"},
        "petroleo_wti": {"symbol": "CL=F", "price": 78.26, "change": 0.85, "pct_change": 1.10, "high": 79.10, "low": 77.40, "trend": "Alta"},
        "petroleo_brent": {"symbol": "BZ=F", "price": 82.44, "change": 0.94, "pct_change": 1.15, "high": 83.20, "low": 81.50, "trend": "Alta"}
    }
    return defaults.get(key)

def gerar_pdf_diario(dest_path=None):
    if dest_path is None:
        dest_path = '/Users/rodrigoramos/.gemini/antigravity/scratch/analise-mercado-soja/dados/relatorios/diario_soja.pdf'
        
    # Create directory if it does not exist
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Page setup
    # 36pt margin = 0.5 inch (maximizes print space to fit 1 page)
    doc = SimpleDocTemplate(
        dest_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=15,
        bottomMargin=45
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=LIGHT_TEXT,
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=LIGHT_TEXT,
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=DARK_GREEN,
        spaceBefore=4,
        spaceAfter=2,
        borderPadding=2
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=7.8,
        textColor=DARK_TEXT,
        leading=10.5
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold',
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        textColor=LIGHT_TEXT,
        alignment=1 # Centered
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        textColor=DARK_TEXT,
        leading=9.5
    )
    
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )
    
    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=table_cell_style,
        alignment=1 # Centered
    )
    
    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=table_cell_style,
        alignment=2 # Right aligned
    )

    story = []
    
    # 1. HEADER BANNER
    now_br = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    header_data = [
        [
            Paragraph("AGROFOODS COMERCIAL", title_style),
            Paragraph(f"<b>DATA-BASE:</b> {now_br.strftime('%d/%m/%Y')} | <b>HORA:</b> {now_br.strftime('%H:%M')}", subtitle_style)
        ],
        [
            Paragraph("DIÁRIO DE MERCADO | SOJA, ÓLEOS & ENERGIA", subtitle_style),
            Paragraph("<b>INFORME EXECUTIVO TIME DE VENDAS</b>", subtitle_style)
        ]
    ]
    
    # Total printable width is A4 width (595.27) - 72 (margins) = 523.27
    header_table = Table(header_data, colWidths=[300, 223])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_GREEN),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3))
    
    # Fetch live quotes
    quotes = fetch_quotes()
    
    # 2. INDICATORS GRID
    # Columns: Indicador, Símbolo, Preço, Var. %, Tendência (30d), Farol / Leitura
    indicators_header = [
        Paragraph("Indicador de Mercado", table_header_style),
        Paragraph("Referência / Ticker", table_header_style),
        Paragraph("Preço / Fechamento", table_header_style),
        Paragraph("Variação (Diária)", table_header_style),
        Paragraph("Direção (30d)", table_header_style),
        Paragraph("Leitura Comercial Executiva", table_header_style)
    ]
    
    grid_rows = [indicators_header]
    
    # Populate quotes in grid
    items_to_display = [
        ("Óleo de Soja CBOT", "soja_oleo", "cents/lb", "ZL=F", "Alta Forte", "Driver central da rentabilidade e do piso de preço."),
        ("Soja Grão CBOT", "soja_grao", "cents/bu", "ZS=F", "Alta", "Sustenta custo do esmagamento global."),
        ("Soja B3 (Física Calc.)", "soja_b3", "R$/sc 60kg", "SJC (Calc)", "Alta", "Preço de paridade da saca física no mercado interno."),
        ("Dólar Comercial", "dolar", "R$/USD", "USDBRL=X", "Volátil", "Define repasse industrial e margem de esmagadores."),
        ("Petróleo WTI (Nymex)", "petroleo_wti", "USD/barril", "CL=F", "Alta", "Piso de energia sustentando biodiesel nos EUA."),
        ("Petróleo Brent (ICE)", "petroleo_brent", "USD/barril", "BZ=F", "Alta", "Seta custos globais de frete e refino.")
    ]
    
    for label, key, unit, ticker_symbol, trend, reading in items_to_display:
        q = quotes.get(key)
        if q:
            price_val = q["price"]
            change_pct = q["pct_change"]
            
            # Format price
            if key == "dolar":
                price_str = f"R$ {price_val:.4f}"
            elif key == "soja_b3":
                price_str = f"R$ {price_val:.2f} /sc"
            elif key == "soja_oleo":
                price_str = f"{price_val:.2f} ¢/lb\n(USD {q['usd_ton']:.1f}/t)"
            elif key == "soja_grao":
                price_str = f"{price_val:.2f} ¢/bu"
            else:
                price_str = f"USD {price_val:.2f}"
                
            # Format variation
            sign = "+" if change_pct >= 0 else ""
            color_text = GREEN_UP if change_pct >= 0 else RED_DOWN
            arrow = "▲" if change_pct >= 0 else "▼"
            var_paragraph = Paragraph(f"<font color='{color_text}'><b>{arrow} {sign}{change_pct:.2f}%</b></font>", table_cell_center)
            
            dynamic_trend = q.get("trend", trend)
            date_str = q.get("date", "")
            ticker_display = f"{ticker_symbol}<br/><font size='5.5' color='#666'>Ref: {date_str}</font>" if date_str else ticker_symbol
            
            grid_rows.append([
                Paragraph(f"<b>{label}</b>", table_cell_bold),
                Paragraph(f"{ticker_display}", table_cell_center),
                Paragraph(f"{price_str}", table_cell_center),
                var_paragraph,
                Paragraph(f"<b>{dynamic_trend}</b>", table_cell_center),
                Paragraph(f"{reading}", table_cell_style)
            ])
            
    grid_table = Table(grid_rows, colWidths=[110, 65, 95, 75, 60, 118])
    grid_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK_GREEN),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ccc")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    
    story.append(grid_table)
    story.append(Spacer(1, 3))
    
    # 3. TAKEAWAYS ESTRATÉGICOS & ANÁLISE DE MERCADO
    story.append(Paragraph("TAKEAWAYS ESTRATÉGICOS (ÓLEO DE SOJA & DIRETRIZ COMERCIAL)", section_title_style))
    
    # Dynamically generate takeaways based on CBOT Soybean Oil status
    trend_oleo = quotes.get("soja_oleo", {}).get("trend", "Alta")
    
    if trend_oleo == "Alta":
        takeaway_points = [
            "<b>Ativo Energético:</b> O óleo de soja continua operando descolado da dinâmica alimentar tradicional, respondendo diretamente ao piso dos combustíveis renováveis (biodiesel no Brasil e renewable diesel nos EUA).",
            "<b>Esmagamento e Demanda:</b> A forte demanda doméstica para o mandato B15 a B16 no Brasil limita a disponibilidade de óleo para exportação e mantém os prêmios portuários nacionais extremamente firmes.",
            "<b>Câmbio Protetor:</b> A volatilidade cambial (dólar operando no range R$ 5,00 - R$ 5,10) atua como colchão para os preços físicos no porto, atenuando flutuações intradiárias da CBOT.",
            "<b>Narrativa de Vendas B2B:</b> O time comercial não deve vender o balde baseado apenas em preço por quilo. O foco deve ser o <b>custo por fritura produzida</b>, rendimento e estabilidade do produto em alta temperatura."
        ]
    else:
        takeaway_points = [
            "<b>Pressão de Safra:</b> O ritmo avançado da colheita sul-americana e a perspectiva de grande área plantada de soja nos EUA trazem pressão técnica para os grãos na bolsa de Chicago.",
            "<b>Arbitragem de Importação:</b> O esmagamento acelerado nos EUA gera abundância local de óleo vegetal, reduzindo temporariamente os prêmios de exportação na América do Norte.",
            "<b>Janela de Oportunidade:</b> Correções pontuais na CBOT e no dólar devem ser aproveitadas para <b>reforçar estoques táticos</b> de óleo de soja bruto refinado, garantindo posições antes de novos gatilhos logísticos.",
            "<b>Defesa de Mix no Campo:</b> Diante da pressão de preço das commodities, acelerar a venda do mix de **Margarinas Especiais** (margem de 20,28%) para compensar a compressão temporária de margem em óleos puros."
        ]
        
    takeaway_story = []
    for point in takeaway_points:
        takeaway_story.append(Paragraph(f"• {point}", body_style))
        takeaway_story.append(Spacer(1, 3))
        
    story.append(KeepTogether(takeaway_story))
    story.append(Spacer(1, 5))
    
    # 4. CENÁRIOS PROJETADOS — PRÓXIMOS 15 A 30 DIAS
    story.append(Paragraph("CENÁRIOS PROJETADOS & AÇÕES SUGERIDAS", section_title_style))
    
    scenarios_header = [
        Paragraph("Cenário", table_header_style),
        Paragraph("Probabilidade", table_header_style),
        Paragraph("Diretriz de Ação Comercial Sugerida", table_header_style)
    ]
    
    # Scenarios details
    scenarios_rows = [
        scenarios_header,
        [
            Paragraph("<b>Cenário Base (Firme)</b><br/>Preços laterais-altistas, óleo CBOT no canal de 73-78 ¢/lb.", table_cell_style),
            Paragraph("<b>55%</b>", table_cell_center),
            Paragraph("Defender margens contratuais, evitar posições curtas de estoque e focar no mix de valor agregado (margarinas especiais/ Sina Cheff).", table_cell_style)
        ],
        [
            Paragraph("<b>Cenário Altista (Pressão)</b><br/>Quebras climáticas nos EUA ou petróleo Brent acima de US$ 88.", table_cell_style),
            Paragraph("<b>30%</b>", table_cell_center),
            Paragraph("Disparar gatilhos rápidos de repasse de preço semanais e reduzir o prazo de cotações comerciais para no máximo 3 dias.", table_cell_style)
        ],
        [
            Paragraph("<b>Cenário de Correção</b><br/>Clima ideal nos EUA e aumento de esmagamento no Brasil.", table_cell_style),
            Paragraph("<b>15%</b>", table_cell_center),
            Paragraph("Aproveitar realizações técnicas em Chicago para compra de matéria-prima e fechamento de contratos táticos com distribuidores.", table_cell_style)
        ]
    ]
    
    scenarios_table = Table(scenarios_rows, colWidths=[150, 75, 298])
    scenarios_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LEAF_GREEN),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ccc")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(scenarios_table)
    story.append(Spacer(1, 3))
    
    # 5. NOTÍCIAS DE IMPACTO & MONITORAMENTO
    story.append(Paragraph("RADAR DE NOTÍCIAS DO SETOR & DIREÇÃO DO CAMPO", section_title_style))
    
    brent_price = quotes.get("petroleo_brent", {}).get("price", 82.0)
    usd_price = quotes.get("dolar", {}).get("price", 5.00)
    
    # Try fetching dynamic agricultural news, fallback to templates if empty
    news_items = fetch_noticias_agricolas()
    if not news_items:
        news_items = [
            ("Mandato de Biodiesel & Petróleo: Sustentação de Demanda por Óleo de Soja", f"Com o petróleo Brent cotado a USD {brent_price:.1f}/barril, a viabilidade do biodiesel se mantém elevada. O óleo de soja, principal insumo nacional, ganha suporte direto do mercado internacional de energia."),
            (f"Câmbio & Competitividade: Dólar a R$ {usd_price:.2f} atua como Amortecedor Cambial", "A moeda americana valorizada compensa flutuações intradiárias da soja em grão na CBOT, mantendo firmes as margens de esmagamento e os preços da saca no mercado físico interno."),
            ("Arbitragem Global de Óleos: Custos de frete e refino doméstico de soja", "A combinação de dólar firme e frete logístico pressionado eleva a competitividade do esmagamento local de soja, limitando o espaço para óleos concorrentes importados no refino.")
        ]
        
    news_story = []
    for title, desc in news_items:
        news_story.append(Paragraph(f"<b>{title}</b>", bold_body_style))
        news_story.append(Paragraph(desc, body_style))
        news_story.append(Spacer(1, 4))
        
    story.append(KeepTogether(news_story))
    
    # 6. ACTION TODAY PANEL
    story.append(Spacer(1, 4))
    action_box_content = [
        Paragraph("<b>ACTION TODAY | DIRETRIZ DE CAMPO PARA OS VENDEDORES:</b>", bold_body_style),
        Paragraph("1. Apresentar aos clientes de fritura (redes e operadores) o rendimento em ciclos de fritura em vez de preço por quilo.", body_style),
        Paragraph("2. Priorizar a venda cruzada de **Margarinas Especiais Sina Cheff (margem de 20,28%)** em padarias e confeitarias de alta rotação.", body_style),
        Paragraph("3. Monitorar: óleo CBOT sustentado acima de 75 c/lb e taxa cambial USD/BRL acima de R$ 5,05 como gatilho de reajuste automático.", body_style)
    ]
    
    action_table = Table([[action_box_content]], colWidths=[523])
    action_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), LIGHT_GREEN),
        ('BOX', (0,0), (0,0), 1, LEAF_GREEN),
        ('PADDING', (0,0), (0,0), 8),
        ('VALIGN', (0,0), (0,0), 'TOP'),
        ('TOPPADDING', (0,0), (0,0), 4),
        ('BOTTOMPADDING', (0,0), (0,0), 4),
    ]))
    
    story.append(action_table)

    # Build the document using the NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully at: {dest_path}")
    
    # Also save a copy in the Downloads folder so it is easily accessible
    downloads_path = '/Users/rodrigoramos/Downloads/AGROFOODS_DAILY_MARKET_INTELLIGENCE.pdf'
    import shutil
    try:
        shutil.copy2(dest_path, downloads_path)
        print(f"Copy saved to Downloads: {downloads_path}")
    except Exception as e:
        print(f"Error copying to Downloads: {e}")
        
    return dest_path

if __name__ == "__main__":
    gerar_pdf_diario()
