# IDDUN — Auditoria estrutural de telas e dívida de Design System

Data: 20/10/2026  
Baseline: `main` árvore SHA `086338afb84609fb7892790638e4a246725090ad`  
Status: **inventário integral de caminhos relevantes + inspeção estática amostral**, não auditoria funcional/exploratória integral e não homologação.

## Escopo e método
- Inventariadas as entradas de `app/templates`, `app/static/css`, `mobile/src/app` e `mobile/src/components` na árvore GitHub.
- Inspecionados diretamente arquivos representativos de Home, marketplace, feed, perfis, dashboards, onboarding, booking e tabs mobile.
- Não foram executados navegador, dispositivo físico, Playwright, pytest, lint, typecheck ou teste de contraste; não há screenshots de antes/depois neste relatório.
- Notion 03, 89 e 90 são a fonte de decisões FE-DEC 001–060 e rastreabilidade. Não confundir documento aprovado com código entregue.
- PR #122 estava **aberto e não mergeado** no momento da auditoria, logo seus novos tokens mobile não são parte da `main`.

## Gaps comprovados

| ID | Gravidade | Arquivo/evidência estática | Ação |
|---|---|---|---|
| DS-AUD-001 | P1 | `mobile/src/theme.ts` ainda contém `ColorScheme = "dark"` na main | Migrar tema semântico e persistência após aprovação PR #122 |
| DS-AUD-002 | P1 | `mobile/src/app/(tabs)/_layout.tsx` traz tab `create` | Alinhar navegação Cliente com FE-DEC-021–030: Início/Explorar/Reservas/Favoritos/Perfil; Criar contextual |
| DS-AUD-003 | P1 | `mobile/src/app/create-service.tsx` contém “Cadastro de serviços em integração” | Resolver placeholder funcional antes de declarar V0 pronta; depende de contratos |
| DS-AUD-004 | P1 | `app/static/css/visual-v2.css` mantém #cfb98e, #87683f, #f3e5c7, #6f512e | Remover paleta dourada/bege com screenshot de regressão |
| DS-AUD-005 | P1 | `app/templates/platform/professional-edit.html` possui 540 linhas com hero/editor e múltiplas seções | Simplificar edição; separar perfil público, mídia e formulário com teste visual |
| DS-AUD-006 | P1 | `mobile/src/app/professional-onboarding.tsx` com 2976 linhas e 117 ocorrências `style={{...` na contagem estática | Quebrar em etapas/componentes/testes; evitar refactor em bloco |
| DS-AUD-007 | P2 | `mobile/src/app/booking/[serviceId].tsx` com 2313 linhas | Modularizar etapas e estilos preservando regras de reserva |
| DS-AUD-008 | P2 | `mobile/src/app/(tabs)/index.tsx` (1351 linhas), `discover.tsx` (1253), `create.tsx` (1186) | Extrair componentes reaproveitáveis após baseline visual |
| DS-AUD-009 | P2 | `app/static/css/feed.css` mistura fundo #F1F1F3 e regras dark em seletores locais | Consumir tokens semânticos DS02 gradualmente |
| DS-AUD-010 | P2 | `app/templates/platform/professional-dashboard.html` tem hero editorial e vários módulos | Revisar hierarquia funcional e densidade em desktop/mobile |
| DS-AUD-011 | P2 | `app/templates/platform/business-dashboard.html` usa hero e painéis business | Harmonizar com Pro, mantendo ações por permissão |
| DS-AUD-012 | P2 | `app/templates/public/home.html` (908 linhas) e `experiences.html` (942) | Componentizar seções e reduzir variações de identidade |
| DS-AUD-013 | P2 | `mobile/src/app/manage-services.tsx` já carrega `getManagedServices` da API (não é mais o placeholder histórico) | Auditar estados, CTA de criação e autorização; não registrar bug antigo sem reprodução |
| DS-AUD-014 | P2 | `mobile/src/app/(tabs)/profile.tsx` concentra ~1007 linhas | Separar visualização, edição, permissões e configurações |

## Matriz inicial de reformulações — a confirmar visualmente

| Jornada | Tela/arquivos web | Tela/arquivos mobile | Prioridade | Natureza |
|---|---|---|---|---|
| Design base | `tokens.css`, `components.css`, `visual-v2.css` | `theme.ts`, `components/*` | P0 de fundação | Tokens, tipografia e estados |
| Cliente navegação | `feed/index.html`, componentes header/bottom-nav | `(tabs)/_layout.tsx`, `(tabs)/index.tsx` | P1 | Destinos e switch contextual |
| Feed e descoberta | `feed/index.html`, `feed.css`, `public/experiences.html` | `(tabs)/discover.tsx`, `post/[id].tsx` | P1 | Editorial híbrido + masonry |
| Perfil Pro | `professional-edit.html`, `public/professional-detail.html` | `professional/[id].tsx`, `(tabs)/profile.tsx` | P1 | Separar exibir/editar e mídia |
| Onboarding | `professional-onboarding.html`, `business-onboarding.html` | `professional-onboarding.tsx`, `signup-pro/index.tsx` | P1 | Simplificação por etapas |
| Serviços | `professional-services.html`, `professional-service-form.html` | `create-service.tsx`, `manage-services.tsx` | P1 | Completar CTA real |
| Reserva | `bookings/confirm.html`, `bookings/mine.html` | `booking/[serviceId].tsx`, `bookings.tsx` | P1 QA / P2 visual | Clareza sem quebrar contrato |
| Painel Pro | `professional-dashboard.html`, `pro-dashboard.css` | rotas operacionais atuais | P2 | Hierarquia operacional |
| Painel Business | `business-dashboard.html`, `platform.css` | rotas Business atuais | P2 | Layout por permissões |
| Landing pública | `public/home.html`, `home.css` | — | P2 | Direção editorial e motion |
| Administração | `admin/*`, `admin.css` | — | P3 | Consistência funcional, não cinematográfica |

## Ordem proposta em PRs
1. **Auditoria e matriz**: inventário rastreável com baseline, telas, evidência e status; este PR somente documentação.
2. **Mobile semantic theme**: aguardar revisão/merge do #122, não duplicar branch.
3. **Web legacy palette**: tratar visual-v2 CSS, tokens de feed, checagem por screenshots.
4. **Navegação Cliente**: FE-DEC-021–030; alterar tab `create` apenas com fluxo contextual equivalente.
5. **Onboarding e perfis**: componentes e etapas, validação e media crop.
6. **Serviços**: remover placeholder após implementar contrato real.
7. **Feed/Descoberta**: masonry, cartões, responsividade, 320–1440 CSS px.
8. **Dashboards e admin**: hierarquia, permissões e acessibilidade.
9. **QA visual final**: screenshots, contraste, screen reader, reduced motion, iOS/Android e E2E.

## Critérios de aceite por tela
Registrar ID tela, público, rota, cenário, responsividade, light/dark, loading/error/empty/offline, foco, reader, FE-DEC, screenshot, TC, resultado, PR e reviewer. Só classificar **Verified** após execução; nenhum item acima está homologado.
