# IDDUN Mobile V1 — Auditoria final e matriz de aceite

**Status:** plano de auditoria; execução **não iniciada**.  
**Base revisada:** `main` após PR #89 (commit `7abfc8a`), em 13/10/2026.  
**Escopo:** aplicativo Expo/React Native; integrações reais com API Flask; jornadas Cliente, Profissional e Estabelecimento.  
**Não confundir:** a existência da tela, o CI verde ou o teste de backend **não comprovam** funcionamento real no dispositivo.

## 1. Evidências já disponíveis no repositório

| Área | Evidência encontrada | Limitação |
| --- | --- | --- |
| Backend | CI roda pytest com cobertura e migrations Alembic | Não demonstra UX do Expo; cobertura não tem `fail-under` |
| Reservas | Job PostgreSQL testa concorrência de reservas | Não substitui uso simultâneo real de dispositivos |
| Web | CI roda E2E com Playwright no Chromium | Não testa interface React Native |
| Mobile | CI roda `npm run typecheck` e `npm run lint` | `mobile/package.json` não contém script de testes E2E/unitários |
| Segurança | Bandit e pip-audit publicam baseline | Scanners são consultivos (`continue-on-error`) |
| Google Calendar | [Roteiro manual](QA_GOOGLE_CALENDAR_LIVE_V1.md) com GC-01…GC-12 | Todos os cenários estavam marcados **Não executado** no documento consultado; não inferir homologação |

## 2. Achados iniciais de código (validar antes de classificar como bug)

| ID | Prioridade inicial | Constatação | Risco e ação |
| --- | --- | --- | --- |
| AUD-M01 | P1 para lançamento com CRUD Pro no mobile | `mobile/src/app/manage-services.tsx` ainda exibe **Gerenciamento em integração** | Criar/editar/excluir serviços no próprio app não está disponível nessa rota. Decidir se CRUD mobile é requisito da V1; se for, bloquear aceite da jornada Pro até integrar API real |
| AUD-M02 | P1 para encerrar homologação | CI Mobile somente TypeScript + ESLint, sem automação de fluxo Expo | Homologar manualmente em Android e iOS e registrar evidências; planejar testes automatizados das jornadas críticas |
| AUD-M03 | P1 se integração Google for requisito de lançamento | Google Calendar real ainda exige execução documentada de GC-01…GC-12 | Usar calendário e contas exclusivamente de teste, registrar evidências sanitizadas e decisões |
| AUD-M04 | P2 | Verificação de roles e navegação Pro/Business requer dispositivo real | Confirmar permissões e destino correto ao trocar conta, sair, reabrir app ou cair a rede |

**Severidades:** P0 = vazamento, operação indevida ou indisponibilidade generalizada; P1 = bloqueio de jornada essencial ou inconsistência de reserva; P2 = falha recuperável/UX significativa; P3 = cosmético. Prioridade final depende da reprodução.

## 3. Preparação do ambiente

- [ ] Criar ambiente de homologação com base de dados descartável e sem dados pessoais reais.
- [ ] Usar duas contas Cliente, uma Profissional e uma Estabelecimento; reservar também uma conta admin para Google Calendar.
- [ ] Publicar serviço/experiência reais de teste, associar profissional/estabelecimento e criar horários futuros.
- [ ] Anotar versão do app, commit `main`, Android/iOS, tipo de instalação (Expo Go ou development build), ambiente de API e data/hora.
- [ ] Confirmar conectividade do dispositivo com a API alvo e migrações aplicadas.
- [ ] Registrar evidências sem credenciais, tokens, cookies ou informações pessoais.

## 4. Casos exploratórios obrigatórios

Preencher cada caso com **Passou / Falhou / Bloqueado / Não executado**, dispositivo, data, conta de teste, issue e evidência. Não marcar como aprovado com base apenas no código.

