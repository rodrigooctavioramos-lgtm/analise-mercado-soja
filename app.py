import os
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request
import pandas as pd
import yfinance as yf

app = Flask(__name__)

# Global cache for quotes to prevent yfinance rate limits
QUOTES_CACHE = {}
OIL_COMPARISON_CACHE = {}
WEEKLY_FORECAST_CACHE = {}
CACHE_LOCK = threading.Lock()
LAST_UPDATE = None

# Tickers to track
TICKERS = {
    "soja_grao": "ZS=F",        # CBOT Soybean Futures (cents/bushel)
    "soja_oleo": "ZL=F",        # CBOT Soybean Oil Futures (cents/lb)
    "soja_farelo": "ZM=F",      # CBOT Soybean Meal Futures (USD/short ton)
    "dolar": "USDBRL=X",        # USD/BRL Currency Rate
    "soja3_b3": "SOJA3.SA",     # Boa Safra Sementes Stock B3 (R$)
    "palma_oleo": "CPO=F",      # Bursa Malaysia Palm Oil Futures (MYR/ton)
    "algodao_oleo": "CT=F",     # ICE Cotton Futures (cents/lb) - Cottonseed oil proxy
    "usdmyr": "USDMYR=X"        # USD/MYR exchange rate
}

def atualizar_cotacoes():
    """Updates Yahoo Finance quotes and saves to cache."""
    global QUOTES_CACHE, OIL_COMPARISON_CACHE, WEEKLY_FORECAST_CACHE, LAST_UPDATE
    print("Atualizando cotações do Yahoo Finance...")
    novas_cotacoes = {}
    
    # 1. Fetch individual quote data
    for key, ticker_symbol in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch last 5 days history to get close and change
            hist = ticker.history(period="5d")
            if not hist.empty:
                last_row = hist.iloc[-1]
                prev_row = hist.iloc[-2] if len(hist) > 1 else last_row
                
                close_val = float(last_row["Close"])
                prev_close = float(prev_row["Close"])
                change = close_val - prev_close
                pct_change = (change / prev_close * 100) if prev_close != 0 else 0
                
                # Fetch 6 months history for charts
                hist_6m = ticker.history(period="6mo")
                series_data = []
                for dt, row in hist_6m.iterrows():
                    series_data.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "value": float(row["Close"])
                    })
                
                novas_cotacoes[key] = {
                    "symbol": ticker_symbol,
                    "price": close_val,
                    "change": change,
                    "pct_change": pct_change,
                    "prev_close": prev_close,
                    "high": float(last_row["High"]),
                    "low": float(last_row["Low"]),
                    "volume": float(last_row["Volume"]),
                    "history_6m": series_data
                }
            else:
                print(f"Histórico vazio para o ticker {ticker_symbol}")
        except Exception as e:
            print(f"Erro ao buscar ticker {ticker_symbol}: {e}")
            
    # 2. Perform Calculations & Align Historical series for Vegetable Oil Comparison (USD/ton)
    try:
        # Check if we have the needed series
        if "soja_oleo" in novas_cotacoes and "palma_oleo" in novas_cotacoes and "algodao_oleo" in novas_cotacoes and "usdmyr" in novas_cotacoes:
            df_soja = pd.DataFrame(novas_cotacoes["soja_oleo"]["history_6m"])
            df_palma = pd.DataFrame(novas_cotacoes["palma_oleo"]["history_6m"])
            df_cotton = pd.DataFrame(novas_cotacoes["algodao_oleo"]["history_6m"])
            df_myr = pd.DataFrame(novas_cotacoes["usdmyr"]["history_6m"])
            
            # Set index to date
            df_soja.set_index("date", inplace=True)
            df_palma.set_index("date", inplace=True)
            df_cotton.set_index("date", inplace=True)
            df_myr.set_index("date", inplace=True)
            
            # Rename columns
            df_soja.rename(columns={"value": "soja_cents_lb"}, inplace=True)
            df_palma.rename(columns={"value": "palma_myr_ton"}, inplace=True)
            df_cotton.rename(columns={"value": "cotton_cents_lb"}, inplace=True)
            df_myr.rename(columns={"value": "usdmyr"}, inplace=True)
            
            # Merge
            df_merged = df_soja.join([df_palma, df_cotton, df_myr], how="inner")
            
            # Convert units to USD / Metric Ton
            # 1 lb = 0.453592 kg -> 1 ton = 2204.62 lbs
            # Soybean Oil is in cents/lb. USD/ton = (cents/100) * 2204.62 = price * 22.0462
            df_merged["soja_usd_ton"] = df_merged["soja_cents_lb"] * 22.0462
            
            # Cotton Oil is in cents/lb. USD/ton = (cents/100) * 2204.62 = price * 22.0462
            df_merged["algodao_usd_ton"] = df_merged["cotton_cents_lb"] * 22.0462
            
            # Palm Oil is in MYR/ton. USD/ton = MYR / usdmyr
            df_merged["palma_usd_ton"] = df_merged["palma_myr_ton"] / df_merged["usdmyr"]
            
            # Format comparison list
            comp_series = []
            for dt, row in df_merged.iterrows():
                comp_series.append({
                    "date": dt,
                    "soja": float(row["soja_usd_ton"]),
                    "palma": float(row["palma_usd_ton"]),
                    "algodao": float(row["algodao_usd_ton"])
                })
                
            CACHE_LOCK.acquire()
            try:
                OIL_COMPARISON_CACHE["series"] = comp_series
                # Current values in USD/ton
                OIL_COMPARISON_CACHE["current"] = {
                    "soja": float(df_merged["soja_usd_ton"].iloc[-1]) if not df_merged.empty else 0,
                    "palma": float(df_merged["palma_usd_ton"].iloc[-1]) if not df_merged.empty else 0,
                    "algodao": float(df_merged["algodao_usd_ton"].iloc[-1]) if not df_merged.empty else 0
                }
            finally:
                CACHE_LOCK.release()
    except Exception as e:
        print(f"Erro ao calcular comparação de óleos: {e}")

    # 3. Calculate weekly technical forecast (based on SOYBEAN OIL trend)
    try:
        if "soja_oleo" in novas_cotacoes and "dolar" in novas_cotacoes:
            hist_oleo = novas_cotacoes["soja_oleo"]["history_6m"]
            last_price = novas_cotacoes["soja_oleo"]["price"]
            
            # Calculate 5-day SMA for Soybean Oil
            if len(hist_oleo) >= 5:
                closes_5d = [h["value"] for h in hist_oleo[-5:]]
                sma_5d = sum(closes_5d) / 5
            else:
                sma_5d = last_price
                
            momentum = (last_price - sma_5d) / sma_5d * 100
            
            # Simple technical rule for Soybean Oil
            if last_price > sma_5d:
                direction = "Alta"
                probability = min(max(50 + momentum * 15, 55), 88)
                range_min = last_price * 0.985
                range_max = last_price * 1.025
                commentary = "Mercado de óleo de soja demonstrando viés de alta na CBOT. O preço do óleo opera acima da média móvel curta, impulsionado pela forte demanda da indústria de biodiesel nacional e americana e a alta nos preços de energia (petróleo)."
            else:
                direction = "Baixa"
                probability = min(max(50 - momentum * 15, 55), 88)
                range_min = last_price * 0.975
                range_max = last_price * 1.015
                commentary = "Mercado de óleo de soja sob pressão técnica na CBOT. O fechamento recente abaixo da média móvel de 5 dias é pressionado pelo ritmo forte de esmagamento nos EUA e pela ampla oferta da colheita sul-americana."
                
            # Convert targets to USD / Tonelada
            usd_ton_min = range_min * 22.0462
            usd_ton_max = range_max * 22.0462
            
            CACHE_LOCK.acquire()
            try:
                WEEKLY_FORECAST_CACHE.update({
                    "direction": direction,
                    "probability": round(probability, 1),
                    "cbot_oil_range_min": round(range_min, 2),
                    "cbot_oil_range_max": round(range_max, 2),
                    "usd_ton_range_min": round(usd_ton_min, 2),
                    "usd_ton_range_max": round(usd_ton_max, 2),
                    "commentary": commentary,
                    "last_oleo": last_price,
                    "calculated_at": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
            finally:
                CACHE_LOCK.release()
    except Exception as e:
        print(f"Erro ao calcular previsão semanal: {e}")

    # 4. Save to cache
    if novas_cotacoes:
        CACHE_LOCK.acquire()
        try:
            # Inject calculated B3 Soybean pricing
            # B3 Soybean = ((CBOT Soybean + 80 cents Premium) / 100) * 2.20462 * USD/BRL
            if "soja_grao" in novas_cotacoes and "dolar" in novas_cotacoes:
                cbot_price = novas_cotacoes["soja_grao"]["price"]
                usd_brl = novas_cotacoes["dolar"]["price"]
                b3_calc_bag_usd = (cbot_price + 80.0) / 100.0 * 2.20462
                b3_calc_bag_brl = b3_calc_bag_usd * usd_brl
                
                # Mock high/low/change for calculated B3 Soybean
                cbot_change = novas_cotacoes["soja_grao"]["change"]
                b3_change_brl = (cbot_change / 100.0) * 2.20462 * usd_brl
                
                novas_cotacoes["soja_b3_calculada"] = {
                    "symbol": "SJC_CALC",
                    "price": b3_calc_bag_brl,
                    "change": b3_change_brl,
                    "pct_change": novas_cotacoes["soja_grao"]["pct_change"],
                    "prev_close": b3_calc_bag_brl - b3_change_brl,
                    "high": b3_calc_bag_brl * 1.01,
                    "low": b3_calc_bag_brl * 0.99,
                    "volume": 12450.0,
                    "history_6m": [{"date": h["date"], "value": ((h["value"] + 80) / 100 * 2.20462 * usd_brl)} for h in novas_cotacoes["soja_grao"]["history_6m"]]
                }
                
            QUOTES_CACHE.update(novas_cotacoes)
            LAST_UPDATE = datetime.now()
        finally:
            CACHE_LOCK.release()

def start_background_updater():
    """Starts a daemon thread to update quotes every 15 seconds (shortest safe interval)."""
    def run_updater():
        try:
            atualizar_cotacoes()
        except Exception as e:
            print(f"Erro no updater de background inicial: {e}")
            
        while True:
            time.sleep(15)
            try:
                atualizar_cotacoes()
            except Exception as e:
                print(f"Erro no updater de background: {e}")
            
    updater_thread = threading.Thread(target=run_updater, daemon=True)
    updater_thread.start()

# Historical Database & SECEX YTD/Projections
HISTORICAL_DATA = {
    "safra": {
        "anos": ["2020/21", "2021/22", "2022/23", "2023/24", "2024/25", "2025/26 (Proj)"],
        "brasil_prod": [139.3, 125.5, 154.6, 147.7, 161.0, 168.0], # Milhões de toneladas
        "eua_prod": [114.7, 121.5, 116.2, 113.3, 124.8, 127.0],
        "argentina_prod": [46.2, 43.9, 25.0, 50.0, 51.0, 53.0]
    },
    "exportacoes": {
        "anos": ["2021", "2022", "2023", "2024", "2025", "2026 (YTD)"],
        "soja_grao": [86.1, 78.7, 101.8, 95.8, 103.2, 42.5], # Milhões de toneladas
        "soja_oleo": [1.65, 2.60, 2.33, 1.45, 1.82, 0.68],   # Milhões de toneladas
        "detalhes": {
            "soja_grao": {
                "ano_anterior_total": 103.2,
                "ano_anterior_ytd": 40.8,
                "ano_corrente_ytd": 42.5,
                "ano_corrente_projecao": 106.8,
                "ytd_variacao": 4.17,
                "total_variacao": 3.49
            },
            "soja_oleo": {
                "ano_anterior_total": 1.82,
                "ano_anterior_ytd": 0.62,
                "ano_corrente_ytd": 0.68,
                "ano_corrente_projecao": 1.94,
                "ytd_variacao": 9.68,
                "total_variacao": 6.59
            }
        }
    }
}

# Current Industry News database
NEWS_DATABASE = [
    {
        "id": 1,
        "titulo": "Produção de Biodiesel no Brasil atinge recorde histórico no acumulado de 2026",
        "fonte": "SCA Brasil / Notícias Agrícolas",
        "data": "08/06/2026",
        "categoria": "BIODIESEL",
        "resumo": "A produção brasileira de biodiesel registrou o maior volume histórico para o primeiro quadrimestre do ano, atingindo 3,25 milhões de m³ (+9,87% em relação a 2025). O óleo de soja consolida-se como a principal matéria-prima, ampliando sua participação na matriz nacional para 75,6%."
    },
    {
        "id": 2,
        "titulo": "Vazio sanitário da soja inicia em Mato Grosso visando a proteção da safra 2026/27",
        "fonte": "Canal Rural",
        "data": "05/06/2026",
        "categoria": "CLIMA & SAFRA",
        "resumo": "O vazio sanitário de 90 dias teve início no estado de Mato Grosso. A medida, que proíbe manter plantas vivas de soja nas lavouras, é crucial para prevenir a multiplicação do fungo da ferrugem asiática durante o ciclo de entressafra e preparar as lavouras para o plantio em setembro."
    },
    {
        "id": 3,
        "titulo": "Oscilação cambial e prêmios nos portos sustentam o preço físico da soja no Brasil",
        "fonte": "Globo Rural",
        "data": "09/06/2026",
        "categoria": "MERCADO FÍSICO",
        "resumo": "Apesar do clima favorável apontar para uma grande colheita nos EUA e pressionar a bolsa de Chicago (CME), a alta pontual do dólar frente ao real e os prêmios portuários positivos têm atuado como forte colchão de proteção para o mercado físico nacional de soja."
    },
    {
        "id": 4,
        "titulo": "Indonésia adota restrições nas exportações de óleo de palma para priorizar mercado interno de B50",
        "fonte": "Bloomberg Linea",
        "data": "07/06/2026",
        "categoria": "ÓLEOS VEGETAIS",
        "resumo": "O maior exportador global de óleo de palma centralizou a fiscalização das remessas no exterior para assegurar estoques internos e dar suporte ao programa nacional de biocombustível B50. A restrição afeta os fluxos globais e redireciona importadores asiáticos (como a Índia) para o óleo de soja."
    },
    {
        "id": 5,
        "titulo": "Políticas ambientais americanas e lei do Combustível do Futuro abrem debate sobre esmagamento",
        "fonte": "Notícias Agrícolas",
        "data": "04/06/2026",
        "categoria": "TENDÊNCIAS",
        "resumo": "Investimentos bilionários na capacidade de esmagamento de soja nos EUA e a tramitação final da regulação da lei 'Combustível do Futuro' no Brasil mantêm o setor otimista quanto à demanda estrutural de óleo de soja de longo prazo, transformando a oleaginosa em commodity energética."
    },
    {
        "id": 6,
        "titulo": "Mercado Global de Petróleo: Oscilação do Brent e reflexos no complexo de soja e biocombustíveis",
        "fonte": "Reuters / Bloomberg",
        "data": "10/06/2026",
        "categoria": "ENERGIA",
        "resumo": "A firmeza dos preços da energia (Brent e WTI) devido a tensões geopolíticas globais e cortes de oferta da OPEP+ continua a sustentar as margens de biodiesel nos EUA e na Europa, impulsionando a demanda industrial e as cotações de óleo de soja na CBOT."
    }
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/quotes")
def get_quotes():
    global QUOTES_CACHE, LAST_UPDATE
    
    # Trigger instant update if cache is empty
    if not QUOTES_CACHE:
        atualizar_cotacoes()
        
    CACHE_LOCK.acquire()
    try:
        data = {
            "last_update": LAST_UPDATE.strftime("%d/%m/%Y %H:%M:%S") if LAST_UPDATE else None,
            "quotes": QUOTES_CACHE
        }
    finally:
        CACHE_LOCK.release()
        
    return jsonify(data)

@app.route("/api/oil-comparison")
def get_oil_comparison():
    global OIL_COMPARISON_CACHE
    if not OIL_COMPARISON_CACHE:
        atualizar_cotacoes()
    return jsonify(OIL_COMPARISON_CACHE)

@app.route("/api/forecast")
def get_forecast():
    global WEEKLY_FORECAST_CACHE
    if not WEEKLY_FORECAST_CACHE:
        atualizar_cotacoes()
    return jsonify(WEEKLY_FORECAST_CACHE)

@app.route("/api/news")
def get_news():
    return jsonify(NEWS_DATABASE)

@app.route("/api/crops")
def get_crops():
    return jsonify(HISTORICAL_DATA["safra"])

@app.route("/api/exports")
def get_exports():
    return jsonify(HISTORICAL_DATA["exportacoes"])

@app.route("/api/reload")
def force_reload():
    atualizar_cotacoes()
    return jsonify({"status": "sucesso", "mensagem": "Cotações recarregadas sob demanda."})

@app.route("/api/diario-pdf")
def download_diario():
    """Route to generate and download the daily Soybean Market Intelligence PDF."""
    from gerar_pdf_soja import gerar_pdf_diario
    from flask import send_file
    
    # Path of the generated PDF
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados', 'relatorios', 'diario_soja.pdf')
    
    try:
        # Generate fresh PDF
        gerar_pdf_diario(pdf_path)
        
        if os.path.exists(pdf_path):
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"AGROFOODS_DAILY_MARKET_INTELLIGENCE_{datetime.now().strftime('%Y-%m-%d')}.pdf"
            )
        else:
            return jsonify({"erro": "O arquivo PDF não pôde ser gerado."}), 500
    except Exception as e:
        return jsonify({"erro": f"Erro interno ao gerar o PDF: {str(e)}"}), 500

@app.route("/api/enviar-diario")
def trigger_enviar_diario():
    """Manual trigger to execute the daily mailing/mock mailing workflow."""
    from agendador_diario_soja import executar_agendamento_diario
    try:
        executar_agendamento_diario()
        return jsonify({"status": "sucesso", "mensagem": "Automação diária executada com sucesso!"})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

def start_background_pdf_scheduler():
    """Starts a thread to check and run the daily report mailing at 08:00 AM."""
    from agendador_diario_soja import executar_agendamento_diario
    
    def pdf_scheduler_loop():
        # Wait for yfinance cache to populate first
        time.sleep(10)
        ja_enviado_hoje = False
        print("Iniciando agendador diário de mercado de Soja (08:00 AM)...")
        
        while True:
            agora = datetime.now()
            hora_atual = agora.strftime("%H:%M")
            
            if hora_atual == "08:00" and not ja_enviado_hoje:
                try:
                    executar_agendamento_diario()
                except Exception as e:
                    print(f"Erro no agendador de background do PDF: {e}")
                ja_enviado_hoje = True
            elif hora_atual != "08:00":
                ja_enviado_hoje = False
                
            time.sleep(30) # check every 30 seconds
            
    scheduler_thread = threading.Thread(target=pdf_scheduler_loop, daemon=True)
    scheduler_thread.start()

if __name__ == "__main__":
    # Ensure folder relatórios exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "dados", "relatorios"), exist_ok=True)
    # Start background updater
    start_background_updater()
    # Start background PDF scheduler
    start_background_pdf_scheduler()
    # Start app on port 5006
    app.run(host="0.0.0.0", port=5006, debug=True)

