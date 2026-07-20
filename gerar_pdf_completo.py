import os
import sys
import datetime
import pytz
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Import existing daily report functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gerar_pdf_soja import fetch_quotes, NumberedCanvas, format_date_slash

# Palette
DARK_GREEN = colors.HexColor("#1b4332")
LEAF_GREEN = colors.HexColor("#2d6a4f")
LIGHT_GREEN = colors.HexColor("#d8f3dc")
GOLD = colors.HexColor("#d4a373")
DARK_TEXT = colors.HexColor("#212529")
LIGHT_TEXT = colors.HexColor("#f8f9fa")
GREEN_UP = "#1b4332"
RED_DOWN = "#9c4221"

def gerar_pdf_completo(dest_path=None):
    if dest_path is None:
        dest_path = '/Users/rodrigoramos/Downloads/AGROFOODS_DAILY_MARKET_INTELLIGENCE_COMPLETO.pdf'
        
    # Ensure destination directory exists (critical for GitHub Actions runner)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
    doc = SimpleDocTemplate(
        dest_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=15,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        textColor=LIGHT_TEXT,
        spaceAfter=1
    )
    
    header_left_subtitle_style = ParagraphStyle(
        'HeaderLeftSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=colors.HexColor("#d8f3dc"),
        spaceBefore=2
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
    
    story = []
    
    # ------------------ PAGE 1 ------------------
    # 1. HEADER BANNER
    now_br = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    header_data = [
        [
            Paragraph("Agrofoods · Inteligência de Mercado", title_style),
            Paragraph(f"<b>DATA-BASE:</b> {now_br.strftime('%d/%m/%Y')}", subtitle_style)
        ],
        [
            Paragraph("Óleo de Soja Global & Energia", header_left_subtitle_style),
            Paragraph("<b>RELATÓRIO DIÁRIO</b>", subtitle_style)
        ]
    ]
    
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
    
    # Fetch quotes
    quotes = fetch_quotes()
    
    # 2. INDICATORS GRID
    story.append(Paragraph("PAINEL DE INDICADORES GLOBAIS", section_title_style))
    indicators_header = [
        Paragraph("Indicador", table_header_style),
        Paragraph("Ticker/Ref", table_header_style),
        Paragraph("Fechamento", table_header_style),
        Paragraph("Var. %", table_header_style),
        Paragraph("Tendência (30d)", table_header_style),
        Paragraph("Farol / Leitura de Mercado", table_header_style)
    ]
    
    grid_rows = [indicators_header]
    items_to_display = [
        ("CBOT Óleo de Soja (ZL)", "soja_oleo", "ZL=F", "Driver central da rentabilidade global do óleo."),
        ("Cepea Óleo de Soja SP", "cepea_sp", "Cepea (SP)", "Referência física para o mercado doméstico brasileiro."),
        ("Argentina FOB (Rosario)", "argentina_fob", "Rosario (BCR)", "Principal porto de exportação do complexo soja global."),
        ("Malásia Palma (Bursa)", "malaysia_palm", "Bursa Malaysia", "Principal óleo concorrente e benchmark de palma."),
        ("Dólar Comercial", "dolar", "USDBRL=X", "Define competitividade cambial e repasse industrial."),
        ("Petróleo Brent (ICE)", "petroleo_brent", "BZ=F", "Seta custos globais de frete, refino e biodiesel.")
    ]
    
    for label, key, ticker_symbol, reading in items_to_display:
        q = quotes.get(key)
        if q:
            price_str = q.get("price_str")
            if not price_str:
                price_val = q["price"]
                if key == "dolar":
                    price_str = f"R$ {price_val:.4f}"
                elif key == "soja_oleo":
                    price_str = f"{price_val:.2f} ¢/lb<br/>(USD {q['usd_ton']:.1f}/t)"
                else:
                    price_str = f"USD {price_val:.2f}"
            
            change_pct = q["pct_change"]
            date_str = q.get("date", "")
            
            if change_pct == 0.0 and (key == "cepea_sp" or key == "argentina_fob"):
                var_paragraph = Paragraph("<b>Estável</b>", table_cell_center)
            else:
                sign = "+" if change_pct >= 0 else ""
                color_text = GREEN_UP if change_pct >= 0 else RED_DOWN
                arrow = "▲" if change_pct >= 0 else "▼"
                var_paragraph = Paragraph(f"<font color='{color_text}'><b>{arrow} {sign}{change_pct:.2f}%</b></font>", table_cell_center)
            
            dynamic_trend = q.get("trend", "Estável")
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
    
    # 3. TAKEAWAYS
    story.append(Paragraph("DESTAQUES ESTRATÉGICOS", section_title_style))
    trend_oleo = quotes.get("soja_oleo", {}).get("trend", "Alta")
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
        
    takeaway_story = []
    for point in takeaway_points:
        takeaway_story.append(Paragraph(f"• {point}", body_style))
        takeaway_story.append(Spacer(1, 3))
    story.append(KeepTogether(takeaway_story))
    story.append(Spacer(1, 4))
    
    # 4. CENARIOS
    story.append(Paragraph("CENÁRIOS & PROJEÇÕES (PRÓXIMOS 15-30 DIAS)", section_title_style))
    scenarios_header = [
        Paragraph("Cenário", table_header_style),
        Paragraph("Probabilidade", table_header_style),
        Paragraph("Diretriz de Ação Comercial Sugerida", table_header_style)
    ]
    scenarios_rows = [
        scenarios_header,
        [
            Paragraph("<b>Cenário Base (Firme)</b><br/>ZL no canal de 73-78 ¢/lb.", table_cell_style),
            Paragraph("<b>55%</b>", table_cell_center),
            Paragraph("Defender margens contratuais, evitar posições curtas de estoque e focar no mix de valor agregado (margarinas especiais/ Sina Cheff).", table_cell_style)
        ],
        [
            Paragraph("<b>Cenário Altista (Pressão)</b><br/>Quebras nos EUA ou Brent acima de US$ 88.", table_cell_style),
            Paragraph("<b>30%</b>", table_cell_center),
            Paragraph("Disparar gatilhos rápidos de repasse de preço semanais e reduzir o prazo de cotações comerciais para no máximo 3 dias.", table_cell_style)
        ],
        [
            Paragraph("<b>Cenário de Correção</b><br/>Clima ideal nos EUA e esmagamento acelerado.", table_cell_style),
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
    
    # 5. RADAR NOTICIAS
    story.append(Paragraph("RADAR DE NOTÍCIAS DO SETOR", section_title_style))
    manual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'manual.json')
    manual_data = {}
    if os.path.exists(manual_path):
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                manual_data = json.load(f)
        except:
            pass
            
    headline = manual_data.get("headline_dia", {})
    headline_title = headline.get("title", "N/D")
    headline_summary = headline.get("summary", "N/D")
    
    news_box_content = [
        Paragraph(f"<b>Destaque do Dia: {headline_title}</b>", bold_body_style),
        Spacer(1, 2),
        Paragraph(headline_summary, body_style)
    ]
    
    news_table_data = [[ "", news_box_content ]]
    news_table = Table(news_table_data, colWidths=[4, 519])
    news_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor("#d4a373")),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor("#f8f9fa")),
        ('PADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (1,0), (1,0), 6),
        ('BOTTOMPADDING', (1,0), (1,0), 6),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (1,0), (1,0), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(news_table)
    story.append(Spacer(1, 4))
    
    # 6. ACTION TODAY
    story.append(Spacer(1, 2))
    action_box_content = [
        Paragraph("<b>ACTION TODAY | DIRETRIZ DE CAMPO PARA VENDAS:</b>", bold_body_style),
        Spacer(1, 2),
        Paragraph("1. Apresentar aos clientes de fritura o rendimento em ciclos de fritura em vez de preço por quilo.", body_style),
        Paragraph("2. Priorizar a venda cruzada de <b>Margarinas Especiais Sina Cheff (margem de 20,28%)</b> em padarias de alta rotação.", body_style),
        Paragraph("3. Monitorar: óleo CBOT sustentado acima de 75 c/lb e taxa cambial USD/BRL acima de R$ 5,05 como gatilho de reajuste automático.", body_style)
    ]
    action_table = Table([[action_box_content]], colWidths=[523])
    action_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), LIGHT_GREEN),
        ('BOX', (0,0), (0,0), 1, LEAF_GREEN),
        ('PADDING', (0,0), (0,0), 8),
        ('VALIGN', (0,0), (0,0), 'TOP'),
        ('TOPPADDING', (0,0), (0,0), 6),
        ('BOTTOMPADDING', (0,0), (0,0), 6),
    ]))
    story.append(action_table)
    
    # ------------------ PAGE BREAK ------------------
    story.append(PageBreak())
    
    # ------------------ PAGE 2 ------------------
    # HEADER BANNER PAGE 2
    header_data_p2 = [
        [
            Paragraph("Agrofoods · Inteligência de Mercado", title_style),
            Paragraph(f"<b>DATA-BASE:</b> {now_br.strftime('%d/%m/%Y')}", subtitle_style)
        ],
        [
            Paragraph("Mapeamento de Safra & Previsões 2026/2027", header_left_subtitle_style),
            Paragraph("<b>MÓDULO DE FONTES DE DADOS</b>", subtitle_style)
        ]
    ]
    header_table_p2 = Table(header_data_p2, colWidths=[330, 193])
    header_table_p2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_GREEN),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(header_table_p2)
    story.append(Spacer(1, 8))
    
    # Subtitle or explanation
    intro_p2 = Paragraph(
        "Este módulo especial mapeia a origem, frequência e acesso aos indicadores da safra "
        "de soja e projeções para o período 2026/2027, divididos entre séries diárias, safras mensais e climatologia.",
        body_style
    )
    story.append(intro_p2)
    story.append(Spacer(1, 6))
    
    # TABLE 1: DADOS DIÁRIOS
    story.append(Paragraph("1. Indicadores com Atualização Diária", section_title_style))
    t1_header = [
        Paragraph("Indicador", table_header_style),
        Paragraph("Fonte Oficial", table_header_style),
        Paragraph("Método de Acesso", table_header_style),
        Paragraph("Frequência", table_header_style)
    ]
    t1_rows = [
        t1_header,
        [
            Paragraph("<b>Óleo de Soja (CBOT, ZL)</b>", table_cell_bold),
            Paragraph("CME Group / Yahoo Finance", table_cell_style),
            Paragraph("Yahoo Finance API (Automático)", table_cell_style),
            Paragraph("Diário (Fechamento/Intraday)", table_cell_style)
        ],
        [
            Paragraph("<b>Energia (WTI/Brent)</b>", table_cell_bold),
            Paragraph("CME / ICE via Yahoo Finance", table_cell_style),
            Paragraph("Yahoo Finance API (Automático)", table_cell_style),
            Paragraph("Diário (Fechamento)", table_cell_style)
        ],
        [
            Paragraph("<b>Câmbio USD/BRL</b>", table_cell_bold),
            Paragraph("Frankfurter API / Banco Central", table_cell_style),
            Paragraph("Frankfurter API (Automático)", table_cell_style),
            Paragraph("Diário", table_cell_style)
        ],
        [
            Paragraph("<b>Soja Grão (ZS) & Farelo (ZM)</b>", table_cell_bold),
            Paragraph("CME Group / Yahoo Finance", table_cell_style),
            Paragraph("Yahoo Finance API (Automático)", table_cell_style),
            Paragraph("Diário (Fechamento)", table_cell_style)
        ]
    ]
    t1_table = Table(t1_rows, colWidths=[130, 130, 160, 103])
    t1_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LEAF_GREEN),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ccc")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(t1_table)
    story.append(Spacer(1, 8))
    
    # TABLE 2: DADOS DE SAFRA E CENÁRIOS 26/27
    story.append(Paragraph("2. Indicadores de Safra & Cenários 2026/2027", section_title_style))
    t2_header = [
        Paragraph("Dado de Safra", table_header_style),
        Paragraph("Fonte de Dados", table_header_style),
        Paragraph("Como Acessar / Integrar", table_header_style),
        Paragraph("Atualização", table_header_style)
    ]
    t2_rows = [
        t2_header,
        [
            Paragraph("<b>Produção Brasil/UFs</b>", table_cell_bold),
            Paragraph("CONAB (Safras)", table_cell_style),
            Paragraph("portaldeinformacoes.conab.gov.br (Planilhas XLS)", table_cell_style),
            Paragraph("Mensal (8 a 14/mês)", table_cell_style)
        ],
        [
            Paragraph("<b>Exportações Soja</b>", table_cell_bold),
            Paragraph("Secex/ComexStat (MDIC)", table_cell_style),
            Paragraph("API REST Pública ComexStat (Automático)", table_cell_style),
            Paragraph("Mensal (~dia 5)", table_cell_style)
        ],
        [
            Paragraph("<b>USDA WASDE Global</b>", table_cell_bold),
            Paragraph("USDA World Board", table_cell_style),
            Paragraph("FAS PSD Online (Export CSV/API)", table_cell_style),
            Paragraph("Mensal (2ª ou 3ª semana)", table_cell_style)
        ],
        [
            Paragraph("<b>Climatologia (ENSO)</b>", table_cell_bold),
            Paragraph("NOAA Climate Center", table_cell_style),
            Paragraph("cpc.ncep.noaa.gov (Boletim ENSO/API)", table_cell_style),
            Paragraph("Mensal (2ª quinta/mês)", table_cell_style)
        ]
    ]
    t2_table = Table(t2_rows, colWidths=[130, 130, 160, 103])
    t2_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), LEAF_GREEN),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ccc")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
    ]))
    story.append(t2_table)
    story.append(Spacer(1, 8))
    
    # 3. INTEGRAÇÃO E DIRETRIZES
    story.append(Paragraph("3. Recomendações e Diretrizes de Confiabilidade", section_title_style))
    guidelines_text = [
        "<b>Estrutura Híbrida:</b> Recomenda-se manter o Bloco Diário rodando automaticamente às 9:00 AM (CBOT, câmbio, brent), enquanto as seções de <b>Safra CONAB</b> e <b>Cenários 26/27</b> devem ser atualizadas mensalmente, de acordo com o calendário de divulgação das fontes primárias.",
        "<b>Garantia de Qualidade:</b> Fontes sem API estruturada (Conab, Embrapa, Aprosoja-MS) devem ser atualizadas via conferência manual ou scripts assistidos de leitura de PDF/XLS, evitando repassar erros de leitura direta para as planilhas comerciais.",
        "<b>Monitoramento Climático Crítico:</b> Durante os meses de plantio e desenvolvimento da safra sul-americana (setembro a dezembro), o acompanhamento dos boletins ENSO da NOAA e do WASDE/USDA deve ser intensificado para reajuste dinâmico dos cenários comerciais Altista e de Correção."
    ]
    
    guideline_story = []
    for g in guidelines_text:
        guideline_story.append(Paragraph(f"• {g}", body_style))
        guideline_story.append(Spacer(1, 3))
    story.append(KeepTogether(guideline_story))
    
    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Complete 2-page PDF generated successfully at: {dest_path}")
    return dest_path

if __name__ == '__main__':
    gerar_pdf_completo()