| ID | Perfil | Cenário | Resultado esperado | Status |
| --- | --- | --- | --- | --- |
| CL-01 | Cliente | Abrir o app como visitante, navegar pelo feed, descobrir experiência | Exploração possível sem login; ações privadas exigem autenticação | Não executado |
| CL-02 | Cliente | Cadastrar, autenticar, reiniciar o app e encerrar sessão | Sessão coerente; saída limpa; sem acesso indevido a dados anteriores | Não executado |
| CL-03 | Cliente | Buscar experiência, escolher data/hora e iniciar hold | Somente horários disponíveis; preço e profissional corretos | Não executado |
| CL-04 | Cliente | Confirmar hold dentro da validade | Uma reserva confirmada e visível em Meus agendamentos | Não executado |
| CL-05 | Cliente | Retomar hold via Meus agendamentos, tocar Voltar e retornar | Hold pendente não cancelado apenas pela navegação | Não executado |
| CL-06 | Cliente | Simular 409 e timeout após tentativa de confirmação | Estado recuperado pela API; sem duplicar reserva; mensagem honesta na incerteza | Não executado |
| CL-07 | Cliente | Expirar hold e tentar confirmar | Sem confirmação tardia; escolher novo horário | Não executado |
| CL-08 | Cliente | Cancelar reserva, alternar Próximos/Histórico e carregar mais de 50 registros | Estado e paginação corretos; sem perda ou duplicação | Não executado |
| CL-09 | Cliente | Trocar de conta após ter reservas | Dados pertencem apenas à conta autenticada atual | Não executado |
| PRO-01 | Profissional | Concluir onboarding, abrir painel e navegar pelas funções | Perfil persistido, menus corretos, sem tela vazia/travada | Não executado |
| PRO-02 | Profissional | Selecionar serviço autorizado e publicar horário | Horário criado na API e disponível na descoberta quando aplicável | Não executado |
| PRO-03 | Profissional | Abrir horário com serviceId inválido/desatualizado e sem serviços | Não permite publicar serviço que não conste das opções da API | Não executado |
| PRO-04 | Profissional | Derrubar temporariamente API de serviços e tocar Tentar novamente | Recuperação sem fechar o app | Não executado |
| PRO-05 | Profissional | Receber, aceitar e recusar convites de estabelecimentos | Estado real refletido após ação e retorno à tela | Não executado |
| PRO-06 | Profissional | Abrir gerenciamento de serviços | Validar escopo da V1: rota atualmente provisória | Não executado |
| BUS-01 | Estabelecimento | Abrir painel, equipe e convites | Somente equipe do estabelecimento autorizado | Não executado |
| BUS-02 | Estabelecimento | Convidar profissional por conta existente e aceitar no perfil Pro | Convite pendente vira vínculo ativo após aceite | Não executado |
| BUS-03 | Estabelecimento | Cancelar convite pendente e remover membro ativo | Confirmações distintas e estado persistido correto | Não executado |
| BUS-04 | Estabelecimento | Criar rascunho de vaga, publicar e encerrar | Estado atualizado sem operações concorrentes duplicadas | Não executado |
| BUS-05 | Estabelecimento | Consultar candidatos e verificar isolamento de outro estabelecimento | Sem acesso cruzado a candidatos ou dados privados | Não executado |
| X-01 | Todos | Perder conexão em ações de leitura e escrita; restaurar | Feedback e recuperação corretos; sem sucesso falso | Não executado |
| X-02 | Todos | Reiniciar app, voltar pelo sistema, abrir rota diretamente e navegar por abas | Navegação estável e estado consistente | Não executado |
| X-03 | Todos | Testar acessibilidade básica, teclado, telas menores e rolagem | Botões acessíveis; conteúdo legível; sem sobreposição | Não executado |
| X-04 | Integrações | Executar checklist GC-01…GC-12 com Google real de teste | Evidências e resultados por cenário, sem tocar contas pessoais | Não executado |

## 5. Política de execução e aceite

1. Rodar testes em **ao menos um Android e um iPhone** (ou registrar impossibilidade e risco explícito).
2. Anotar **Passou** somente com execução e evidência. Falhas viram issues com passos de reprodução, severidade e commit.
3. Corrigir primeiro P0/P1; reexecutar cenário afetado e regressão de CL-03 a CL-08, PRO-02, BUS-02 a BUS-05.
4. Tratar AUD-M01 como decisão de escopo explícita: **não anunciar gerenciamento completo de serviços no app** enquanto a rota estiver provisória.
5. Aprovar a etapa apenas quando nenhum P0/P1 conhecido estiver aberto, todos os cenários essenciais tiverem resultado/evidência e pendências P2/P3 tiverem decisão documentada.
6. Não equiparar **aceite Mobile V1** a aprovação para App Store/Google Play: publicação, política de privacidade, observabilidade, infraestrutura e operação exigem etapa própria.

## 6. Registro dos resultados

| ID | Status | Dispositivo/build | Data/hora | Evidência/issue | Responsável |
| --- | --- | --- | --- | --- | --- |
| A preencher durante execução | Não executado | — | — | — | — |

**Próxima ação:** executar CL-01…CL-09 no Expo antes de iniciar nova sequência de PRs. Atualizar este documento conforme execução, sem marcar verificações presumidas como sucesso.
