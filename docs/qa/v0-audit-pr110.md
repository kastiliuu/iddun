# IDDUN V0 — Auditoria técnica PR #110

**Base:** `main` no commit `273cc1de` (após PR #109). **Fonte de regras:** Notion DEC-ID-188–196, TC-CLI-RES-021–040. **Natureza:** inspeção estática do repositório via GitHub; não equivale a executar aplicação, npm, banco, CI ou testes em dispositivo.

## Achados confirmados

| Prioridade | Componente | Evidência / consequência | Ação |
|---|---|---|---|
| P1 | `mobile/package-lock.json` | Registro de `node_modules/expo-calendar` versão 57.0.3 possui `resolved`, **sem `integrity`**. Instalação reproduzível não validada. | **Bloqueador de aceite**: regenerar usando npm real e executar `npm ci`. Não fabricar hash. |
| P2 | `app/routes/api_bookings.py` | `booking_actions` executava `rebook_offer(booking)` duas vezes para construir campos relacionados. Possível consulta redundante/estado divergente. | Corrigido: avaliar uma vez. |
| P2 | Mobile / Solicitações | Filtro considera apenas `cancellationRequestStatus='pending'` e `rescheduleRequestStatus='pending'`; pedidos resolvidos/retirados só ficam no histórico da tela de detalhe. Diferença frente TC-CLI-RES-031/040. | Pendente de escopo: formalizar contrato e UX; não inventar estados neste PR. |
| P2 | Calendário nativo | Risco residual de duplicação entre `createEventAsync` e persistência em AsyncStorage após falha/crash; ausência de sincronização automática após mudanças. | Documentado; demanda teste real e desenho de reconciliação. |
| P2 | Avaliações / snapshot | Detalhe mobile usa duração atual `booking.experience.durationMinutes`, não snapshot comprovado das condições originais; TC-CLI-RES-023 carece de verificação de modelo e migração. | Pendência de auditoria de dados; não exibir garantia de snapshot inexistente. |
| P2 | Expo Calendar | API `expo-calendar/legacy`, permissões e escrita em calendários graváveis não foram exercitadas em development builds. | Testes físicos necessários. |
| P3 | Acessibilidade | Diálogos, descrições de status, foco de leitores de tela e suporte a fonte ampliada não foram auditados em dispositivos. | Plano de QA abaixo. |

## Correções e cobertura adicionadas neste PR

- Remoção da avaliação duplicada de elegibilidade de Reservar novamente em resposta autenticada de `/actions`; coerência dos campos `canRebook` e `rebookExperienceSlug`.
- Regressão de API verifica 401 sem Bearer, 404 para outra conta, cache privado e consistência dos campos de elegibilidade.
- Cobertura efetiva **não calculada**: sem resultado de execução de pytest/coverage ou runner na sessão.

## Verificações bloqueantes de ambiente

Executar no checkout **desta branch**, preservando os resultados e anexando-os ao PR:

```bash
cd mobile
npm install --package-lock-only --ignore-scripts
npm ci
npx expo install --check
npm run lint
npm run typecheck
cd ..
python -m pytest -q
```

Se o npm regenerar `package-lock.json`, incluir o lockfile atualizado neste mesmo PR e executar os checks novamente. **Não sinalizar como verde sem logs**.

## Matriz exploratória V0 (precisa de evidências)

- Cliente: criação/hold/confirmar; cancelamento e retirada; reagendamento aceito/recusado/conflitado; voltar e recarregar app; conta alheia; histórico completo; avaliação apenas após conclusão legítima; no-show e moderação.
- Profissional e Estabelecimento: permissões, aceite e rejeição de solicitações, controle de slots sob concorrência, alterações de executores e preços sob autorização.
- Web x Mobile: dados reais, filtros e estados, status/horário local, mensagens de erro, offline, sessão expirada e tentativas repetidas; conferir TC-CLI-RES-021–040.
- Android e iOS **development builds**: calendário nativo, permissões negadas/revogadas, múltiplos calendários, importação, mudança de horário, exclusão e recuperação de falha; dispositivos diferentes.
- Acessibilidade: VoiceOver/TalkBack, leitor de status, ordem de foco, alvo de toque, fonte ampliada, contraste e mensagens com `accessibilityRole`.

## Critério de saída desta fase

Sem comprovação de `npm ci`, pytest, lint, typecheck, builds e smoke tests, o IDDUN permanece **implementado, mas não validado para piloto**. Este PR é um incremento direcionado de estabilização, **não uma certificação abrangente**.
