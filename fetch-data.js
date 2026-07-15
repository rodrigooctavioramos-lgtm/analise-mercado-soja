// fetch-data.js
// Busca os dados que têm fonte pública, gratuita e estável.
// CBOT Soybean Oil (ZL=F) via endpoint público do Yahoo Finance.
// Câmbio via Frankfurter API (Banco Central Europeu, sem chave necessária).

const fs = require('fs');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'data');
const OUT_FILE = path.join(OUT_DIR, 'auto.json');

async function fetchJSON(url) {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (radar-soja-agrofoods/1.0)' }
  });
  if (!res.ok) throw new Error(`Falha ao buscar ${url}: HTTP ${res.status}`);
  return res.json();
}

async function fetchCbotSoyOil() {
  const url = 'https://query1.finance.yahoo.com/v8/finance/chart/ZL=F?interval=1d&range=5d';
  const json = await fetchJSON(url);
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error('Formato inesperado na resposta do Yahoo Finance');

  const meta = result.meta;
  const price = meta.regularMarketPrice;
  const prevClose = meta.previousClose ?? meta.chartPreviousClose;
  const change = price - prevClose;
  const changePct = (change / prevClose) * 100;

  return {
    symbol: 'ZL=F',
    label: 'CBOT Óleo de Soja',
    price_cents_lb: Number(price.toFixed(2)),
    change_abs: Number(change.toFixed(2)),
    change_pct: Number(changePct.toFixed(2)),
    as_of: new Date(meta.regularMarketTime * 1000).toISOString(),
    source: 'Yahoo Finance (query1.finance.yahoo.com)'
  };
}

async function fetchFX() {
  const url = 'https://api.frankfurter.dev/v1/latest?base=USD&symbols=BRL,MYR,ARS';
  const json = await fetchJSON(url);
  return {
    base: 'USD',
    rates: json.rates,
    date: json.date,
    source: 'Frankfurter API (frankfurter.dev)'
  };
}

async function main() {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

  const result = {
    generated_at: new Date().toISOString(),
    cbot_soy_oil: null,
    fx: null,
    errors: []
  };

  try {
    result.cbot_soy_oil = await fetchCbotSoyOil();
  } catch (err) {
    result.errors.push(`CBOT: ${err.message}`);
  }

  try {
    result.fx = await fetchFX();
  } catch (err) {
    result.errors.push(`FX: ${err.message}`);
  }
  // Nota: ARS via Frankfurter costuma ser o câmbio oficial, não o paralelo/MEP
  // usado no agro argentino — trate como referência, não como FX operacional.

  fs.writeFileSync(OUT_FILE, JSON.stringify(result, null, 2), 'utf-8');
  console.log(`Gravado em ${OUT_FILE}`);
  if (result.errors.length) {
    console.warn('Atenção, houve falhas parciais:', result.errors);
  }
}

main().catch(err => {
  console.error('Falha geral em fetch-data.js:', err);
  process.exit(1);
});
