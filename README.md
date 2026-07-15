# Radar Óleo de Soja — Antigravity

Script pronto para rodar no seu Antigravity, com envio diário por e-mail via
Gmail (senha de app). Sem depender de Claude Cowork nem de nenhum conector.

## Checklist de instalação (10-15 min)

- [ ] **1.** Copie a pasta inteira `radar-soja-antigravity/` para dentro de um
      projeto no Antigravity
- [ ] **2.** No terminal do Antigravity: `npm install`
- [ ] **3.** Ative a verificação em 2 etapas na sua conta Gmail (se ainda não
      tiver): myaccount.google.com/security
- [ ] **4.** Gere uma senha de app em myaccount.google.com/apppasswords
      → escolha "Outro (nome personalizado)" → nomeie "Radar Soja Antigravity"
      → copie os 16 dígitos gerados
- [ ] **5.** Copie `.env.example` para `.env` e preencha:
      - `SMTP_USER` = seu e-mail do Gmail
      - `SMTP_PASS` = a senha de app de 16 dígitos (sem espaços)
      - `RECIPIENT_EMAIL` = para onde o radar deve chegar (pode ser o próprio
        Gmail ou seu e-mail agrofoods.com.br — Gmail entrega em qualquer caixa)
- [ ] **6.** Teste manualmente: `npm run fetch` e depois `npm run send`
      → confira se o e-mail chegou
- [ ] **7.** No Agent Manager do Antigravity, abra `workflow.md` e peça ao
      agente: *"crie um Workflow chamado 'Radar Soja Diário' a partir deste
      arquivo, com agendamento cron todo dia às 7h (horário de São Paulo)"*
- [ ] **8.** Confirme o agendamento e deixe rodando por 3-4 dias observando
      se os dados extraídos (Cepea, Rosario, Malásia) batem com a fonte —
      esses três não têm API, dependem do agente ler a página corretamente

## Comandos disponíveis

```bash
npm run fetch    # busca CBOT ZL + câmbio (API pública, automático)
npm run send     # monta e envia o e-mail com os dados disponíveis em data/
npm run run-radar  # roda os dois em sequência
```

## Estrutura

```
radar-soja-antigravity/
├── fetch-data.js          # CBOT ZL + câmbio — 100% automatizado
├── send-email.js          # monta o HTML e envia via Gmail SMTP
├── workflow.md            # instrução para o agente completar os dados sem API
├── package.json
├── .env.example           # copie para .env e preencha
└── data/
    └── manual.example.json  # modelo do que o agente deve preencher em manual.json
```

## O que é automático vs. o que o agente precisa ler

| Dado | Fonte | Como |
|---|---|---|
| CBOT ZL (Chicago) | Yahoo Finance (API pública) | `fetch-data.js`, automático |
| USD/BRL, USD/MYR | Frankfurter API (BCE, sem chave) | `fetch-data.js`, automático |
| Cepea/Esalq (Brasil) | cepea.org.br | agente navega e extrai (`workflow.md`) |
| Rosario/BCR (Argentina) | bcr.com.ar | agente navega e extrai (`workflow.md`) |
| Bursa Malaysia (palma) | bursamalaysia.com / notícias | agente navega e extrai (`workflow.md`) |
| Manchete do dia | busca por termos de biodiesel/mandatos | agente pesquisa (`workflow.md`) |

Se em algum momento você tiver acesso a uma API paga para Cepea/BCR/Bursa
(Bloomberg, Refinitiv, ou uma assinatura direta), me chama — troco a extração
por chamada de API real, o que deixa o dado auditável e elimina qualquer
variação de leitura do agente.

## Testado

O `fetch-data.js` foi validado por mim (Claude) — a lógica está correta e
grava `data/auto.json` do jeito certo. Não consegui validar a resposta real
das APIs no meu ambiente porque meu sandbox bloqueia domínios fora de uma
lista fixa (Yahoo Finance e Frankfurter não estão nela) — mas são endpoints
públicos estáveis e amplamente usados, então no Antigravity, sem essa
restrição, devem responder normalmente. Se algo der erro no passo 6 acima, me
mande a mensagem de erro que eu ajusto.
