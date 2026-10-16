# IDDUN V0 — Auditoria de reservas pós-PR #108

Base analisada: `main` em `7df37b44`. Referência de negócio: Notion DEC-ID-188–196; TC-CLI-RES-021–040.

## Correção entregue

- O serviço nativo de calendário não interpreta mais uma falha de leitura/atualização como remoção do evento. Antes, uma exceção capturada indiscriminadamente caía no caminho de criação de um novo evento, com risco de duplicar a reserva no calendário.
- A rotina de exclusão também preserva a referência local quando a API nativa falha; assim a operação poderá ser tentada novamente.
- A comparação de datas usa também o evento real, evitando considerar como sincronizado um evento alterado fora do IDDUN.
- Testes estáticos adicionados para prevenir regressão na rotina e conferir versão declarada.

## Bloqueador: lockfile de expo-calendar

A entrada de `node_modules/expo-calendar` no `mobile/package-lock.json` foi criada no PR #108 com `version` e `resolved`, **sem integridade `sha512`**. Não obtivemos acesso ao registro npm neste ambiente para regenerar e verificar o arquivo com o instalador oficial.

**Antes de aprovar o merge, executar em máquina com acesso ao npm:**

```bash
cd mobile
npm install --package-lock-only --ignore-scripts
npm ci
npm run lint
npm run typecheck
```

Fazer commit de qualquer mudança produzida pelo npm **nesta mesma branch**. Não preencher `integrity` manualmente ou presumir `npm ci` verde. Confirmar a versão compatível no `npx expo install --check`.

## Matriz de testes manuais — development build, não Expo Go

1. iOS: conceder e negar permissão, calendários graváveis e ausência de calendários, criar evento, fechar e reabrir a tela, repetir sincronização sem duplicar.
2. Android: mesmos cenários, incluindo múltiplas contas/calendários, escolha de calendário gravável e restrições de permissão.
3. Reagendamento aprovado: solicitar atualização, confirmar novo horário, UID e ausência de duplicação local.
4. Cancelamento: impedir novas exportações; remover apenas evento rastreado pelo app; negar permissão e tentar novamente, sem perder referência.
5. Evento removido/alterado pelo usuário: comportamento previsível ao sincronizar novamente.
6. Dispositivo offline, sessão expirada, reserva alheia (404) e tela de erro.
7. Acessibilidade: VoiceOver/TalkBack, tamanho dinâmico de texto, foco e contraste dos botões de calendário e mensagens de erro.

## Limites documentados (não tratados como funcionalidades concluídas)

- Atualizações e cancelamentos de eventos **não são automáticos** em background.
- AsyncStorage rastreia apenas eventos neste dispositivo, sem sincronização multiplataforma; em queda entre criação nativa e persistência, ainda há risco residual de duplicação.
- `expo-calendar/legacy` exige teste com build nativo real; qualquer incompatibilidade de runtime deverá ser corrigida em novo commit antes de merge.
- Filtros avançados, snapshots de preço/duração e paridade web/mobile TC-040 carecem de validação exploratória de ponta a ponta.
- Não foram executados testes reais de dispositivo nem `npm ci` neste ambiente.
