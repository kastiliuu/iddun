# IDDUN V1 — Roteiro de homologação

**Base auditada:** `main@809e9afa` (merge da PR #253). **Entrega em revisão:** PR #254 (4/4), branch `be/v1-pr4-mobile-services-refresh`; não considerar concluída antes de CI e homologação.
**Ambiente:** homologação (nunca produção), com contas e dados de teste.
**Decisões:** Notion 08, V1-CONV-D01 a D07, DS-V1-01-D01 a D03, D-NV07-01/02/03, A1-DEC-01 a 03.

Cada passo traz o resultado esperado. Marque **OK**, **Falhou** (com print e horário) ou **Não executado**. O teste automatizado de cada passo, quando existe, está em "Automático"; ele não substitui a conferência em aparelho real.

## 0. Preparação

| # | Passo | Esperado |
|---|---|---|
| 0.1 | Aplicar `flask db upgrade` numa base de homologação | Sobe até `a74c1r2p2026` sem erro; `flask db check` acusa só o desvio antigo `uq_notification_preferences_user` |
| 0.2 | Criar ou usar contas de teste: Cliente, Cliente sem perfil Pro, Profissional, Dona de estabelecimento, Gerente do mesmo estabelecimento, Admin IDDUN | Contas entram na Web e no app |
| 0.3 | Instalar o app de homologação (Android e iOS) apontando para a API de homologação | O app abre no tema claro |

## 1. Cliente

| # | Passo | Esperado | Automático |
|---|---|---|---|
| C1 | No app, Perfil › Aparência: alternar claro/escuro; fechar e reabrir | O app inteiro troca de tema e lembra a escolha; cabeçalho preto nos dois; textos e botões legíveis | auditoria de contraste no render web (PR 3) |
| C2 | Abrir serviço → escolher horário → na confirmação, tocar "Escolher outro horário" | O horário retido aparece como "Seu horário em andamento"; escolher outro libera o anterior (QA-004) | `test_qa004_choose_another_time.py` |
| C3 | Outra conta abre o mesmo serviço durante C2 | O horário retido não aparece para ela | idem |
| C4 | Web, Minha conta › Privacidade › Aparelhos: encerrar uma sessão do app | O app volta para o login na próxima ação | `test_web_app_sessions.py` |
| C5 | Abrir `/vagas` sem perfil profissional e tentar se candidatar | A página explica que precisa de perfil profissional; nada é enviado | `test_recruitment_pilot.py` |

## 2. Profissional

| # | Passo | Esperado | Automático |
|---|---|---|---|
| P1 | Web, Pro › Serviços › Criar serviço: tentar avançar sem nome | Não avança; o campo fica em foco com a mensagem | `test_web_service_wizard_catalog.py` |
| P2 | Preencher preço IDDUN maior que o regular | Etapa 2 recusa com "O preço IDDUN não pode ser maior que o preço regular." | idem |
| P3 | Concluir as 5 etapas e salvar | Rascunho criado, privado, sem horário, sem post; aparece selecionado em Meus serviços | `test_service_wizard_catalog.py` |
| P4 | Sem JavaScript (ou leitor de tela): abrir Criar serviço | As 5 etapas aparecem em sequência e o envio funciona | E2E sem JavaScript |
| P5 | Meus serviços: publicar; abrir horário, lote e jornada pelas janelas | Janela com foco no primeiro campo; Esc fecha e volta ao botão; lote com conflito não cria nenhum horário | E2E + `test_api_service_image_batch.py` |
| P6 | Celular (Web, 390 px): Meus serviços | Lista → detalhe → "Todos os serviços" | E2E |
| P7 | App: Criar serviço em 5 etapas com foto; editar um rascunho criado na Web | Foto enviada depois de salvar; o preço regular da Web é mantido | `service-wizard.test.mjs` + API |
| P8 | App: Meus serviços → serviço → Gerenciar horários → "Abrir horários em lote" | Horários criados; repetir o mesmo lote é recusado sem duplicar | `test_v1_negative_paths.py` |
| P9 | App: Criar › "Gerenciar serviços" | Abre Meus serviços (antes aparecia "em integração") | — |
| P10 | Painel Pro: marcar no-show antes da tolerância | O botão não aparece; depois da tolerância exige motivo | `test_booking_operation_rules.py` |
| P11 | Cancelar reserva sem motivo | Recusado; com motivo, registrado em `booking_events` | idem |
| P12 | `/vagas` → vaga → enviar candidatura; retirar; enviar de novo | Funciona; aparece em Minhas candidaturas | `test_recruitment_pilot.py` |

## 3. Estabelecimento (dona e gerente)

| # | Passo | Esperado | Automático |
|---|---|---|---|
| E1 | Dona: Editar empresa › Reservas: salvar 0 e 60; tentar 61 | 0 e 60 aceitos; 61 recusado | `test_booking_operation_rules.py` |
| E2 | Dona: Business › Mais › Vagas com o piloto desligado | "Recrutamento ainda não habilitado"; sem "Nova vaga"; vagas antigas seguem editáveis e encerráveis | E2E `test_web_recruitment.py` |
| E3 | Admin habilita (E5); dona cria rascunho e publica | Vaga em `/vagas`; aparece no app | idem |
| E4 | Gerente sem permissão abre Vagas | "Sem permissão de recrutamento"; não vê vagas nem candidaturas (Web e app) | `test_recruitment_pilot.py` |
| E5 | Dona: "Permitir recrutar" para o gerente; depois "Retirar permissão" | Gerente passa a ver e criar; ao retirar, perde o acesso na hora e continua gerente | idem |
| E6 | App: Gerenciar vagas com o piloto desligado | Aviso de habilitação; sem formulário de vaga | — |
| E7 | Painel Business (PR 1): publicar como empresa; convidar e gerenciar a equipe | Post sai com a empresa como autora; volta para o painel | `test_business_feed_panel.py` |

## 4. Admin IDDUN

| # | Passo | Esperado | Automático |
|---|---|---|---|
| A1 | Estabelecimentos › Recrutamento: habilitar sem motivo | Recusado | `test_recruitment_pilot.py` |
| A2 | Habilitar com motivo; depois revogar com motivo | Histórico mostra as duas mudanças com autor e motivo; revogar não tira vaga do ar | idem + E2E |
| A3 | Reservas: cancelar, concluir e no-show sem motivo | Recusado; com motivo, registrado como admin | `test_booking_operation_rules.py` |
| A4 | Em produção (`APP_ENV=production`): "Simular conflito" | Não aparece; a rota responde 404 | idem |

## 5. Segurança e falhas

| # | Passo | Esperado | Automático |
|---|---|---|---|
| S1 | Trocar o id na URL para um recurso de outra conta (serviço, vaga, reserva, sessão) | Recusa (4xx ou volta), sem dado da outra conta e sem mudança | `test_authorization_matrix.py` |
| S2 | App com sessão expirada ou encerrada | 401 e volta ao login, sem mudança | `test_v1_negative_paths.py` |
| S3 | App em produção: criar rascunho, publicar, abrir horário, salvar jornada | Funciona (antes respondia 400 `csrf_failed`) | `test_api_service_image_batch.py` |
| S4 | Enviar foto de serviço com 6 MB ou arquivo que não é imagem | Recusado com mensagem; a foto anterior fica | idem |
| S5 | Tocar duas vezes rápido em publicar, abrir horário ou enviar candidatura | Um envio só | Web: `data-once`; app: conferir à mão (as telas de serviço desabilitam o botão durante o envio) |

## 6. Lacunas conhecidas (registrar se aparecerem)

- Ícones em cinza ficam abaixo de 3:1 no tema escuro do app (texto está AA).
- Textos sobre fotos (IDDUN Now, cartões) foram conferidos só por captura.
- O app não foi testado em aparelho real pelo agente; os passos de app desta lista são obrigatórios na homologação.


## 7. PR #254 — recuperação do catálogo de serviços Expo (P-003)

**Status dos casos abaixo: NÃO EXECUTADOS em dispositivo.** O teste Node `mobile/scripts/request-gate.test.mjs` verifica o versionamento de leituras, mas não substitui a homologação da tela nem a conferência do catálogo real. A Web continua consumindo os serviços do backend; o app deve reproduzir seus dados e estados sem sobrescrita por resposta antiga.

| ID | Plataforma | Procedimento | Resultado esperado | Automático | Manual |
| --- | --- | --- | --- | --- | --- |
| PR4-SRV-01 | Expo Android/iOS | Abrir Meus serviços, sair da tela com rede lenta e retornar | Só a leitura mais recente altera lista/erro/loading; sem atualização de tela fora de foco | `request-gate.test.mjs` + contrato em `test_navigation_contexts.py` | Não executado |
| PR4-SRV-02 | Expo Android/iOS | Falhar carregamento, tocar Tentar novamente e receber resposta antiga após a nova | Lista atual prevalece; erro antigo não substitui sucesso recente | `request-gate.test.mjs` | Não executado |
| PR4-SRV-02B | Expo Android/iOS | Tocar Tentar novamente e sair imediatamente para outra tela | Retry fica invalidado; resposta tardia não altera o catálogo fora de foco | `request-gate.test.mjs` (teste vermelho antes, verde após correção) | Não executado |
| PR4-SRV-03 | Web/Expo | Criar/editar um serviço pela Web e voltar ao catálogo do app | Nome, preço, duração, estado e categoria coincidem com os dados do backend | API e testes existentes | Não executado |
| PR4-SRV-04 | Expo Android/iOS | Desligar rede e voltar para Meus serviços; reativar e tentar novamente | Erro com ação útil, loading coerente e recarga válida | Testes estáticos e Node (parciais) | Não executado |
| PR4-SRV-05 | Expo Android/iOS | Abrir serviços após alternar contas Pro diferentes | Nunca exibir dados privados da conta anterior | Autorização backend existente; device não verificado | Não executado |

**Bloqueio de aceite do release:** homologação real dos casos acima, fluxos de reserva e jornadas de autorização em iOS/Android, checklist de acessibilidade e evidências associadas às matrizes Notion 79/89. **RECRUIT-A2:** dependente da aprovação separada do contrato da página 113; não foi incorporada nesta PR.
