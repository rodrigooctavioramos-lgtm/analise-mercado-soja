// send-email.js
// Lê data/auto.json + data/manual.json, monta o e-mail HTML e envia via SMTP.
// Requer: npm install nodemailer dotenv

require('dotenv').config();
const fs = require('fs');
const path = require('path');
const nodemailer = require('nodemailer');

const DATA_DIR = path.join(__dirname, 'data');

function readJSON(file, fallback = {}) {
  const p = path.join(DATA_DIR, file);
  if (!fs.existsSync(p)) return fallback;
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

function fmtSign(n) {
  if (n === undefined || n === null || isNaN(n)) return 'N/D';
  return (n > 0 ? '+' : '') + n;
}

function buildHtml(auto, manual) {
  const zl = auto.cbot_soy_oil;
  const fx = auto.fx;
  const today = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });

  const zlBlock = zl
    ? `<div class="card">
         <div class="label">CBOT Óleo de Soja (ZL)</div>
         <div class="value">${zl.price_cents_lb} ¢/lb</div>
         <div class="delta ${zl.change_abs >= 0 ? 'up' : 'down'}">${zl.change_abs >= 0 ? '▲' : '▼'} ${fmtSign(zl.change_pct)}%</div>
       </div>`
    : `<div class="card"><div class="label">CBOT Óleo de Soja (ZL)</div><div class="value">N/D</div></div>`;

  const fxLine = fx
    ? `USD/BRL ${fx.rates.BRL ?? 'N/D'} · USD/MYR ${fx.rates.MYR ?? 'N/D'}`
    : 'Câmbio indisponível';

  const cepea = manual.cepea_brasil || {};
  const arg = manual.argentina_fob || {};
  const palm = manual.malaysia_palm || {};
  const headline = manual.headline_dia || {};

  return `
  <html><body style="font-family:Calibri,Arial,sans-serif;background:#F7F5F0;padding:24px;color:#1B1B18;">
    <div style="max-width:640px;margin:0 auto;background:#FCFBF8;border:1px solid #DDD8CC;">
      <div style="background:#122A1B;color:#F7F5F0;padding:18px 24px;border-bottom:3px solid #F28C28;">
        <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#F28C28;">Agrofoods · Radar Diário</div>
        <div style="font-family:Cambria,Georgia,serif;font-size:22px;">Óleo de Soja Global — ${today}</div>
      </div>
      <div style="padding:24px;">
        <table width="100%" style="border-collapse:collapse;margin-bottom:20px;">
          <tr>
            <td style="padding:12px;border:1px solid #DDD8CC;">
              <div style="font-size:11px;color:#4A4A44;text-transform:uppercase;">Chicago (ZL)</div>
              <div style="font-family:Consolas,monospace;font-size:20px;font-weight:bold;">${zl ? zl.price_cents_lb + ' ¢/lb' : 'N/D'}</div>
              <div style="font-size:12px;color:${zl && zl.change_abs >= 0 ? '#1F5C3A' : '#9C4221'};">${zl ? (zl.change_abs >= 0 ? '▲' : '▼') + ' ' + fmtSign(zl.change_pct) + '%' : ''}</div>
            </td>
            <td style="padding:12px;border:1px solid #DDD8CC;">
              <div style="font-size:11px;color:#4A4A44;text-transform:uppercase;">Brasil (Cepea)</div>
              <div style="font-family:Consolas,monospace;font-size:20px;font-weight:bold;">${cepea.value || 'N/D'}</div>
              <div style="font-size:12px;color:#4A4A44;">${cepea.as_of || ''}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:12px;border:1px solid #DDD8CC;">
              <div style="font-size:11px;color:#4A4A44;text-transform:uppercase;">Argentina (FOB/FAS)</div>
              <div style="font-family:Consolas,monospace;font-size:20px;font-weight:bold;">${arg.value || 'N/D'}</div>
              <div style="font-size:12px;color:#4A4A44;">${arg.as_of || ''}</div>
            </td>
            <td style="padding:12px;border:1px solid #DDD8CC;">
              <div style="font-size:11px;color:#4A4A44;text-transform:uppercase;">Malásia (Bursa — Palma)</div>
              <div style="font-family:Consolas,monospace;font-size:20px;font-weight:bold;">${palm.value || 'N/D'}</div>
              <div style="font-size:12px;color:#4A4A44;">${palm.change || ''} ${palm.as_of || ''}</div>
            </td>
          </tr>
        </table>

        <div style="font-size:12px;color:#8A8272;margin-bottom:18px;">${fxLine}</div>

        <div style="border-top:1px solid #DDD8CC;padding-top:16px;">
          <div style="font-size:11px;text-transform:uppercase;color:#E8891A;letter-spacing:1px;">Manchete do dia</div>
          <div style="font-weight:bold;margin:6px 0 4px;">${headline.title || 'N/D'}</div>
          <div style="font-size:13.5px;color:#4A4A44;">${headline.summary || ''}</div>
        </div>
      </div>
      <div style="padding:14px 24px;font-size:11px;color:#8A8272;border-top:1px solid #DDD8CC;">
        Gerado automaticamente. Fontes: Yahoo Finance, Frankfurter API, Cepea/Esalq, BCR, Bursa Malaysia.
      </div>
    </div>
  </body></html>`;
}

async function main() {
  const auto = readJSON('auto.json', {});
  const manual = readJSON('manual.json', readJSON('manual.example.json', {}));

  const html = buildHtml(auto, manual);

  const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT || 587),
    secure: false,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS
    }
  });

  const today = new Date().toLocaleDateString('pt-BR');

  await transporter.sendMail({
    from: process.env.SMTP_USER,
    to: process.env.RECIPIENT_EMAIL,
    subject: `Radar Óleo de Soja — ${today}`,
    html
  });

  console.log('E-mail enviado com sucesso.');
}

main().catch(err => {
  console.error('Falha ao enviar e-mail:', err);
  process.exit(1);
});
