# NV-07A1-WM-02B — Inventário de integração Business (30/10/2026)

Base GitHub `main@bcdc718d83fe3bc9c721b44ee58669afed273388`; nenhuma PR aberta na consulta. Fontes aprovadas: Notion 08 (DEC-ID-100–108, NV-07), 38 (FLOW-EST-001), 79 (paridade), 96 e 97. **Este documento é planejamento técnico, não afirma implementação nem QA manual.**

## Contratos comprovados

- #194 e #195 mergeadas: `app/routes/api_onboarding.py` serializa `operationMode`, `profileCompletion` e readiness; `app/services/mobile_onboarding_service.py` valida `operation_mode`, `business_hours_mode`, `business_hours`, endereço e `commercial_email` para rascunhos.
- O backend preserva valores opcionais não informados, permite rascunho incompleto e exige que publicação/legados permaneçam intactos; testes em `tests/test_api_onboarding.py`.
- `app/templates/platform/business-onboarding.html` não contém campos explícitos de modalidade, funcionamento e contato comercial (inspeção textual de 30/10). A montagem e escrita da Web, bem como as telas Expo correspondentes, precisam ser mapeadas antes do patch funcional.
- **Não interpretar** `profileCompletion` como publicação nem modificar o estado de estabelecimentos publicados historicamente.

## Próximo PR funcional: NV-07A1-WM-02B

1. Localizar o form/route Web do onboarding e a tela Expo concreta antes de mexer; registrar paths e handlers existentes.
2. Ligar somente os campos já definidos no contrato, reutilizando componentes/tokens; apresentar estados vazio, inválido, salvo, erro 401/403/409/422 e sessão expirada, e testes de preservação de valores.
3. Testar rascunho parcial, formulário inválido, proprietário autorizado, legado publicado e equivalência Web/Mobile.
4. Revisar diff, inventário de tokens e gate de acessibilidade. Sem mudanças em publicação efetiva, schema, reservas ou segurança.
5. Se a implementação não couber em ~8 arquivos / ~400 linhas de produção, separar em PRs Web e Expo vinculadas, sem declarar paridade antes de ambas.

## Critérios de pronto da V0 — estimativa de planejamento, não percentual auditado

**341 decisões documentadas:** 281 DEC-ID e 60 FE-DEC, ainda sem matriz linha a linha atualizada com evidências por plataforma. A contagem de decisões NÃO equivale a número de funcionalidades ou percentual concluído.

Trilhas restantes a verificar: (A) integridade e homologação booking/auth; (B) Business completo; (C) jornadas Cliente/Pro e social; (D) paridade Expo; (E) design system/navegação/acessibilidade; (F) moderação, segurança e infraestrutura; (G) QA end-to-end/release/piloto. CONV-01..13 é a fila de convergência, não 13 PRs restantes.

Faixa preliminar **15–30 PRs coesas**, condicionada ao inventário, mais homologação e correções surgidas nos testes. Não é compromisso de prazo nem taxa de progresso; o denominador real de aceites ainda não foi reconciliado. Meta para V0: nenhuma falha P0/P1 aberta, trilhas críticas testadas Web/Expo, regressões e CI verdes, documentação e piloto aprovados.

## Evidência e limites

- Consultados: GitHub main, PRs #182/#194/#195 e código dos três arquivos listados, Notion 08/79/96/97 e roadmap 81.
- **NÃO VERIFICADO**: baseline completo pytest, tsc, lint, E2E, DS e QA visual; não há checkout/ambiente de testes configurado aqui.
- Nenhuma regra de negócio ou arquivo funcional alterado nesta PR.
