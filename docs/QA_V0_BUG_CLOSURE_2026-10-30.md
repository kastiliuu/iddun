# IDDUN — Fechamento QA dos 17 registros (30/10/2026)

Baseline GitHub main: `0a0966f36f235bce6a2a2b04a012e25ef97672de` (PR #204). Fontes: Notion páginas 99, 06, 08, 79, 96 e 97. **Uma PR mergeada não significa homologação.**

| ID | Evidência de código/PR | Status prudente |
|---|---|---|
| BUG-001 | #181 crop; #198 modalidade | Integrado; QA manual pendente |
| BUG-002 | #197 padronização de erros, sem prova do formulário específico | Reproduzir e verificar perda de dados |
| BUG-003 | #183 Voltar/layout | Integrado; QA manual pendente |
| BUG-004 | Menções e vínculos; Notion 08 | Dependente de decisão |
| BUG-005 | #199 retorno à seção | Integrado; QA manual pendente |
| BUG-006 | Galeria repetida não reproduzida | Investigar dados; melhoria separada |
| BUG-007 | Paleta do perfil público | Auditoria visual pendente |
| BUG-008 | Paleta/galeria Business | Auditoria visual pendente |
| BUG-009 | Como chegar em Business | Melhoria e privacidade pendentes |
| BUG-010 | Destaque em diretório Pro | Revisão visual pendente |
| BUG-011 | Navegação global | NAV-01 aguarda aprovação |
| BUG-012 | Hero do Explorar | Revisão visual pendente |
| BUG-013 | #202 link Esqueci minha senha | Integrado; QA manual pendente |
| BUG-014 | #183 e #201 contraste | Integrado; QA manual pendente |
| BUG-015 | #182 onboarding Business | Integrado; QA manual pendente |
| BUG-016 | #181 CSP do crop | Integrado; QA manual pendente |
| BUG-017 | #182 e #197 mensagens Web | Integrado; QA manual pendente |

## Gate de encerramento
Registrar para cada caso: SHA, ambiente, URL/tela, passos, esperado, observado, screenshot/log sem dados pessoais, resultado Web/Mobile e teste automatizado. Só classificar corrigido após regressão verde + evidência de QA; não abrir regressão só por leitura de PR.

Roteiro: (1) Pro: foto/crop, modalidade multi-select, erro em experiência profissional sem perder conteúdo, exclusão de portfólio; (2) Business: envio antecipado, logo opcional, português, rascunho e legado; (3) login: tabulação, recuperação e mobile; (4) Explorar/Home: cards visíveis, busca, vitrine só real, ausência de dados, setas e teclado; (5) Mobile: paridade de fluxo, navegação e mensagens; (6) BOOK-STATE-01: **não reproduzido**, verificar fuso/slot/cutoff/publicação antes de qualquer plano de alteração sensível.

Comandos sugeridos (não executados nesta PR):

```powershell
python -m pytest -q
python -m pytest tests/test_home.py tests/test_professional_dashboard.py tests/test_business_onboarding_wizard.py -q
cd mobile
npm ci
npx expo install --check
npm run typecheck
npm run lint
npm audit --omit=dev --json > npm-audit-production.json
node scripts/check-npm-advisory-baseline.cjs npm-audit-production.json
```

Playwright: seguir `docs/QA_PLAYWRIGHT_WEB.md` com base descartável. A auditoria npm pode retornar código não-zero pelos riscos conhecidos; verificar o gate de novos advisories.

**Provas desta PR:** main e PRs consultadas; suíte pytest, Playwright, tsc, lint, DS e QA manual **NÃO VERIFICADOS**. Nenhuma alteração funcional, migration, contrato, dependência ou autorização.
