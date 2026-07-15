# Workflow: Radar Soja Diário

Gatilho: cron diário às 7h (horário de São Paulo).

## Passo 1 — Dados automatizados
Execute no terminal: `node fetch-data.js`
Isso grava `data/auto.json` com: CBOT ZL (preço, variação do dia), USD/BRL, USD/MYR.

## Passo 2 — Dados via navegação (você, agente, faz isso)
Abra cada URL abaixo, localize o valor pedido, e registre em `data/manual.json`
no mesmo formato de `data/manual.example.json`:

1. https://www.cepea.org.br/br/categoria/soja-cepea.aspx
   → valor mais recente de "óleo de soja bruto/degomado, SP" em R$/tonelada
   → data do dado

2. https://www.bcr.com.ar/es/mercados/mercado-de-granos/cotizaciones/cotizaciones-locales/fobfas-argentina/precios-fobfas-132
   → preço FOB oficial ou FAS teórico de óleo de soja em US$/tonelada

3. https://www.bursamalaysia.com/trade/our_products_services/derivatives/commodity_derivatives/crude_palm_oil_futures
   (se a página não tiver preço ao vivo, busque "Bursa Malaysia palm oil futures
   price today" e use a fonte mais recente entre Business Recorder, Reuters,
   Palm Oil Magazine ou Trading Economics)
   → contrato mais líquido (3º mês em diante), RM/tonelada, variação do dia

4. Busque "soybean oil biodiesel RFS OR B15 OR B16 OR retenciones OR B40 OR B50"
   restringindo a notícias das últimas 24h
   → uma manchete + 1 frase de resumo, a que for mais relevante para o dia

Se qualquer item não for encontrado com confiança em até 3 tentativas de busca,
grave `"N/D"` — nunca estime ou invente um número.

## Passo 3 — Montar e enviar
Execute: `node send-email.js`
Isso lê `data/auto.json` + `data/manual.json`, monta o HTML do e-mail e envia
via SMTP para o endereço definido em `.env` (`RECIPIENT_EMAIL`).

## Passo 4 — Registrar
Anexe uma cópia do e-mail enviado em `data/historico/AAAA-MM-DD.json` para
começar a formar uma série histórica própria — depois de ~60 dias já dá para
calcular correlação estatística real com esses dados.
