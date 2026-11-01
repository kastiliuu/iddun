# Onboarding V0 — Profissional e Estabelecimento

Registro técnico das PRs 1 a 4 do novo cadastro por etapas (Web e app).
Regras de produto vêm das decisões aprovadas no Notion; aqui fica o que o
código faz e onde está a prova.

| PR | Escopo | Estado |
|----|--------|--------|
| #211 | Fundação: id estável, salvamento parcial, publicação explícita | mergeada |
| #212 | Profissional por etapas (Web e app) | mergeada |
| #214 | Estabelecimento por etapas (Web e app) | mergeada |
| PR 4 | Fechamento: retomada, fotos do app, limpeza, a11y, E2E, segurança, documentação | esta PR |

## Decisões aplicadas

| Id | Decisão | Onde está |
|----|---------|-----------|
| F1 | Publicação explícita no Web e no app; legados preservados; nada é migrado ou despublicado automaticamente | `publish_professional_profile`, `publish_establishment` |
| F2 | Endereço manual, sem Google Maps/Places; só para atendimento físico ou híbrido | etapa `endereco` pulada para domicílio |
| F3 | Autenticação, login social, aceite versionado de termos e identidade Pro automática fora destas 4 PRs; cada DEC-ID segue no backlog da V0 | sem mudança de autenticação |
| D-ONB-01 | 8 áreas fixas, iguais no Web e no app | `PROFESSIONAL_CATEGORIES` |
| D-ONB-02 | Apresentação Pro com 40+ caracteres para publicar; perfis publicados não são afetados | `BIO_MIN_LENGTH` |
| D-ONB-03 | Tema visual opcional, padrão Beleza | `visualTheme` |
| D-ONB-04 | Apresentação da empresa com 40+ caracteres | `DESCRIPTION_MIN_LENGTH` |
| D-ONB-05 | E-mail da conta só sugerido; vale apenas quando a etapa é salva | etapa `contato` / app |
| D-ONB-06 | 7 tipos de estabelecimento, iguais no Web e no app | `BUSINESS_CATEGORIES` |
| D-ONB-07 | Fotos do estabelecimento pela API do app (logo, capa, galeria e exclusão), só para o proprietário, mesmos limites do Pro, sem migração | `app/routes/api_media.py` |

## Estados separados

O cadastro nunca mistura estes estados (preservados desde a PR 1):

- **Cadastro concluído** — `journey.registrationComplete`: etapas obrigatórias preenchidas.
- **Perfil 100%** — `journey.profileComplete` / `profileCompletion`: inclui fotos e itens opcionais.
- **Publicado** — `is_active` verdadeiro, só depois da ação explícita de publicar.
- **Reservável** — não faz parte do onboarding: depende de serviço publicado, equipe e horários (DEC-ID-108).

Mais um estado tratado na PR 4:

- **Fora do ar pela moderação** — `published_at` preenchido e `is_active` falso.
  A publicação recusa com `publication_locked` (já era assim). Agora a
  retomada também respeita isso: Web e app não mostram "rascunho" nem
  levam de volta ao cadastro; o painel mostra "Fora do ar" e o caminho
  do suporte.

## Etapas

### Profissional (Web `/pro/onboarding/<etapa>`, app `pro-onboarding`)

| # | Slug Web | Chave | Obrigatória para publicar |
|---|----------|-------|---------------------------|
| 1 | `nome` | `identity` | nome de exibição |
| 2 | `cidade` | `location` | cidade e UF |
| 3 | `especialidade` | `specialty` | especialidade e pelo menos uma área |
| 4 | `atendimento` | `modality` | pelo menos uma modalidade |
| 5 | `apresentacao` | `presentation` | apresentação 40+ |
| 6 | `fotos` | `personalize` | não (opcional) |
| 7 | `revisar` | `review` | publicar |

`/pro/onboarding` retoma na primeira etapa pendente. Conclusão:
`/pro/onboarding/concluido`.

### Estabelecimento (Web `/business/onboarding/...`, app `business-onboarding`)

| # | Slug Web | Obrigatória para publicar |
|---|----------|---------------------------|
| 1 | `novo` → `dados` | nome, tipo, cidade e UF (cria o rascunho) |
| 2 | `atendimento` | modalidade |
| 3 | `endereco` | endereço comercial, só físico ou híbrido (F2) |
| 4 | `funcionamento` | modo de horário e, se fixo, grade válida |
| 5 | `contato` | apresentação 40+ e um contato |
| 6 | `fotos` | não (opcional) |
| 7 | `revisar` | publicar |

- `/business/onboarding` — sem rascunhos vai para `novo`; com rascunhos, lista para continuar ou criar outro.
- `/business/onboarding/<id>` (PR 4) — retoma o rascunho pelo id estável na etapa pendente. Só o proprietário ativo; outra conta recebe 404.
- `/business/onboarding/<id>/concluido` — conclusão.

Entradas de retomada: Minha conta, painel Pro, painel da empresa (só para
o proprietário; o gestor vê o aviso de rascunho sem o atalho), `/pro/comecar`
e, no app, a tela "Como você trabalha?".

## API do app

Todas exigem `Authorization: Bearer`, respondem `Cache-Control: no-store`
e ficam fora do CSRF (não usam cookie de sessão).

### `/api/v1/onboarding`

