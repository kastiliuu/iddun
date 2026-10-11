# IDDUN — Sprint QA-01: linha de base de qualidade

## Objetivo
Tornar o CI mais informativo e preparar gates de segurança sem interromper o desenvolvimento por alertas ainda não classificados.

## Cobertura Python
- Mantém os testes existentes e roda `pytest` com `pytest-cov`.
- Publica `coverage.xml` como artifact **iddun-backend-coverage**.
- Ainda não existe `fail-under`: o primeiro passo é medir a cobertura real, identificar áreas críticas descobertas e estabelecer limiares por acordo. Cobertura alta não garante regras corretas.

## Segurança Python
- `Bandit`: análise estática para achados de severidade/confiança média-alta, com relatório.
- `pip-audit`: consulta de vulnerabilidades conhecidas em dependências Python, com relatório JSON.
- O job de auditoria é **consultivo para achados** nesta fase: as etapas de scanner estão com `continue-on-error`. Uma falha de instalação da ferramenta ou publicação ainda poderá deixar o job vermelho.
- Os relatórios são publicados por 14 dias no artifact **iddun-security-baseline**.
- Achados devem ser triados em: explorável/P0-P1, falso positivo com justificativa, mitigação ou atualização de dependência. Não esconder alertas com exclusões genéricas.

## Próximas entregas de QA-01
1. Testes de isolamento entre organizações com usuário A versus gestor B, especialmente booking/CV/catálogo.
2. Teste de concorrência de booking com **PostgreSQL real** em CI (SQLite em memória não modela o mesmo comportamento transacional).
3. Gate de lint Python (Ruff) com baseline e escopo acordados.
4. Primeiro E2E Web Playwright de autenticação e agendamento, em ambiente descartável.
5. Testes dos fluxos Mobile conforme as telas sejam conectadas às APIs reais.
6. Depois da triagem, converter scanner security e limites de cobertura em bloqueios de PR, priorizando operações sensíveis.

## Critérios de aceite desta PR
- O CI continua executando pytest, Alembic, typecheck e lint mobile.
- `coverage.xml` aparece ao final de uma execução bem-sucedida.
- Bandit e pip-audit geram relatórios consultáveis, ou registram sua falha sem serem confundidos com aprovação de segurança.
- Nenhum modelo, API, template, migration ou permissão de produção foi alterado.
