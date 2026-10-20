# Roadmap incremental — Design System 2.0

**Estado:** planejado. Esta série é uma trilha da Sprint V0-02 existente, não uma duplicação do roadmap V0. Nenhum passo abaixo está homologado.

| Sequência planejada | Unidade | Resultado e critério |
|---|---|---|
| PR DS01 | Governança e especificação | README, roadmap, decisões e diferenças verificadas |
| PR DS02 | Tokens web | Cores semânticas dark/light, compatibilidade aliases e snapshots |
| PR DS03 | Theme mobile | Tipografia 16, radius 12 e semântica light/dark; typecheck/lint |
| PR DS04 | Botões e inputs web | Componente e estados completos, sem regressão de formulários |
| PR DS05 | Componentes mobile | Button, Avatar, cartões, estados e acesso por leitor de tela |
| PR DS06 | Navegação Cliente | Tabs aprovadas, sino, context switch; funcionalidade real |
| PR DS07 | Navegação Pro/Business | Headers, menus por papel/grant; sem ações não autorizadas |
| PR DS08 | Feed web | Masonry, cartões, filtros e provas de usabilidade |
| PR DS09 | Feed/discovery mobile | Paridade semântica, sem APIs falsas e sem regressão |
| PR DS10 | Perfis e mídia | Capa/avatar/crop, visualização separada da edição |
| PR DS11 | Painéis | Hierarquia funcional Pro/Business, responsive |
| PR DS12 | Motion e QA visual | SPARK/skeleton/reduced motion; métricas e regressões |

## Gaps confirmados por inspeção amostral em 20/10/2026
- `mobile/src/theme.ts`: `ColorScheme = "dark"`, `typography.body = 14` e raio `sm=8,md=16,lg=24` sem token 12, divergindo das decisões FE-DEC.
- `app/static/css/visual-v2.css`: tons legados dourados/bege e cores hardcoded.
- `app/static/css/feed.css`: combinação clara/escura já existe, mas cores de superfície locais.
- `app/static/css/components.css`: botão web `min-height:46px` versus `mobile/src/components/Button.tsx` com `minHeight:52`; documentar diferenças intencionais versus regressões.
- `mobile/src/global.css`: referências a Spline Sans; verificar uso efetivo antes de remover.

## Gate entre PRs
- Confirmar head da main antes de cada branch; diff restrito à unidade planejada.
- Executar no ambiente disponível: pytest backend, lint/typecheck Expo e E2E Playwright quando aplicável. Relatar explicitamente itens não executados.
- Evidências screenshots antes/depois e auditoria acessibilidade para alteração visual.
- Usuário revisa e faz merge; somente após isso iniciar PR dependente.
- Atualizar Notion sem reescrever decisões aprovadas e sem declarar implementação pela existência de template.

## Riscos e restrições
Sem migração global de stack. GSAP e Motion não entram automaticamente na base: primeiro prova de conceito e aprovação de impacto. Three.js permanece fase opcional P2. Nenhuma tarefa altera API, auth ou dados sem contrato/testes associados.
