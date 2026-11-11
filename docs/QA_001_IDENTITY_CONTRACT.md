# QA-001A — Contratos existentes da identidade única (V0)

**Status:** proteção de contrato por testes; **não implementa as mudanças de UX** da QA-001.

## Rastreabilidade

- [ClickUp QA-001](https://app.clickup.com/t/1dffe4j3dzj)
- Notion 08: QA-001-UX-01/02/03, ratificadas pelo proprietário em 10/11/2026.
- Notion 29: DEC-ID-064–072; 30: DEC-ID-073–080; 37: DEC-ID-092–099; 85: FE-DEC-021–030.
- `main` auditada: `89b487576c604563673f45c071a1a49349fc4543`.

## O que existe e não será recriado

| Contrato vigente | Evidência no código | Prova de regressão |
| --- | --- | --- |
| Uma conta com ClientProfile e ProfessionalProfile | `app/models/user.py` | `test_client_identity_remains_after_professional_activation` |
| O contexto Cliente vem primeiro mesmo com Pro ativo | `app/services/navigation_context.py` | `test_client_identity_remains_after_professional_activation` |
| Proprietário sem Pro conserva Cliente | `app/services/navigation_context.py`, `app/models/establishment.py` | `test_business_owner_without_pro_still_has_client_context` |
| Múltiplos estabelecimentos pertencem a contextos autorizados | `app/services/navigation_context.py` | `test_contexts_are_isolated_and_update_after_grant_revocation` |
| Grant empresarial revogado sai da lista sem nova sessão | `app/services/navigation_context.py` e `/api/v1/auth/me` | `test_contexts_are_isolated_and_update_after_grant_revocation` |
| API `/api/v1/auth/me` exige bearer; payload legacy `role` preservado | `app/routes/api_auth.py` | testes adicionais em `tests/test_navigation_contexts.py` e `tests/test_api_auth.py` |
| API expõe `contexts` no mesmo formato consumido pelo app | `app/routes/api_auth.py`, `mobile/src/app/contexts.tsx` | `test_auth_me_lists_contexts_and_keeps_role` já existente |

## Cobertura de Web e Mobile

O backend calcula os mesmos contextos para a conta e retorna `contexts` à API. A Web utiliza `navigation_context.py` e a página `/minha-conta`; o Expo usa `mobile/src/app/contexts.tsx`, com navegação Cliente/Pro/empresa. Os novos testes exercitam **somente o contrato backend/API**, não simulam a UI Web ou Expo nem certificam navegação end-to-end.

## Decisões aprovadas, ainda não implementadas nesta PR

- **QA-001-UX-01:** identidade social pública principal com área Pro integrada, preservando autoria, reputação, privacidade e URLs legadas. Exige plano de contrato/publicação e gate visual posterior.
- **QA-001-UX-02:** descoberta pública “Explorar estabelecimentos” distinta da gestão “Meus estabelecimentos”, com criação dentro da gestão. Requer paridade de navegação Web/Expo e revalidação dos grants. **Não altera APIs de criação nesta PR.**
- **QA-001-UX-03:** ativação Pro via avatar/Configurações na mesma conta e Cliente permanente; onboarding já existente, mas jornada completa ainda exige auditoria visual e QA.

## Aceite e limites

A PR A pode ser mergeada após suíte completa pytest, PostgreSQL, Playwright, Node/tsc/lint e segurança verdes. Testes específicos asseguram 401 de bearer inválido/ausente, transição de contextos, múltiplos negócios e revogação de grant; casos 403/409 de mutações permanecem na suíte já existente e exigem rastreio posterior por jornada. **Não declara cobertura total de 401/403/409 ou de concorrência**. Sem migração, dependência, alteração de autenticação, contrato de produção, perfis, slots, reserva, UI ou design tokens.

**Próximo ciclo:** detalhar PR B Web + Expo sob revisão Claude/Notion; PR C perfil público, autoria/reputação e compatibilidade legada com plano específico. Não finalizar QA-001 apenas com a PR A.