| Método e caminho | Limite | O que faz |
|------------------|--------|-----------|
| `GET /professional` | — | perfil e `journey` |
| `PATCH /professional` | 60/h | salva só as chaves enviadas |
| `POST /professional/publish` | 10/h | publicação explícita; `alreadyPublished` quando repetida |
| `GET /establishments` | — | estabelecimentos do proprietário com `journey` |
| `GET /establishments/<id>` | — | um estabelecimento do proprietário |
| `PATCH /establishments/<id>` | 60/h | salva só as chaves enviadas |
| `POST /establishments/<id>/publish` | 10/h | publicação explícita; `alreadyPublished` quando repetida |
| `POST /establishment` | 20/h | cria o rascunho na etapa 1 do app (nome, tipo, cidade, UF) |
| `POST /professional` | 30/h | rota anterior ao PATCH; o app atual não a usa |

Chaves aceitas no `PATCH` (qualquer outra → 400):

- Profissional: `displayName`, `headline`, `primarySpecialty`, `categories`, `city`, `state`, `bio`, `phone`, `whatsappEnabled`, `instagram`, `attendanceModalities`, `visualTheme`.
- Estabelecimento: `name`, `category`, `city`, `state`, `description`, `phone`, `neighborhood`, `addressLine1`, `addressLine2`, `postalCode`, `commercialEmail`, `operationMode`, `businessHoursMode`, `businessHours`, `whatsappEnabled`.

Chave ausente preserva o valor; `null` ou texto vazio só limpam campos que
podem ficar vazios, com validação.

Erros:

| Código | HTTP | Quando |
|--------|------|--------|
| `authentication_required` | 401 | sem token válido |
| `invalid_onboarding_data` | 400 | campo inválido ou não permitido |
| `establishment_not_found` | 404 | inexistente ou de outra conta (mesma resposta) |
| `establishment_exists` | 409 | rota antiga `POST /establishment` com nome, cidade e UF de uma página do dono já publicada ou desativada (compatibilidade por nome só reaproveita rascunho nunca publicado) |
| `profile_incomplete` / `establishment_incomplete` | 409 | publicar sem os requisitos; `details.missingRequirements` |
| `publication_requirement_removed` | 409 | edição que tiraria um requisito de algo já publicado |
| `publication_locked` | 409 | publicar algo desativado pela moderação |

### `/api/v1/media/establishments` (D-ONB-07, PR 4)

| Método e caminho | Limite | O que faz |
|------------------|--------|-----------|
| `GET /<id>` | — | logo, capa e galeria |
| `POST /<id>/logo` | 30/h | multipart `file`, `focusX`, `focusY` |
| `POST /<id>/cover` | 30/h | idem |
| `POST /<id>/gallery` | 60/h | multipart `file`, `caption` (até 180); até 10 fotos → depois `gallery_limit_reached` (409) |
| `DELETE /<id>/gallery/<item>` | 60/h | remove a foto, apaga o arquivo e reordena |

Mesma validação das fotos do Profissional: até 5 MB, tipo conferido pelo
conteúdo (extensão divergente é recusada), metadados removidos, JSON → 415.
Trocar logo ou capa apaga o arquivo anterior. Fotos não mudam o estado de
publicação.

## Revisão de segurança (PR 4)

| Risco | Controle | Prova |
|-------|----------|-------|
| Acessar ou alterar rascunho de outra conta | `owned_establishment` filtra por proprietário ativo; inexistente e alheio respondem igual (404) | `test_onboarding_resume_and_lock.py`, `test_business_onboarding_wizard.py::test_other_owner_cannot_open_or_change_a_draft`, `e2e/test_web_onboarding_closure.py` |
| Enumerar ids / id fora do INTEGER | id validado (1 a 2 147 483 647) antes da consulta | `test_business_resume_is_only_for_the_owner` |
| Apagar foto de outro estabelecimento | exclusão filtra pelo estabelecimento do dono e pelo item | `test_api_establishment_media.py::test_cannot_delete_another_establishments_gallery_item` |
| Arquivo malicioso ou disfarçado | tipo pelo conteúdo, 5 MB, metadados removidos; falha não deixa arquivo | `test_invalid_image_is_rejected_without_leftovers` |
| Despublicar ou republicar sem querer | publicação só pela ação explícita, com trava de linha e idempotente; mídia não muda publicação; moderado não volta | `test_postgres_onboarding_publish.py`, `test_media_on_published_establishment_keeps_it_published`, `test_moderated_*` |
| Gestor retomando cadastro do dono | atalho só para `role == owner`; rota exige proprietário | `test_manager_sees_the_draft_without_the_owner_shortcut` |
| Abuso por volume | limites por rota (tabela acima) | configuração do `limiter` |
| Cache de dados privados | `no-store` em todas as respostas da API | rotas da API |
| Regressão estática | Bandit `-ll -ii` sem achados | job "Auditoria inicial de segurança Python" |

Fora do escopo (F3): autenticação, login social, aceite versionado de termos
e criação automática de identidade Pro. Continuam no backlog da V0 com seus
DEC-ID.

## Testes

- Unitários e integração: `tests/test_onboarding_foundation.py`, `test_mobile_onboarding_service.py`, `test_api_onboarding.py`, `test_onboarding_professional_steps.py`, `test_business_onboarding_wizard.py`, `test_api_establishment_media.py`, `test_onboarding_resume_and_lock.py`.
- PostgreSQL (concorrência da publicação): `tests/test_postgres_onboarding_publish.py`, executado antes do teste de reservas no CI.
- Navegador: `e2e/test_web_pro_onboarding.py`, `e2e/test_web_business_wizard.py`, `e2e/test_web_onboarding_closure.py` (todas as telas a 390 e 1280 px: texto ≥ 12 px, contraste AA, sem rolagem horizontal, um h1, uma etapa atual, botão ≥ 44 px, foco visível).
- App: `npm run typecheck` e `npm run lint` no CI. Não há testes automatizados de tela no app; a paridade das telas do app foi conferida por código, não por execução em aparelho.
