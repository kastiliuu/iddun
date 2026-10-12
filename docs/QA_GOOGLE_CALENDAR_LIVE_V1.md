# IDDUN V1 — Homologação manual da integração real Google Calendar

**Status:** roteiro de execução; não representa integração homologada.  
**Pré-requisito:** PRs #76 e #77 aprovadas. Elas testam o reconciliador e o adaptador FreeBusy com simulações, **não** OAuth e Google real.

## 1. Ambiente e isolamento

- [ ] Usar ambiente DEV/homologação e base descartável, jamais a conta Google real de um cliente.
- [ ] Criar profissional, serviço publicado e 3 horários futuros com intervalo suficiente. Usar datas posteriores ao instante da execução, respeitando o prazo mínimo para reservas.
- [ ] Criar duas contas distintas: profissional com agenda Google de teste e cliente de teste. Criar uma conta administradora para operar a tela atual.
- [ ] Ter um calendário Google exclusivo de teste, sem compromissos pessoais ou compartilhamento de informações de terceiros.
- [ ] Definir no ambiente (não fazer commit): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`. A URI autorizada no Google Cloud deve corresponder exatamente à rota `/integracoes/google/callback` usada pela aplicação.
- [ ] Confirmar que a chave de criptografia necessária à persistência dos tokens está configurada conforme o ambiente. Não registrar tokens, secrets, códigos OAuth ou cookies em prints/logs compartilhados.
- [ ] Executar migrations e verificar que a aplicação sobe sem erro.

> **Atenção:** a UI Web existente para configurar, sincronizar e desconectar está em `/admin/profissionais/<professional_id>/integracoes/google`, acessível ao **administrador**. O callback tem validação para admin/profissional, mas o redirecionamento final volta à tela de admin. Portanto, **não considerar autosserviço do profissional validado** nesta etapa.

## 2. Cenários de aceite

| ID | Ação | Resultado esperado | Evidência |
| --- | --- | --- | --- |
| GC-01 | Abrir configurações sem credenciais OAuth | Exibe aviso de configuração, sem tentar conexão | Tela sanitizada |
| GC-02 | Administrador conecta conta de teste via OAuth | Consentimento Google, retorno ao IDDUN e conexão persistida | Print da tela sem dados secretos |
| GC-03 | Escolher calendário de teste e salvar preferências | Calendário selecionado e preferências persistidos após recarregar | Tela de configurações |
| GC-04 | Criar evento externo que sobreponha **somente** um dos 3 horários; sincronizar | Somente o horário sobreposto deixa de ser oferecido; vizinhos continuam livres | Antes/depois no catálogo |
| GC-05 | Iniciar hold de cliente e então criar evento externo conflitante; sincronizar | Hold pendente cancelado; tentativa de confirmação antiga não funciona | Status em reservas |
| GC-06 | Remover evento externo do Google; sincronizar | Horário volta a ficar disponível, respeitando prazo mínimo; hold cancelado não reaparece | Disponibilidade atualizada |
| GC-07 | Confirmar reserva IDDUN em horário livre com criação de eventos habilitada | Reserva confirmada localmente e evento IDDUN criado no calendário de teste | IDs e horário, sem tokens |
| GC-08 | Cancelar reserva confirmada antes do atendimento | Estado do IDDUN cancelado; verificar remoção do evento Google | Estado IDDUN e Google |
| GC-09 | Temporariamente invalidar a integração *somente na conta de teste*; sincronizar | Falha visível/registrada; verificar se disponibilidade e reservas existentes são preservadas | Erro sem credenciais |
| GC-10 | Desconectar calendário e tentar nova sincronização | Conexão removida, interface oferece reconexão, reservas existentes permanecem | Tela e estado da reserva |
| GC-11 | Acessar tela de configuração como cliente/usuário não-admin | Acesso negado/redirecionado sem exibir conexão ou credenciais | Status HTTP/tela |
| GC-12 | Repetir GC-04/06 com horário localizado em Curitiba | Conversões de UTC e `America/Sao_Paulo` corretas; nenhuma hora deslocada | Horários lado a lado |

## 3. Pontos que exigem atenção

- `sync_connection` usa `fetch_busy_windows` da API FreeBusy e `reconcile_external_busy_windows`. **Bloqueio/reabertura automáticos em execução contínua** dependem de quando a sincronização é disparada; confirmar o comportamento do ambiente testado em vez de pressupor um agendador ativo.
- O estado da sincronização é registrado em `last_sync_status`, `last_sync_error` e `last_synced_at`. Conferir o estado após GC-04, GC-06 e GC-09.
- A criação de eventos após confirmação acontece **depois** da confirmação local. Se o Google estiver indisponível, a reserva pode permanecer confirmada sem evento remoto. Executar GC-07 com a integração disponível e documentar separadamente qualquer erro.
- Conferir GC-08 com cautela: falha na exclusão do evento externo não desfaz necessariamente cancelamento local. Registrar discrepância para tratamento operacional.
- A sincronização FreeBusy deve ser validada com evento criado **fora do IDDUN**. Não usar evento que a própria reserva IDDUN gerou como único critério de conflito.
- Evitar eventos com dados pessoais reais. Não testar exclusão/cancelamento em calendário compartilhado de produção.

## 4. Registro de execução (preencher durante a homologação)

| ID | Resultado (Passou/Falhou/Bloqueado) | Data/hora e ambiente | Evidência/issue |
| --- | --- | --- | --- |
| GC-01 | Não executado | — | — |
| GC-02 | Não executado | — | — |
| GC-03 | Não executado | — | — |
| GC-04 | Não executado | — | — |
| GC-05 | Não executado | — | — |
| GC-06 | Não executado | — | — |
| GC-07 | Não executado | — | — |
| GC-08 | Não executado | — | — |
| GC-09 | Não executado | — | — |
| GC-10 | Não executado | — | — |
| GC-11 | Não executado | — | — |
| GC-12 | Não executado | — | — |

## 5. Critérios para considerar a integração homologada

- Todos os cenários aplicáveis estão **Passou**, ou desvios possuem issue, severidade e decisão explícita sobre lançamento.
- Nenhum evento pessoal/real foi afetado.
- Há evidências sanitizadas de OAuth, conflito, restauração, confirmação e cancelamento.
- Problemas de UX/permissão (incluindo eventual autosserviço do profissional) foram registrados e priorizados, **sem confundir a existência do callback com um fluxo disponível na UI Pro**.
- O CI verde das PRs anteriores permanece condição necessária, mas **não substitui** esta homologação real.
