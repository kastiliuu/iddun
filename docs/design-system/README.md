# IDDUN — Design System 2.0 (Editorial Híbrido)

**Status:** especificação de implementação, não homologação visual.  
**Baseline auditado:** main em 20/10/2026, árvore Git SHA `4c4489dfff2b825a98967638edef309f143a942a`.  
**Governança:** Notion guarda decisões FE-DEC/DEC; GitHub contém os contratos implementáveis, código e testes. Mudanças conflitantes exigem decisão explícita antes de alterar regras aprovadas.

## Fonte normativa
- [Notion — Design System e UX](https://app.notion.com/p/3f8a19c0eb2681689bf0d42107258752)
- [Notion — Matriz de auditoria visual](https://app.notion.com/p/3faa19c0eb2681579f59d10e0be12f6c)
- [Notion — Plano de Sprints V0](https://app.notion.com/p/3faa19c0eb26814b8791cfabb16fb96e)
- [Notion — Arquitetura documental DOC-00](https://app.notion.com/p/3faa19c0eb268135b141f973aca92da2)

## Identidade oficial — imutável sem nova decisão
| Token primitivo | Valor |
|---|---|
| ink | `#0B0B0F` |
| graphite | `#2A2A33` |
| mist | `#DADDE1` |
| plum | `#6B2EFF` |
| deepViolet | `#1A0F2E` |
| offWhite | `#F7F6F4` |

Inter é a fonte padrão de interface, Playfair Display é reservada a títulos editoriais. ✦ SPARK é símbolo da marca. Não reintroduzir dourado/champanhe.

## Direção B — superfícies
- **Dark:** navegação, identidade e superfícies institucionais, com atenção a legibilidade.
- **Light:** conteúdo editorial, exploração, formulários e cartões quando favorecerem leitura.
- Híbrido não significa tema hardcoded por componente. Definir tokens semânticos para `surface`, `onSurface`, `border`, `muted`, `action`, `focus`, `success`, `warning` e `danger` para cada contexto.
- FE-DEC-001–010 requerem seleção light/dark; implementar mecanismo de preferência persistida após fechar contrato; componentes devem respeitar o contexto e não inverter cores individualmente.

## Escalas aprovadas — FE-DEC-011–020
- Corpo: 16px; secundário: 14px; legenda: 12–13px; título funcional: 20–24px.
- Pesos Inter: 400/500/600/700.
- Espaçamento: 4/8/12/16/24/32/48; raio: 8/12/16/24.
- Toque mínimo 44px, ideal 44–48px para ações; verificar escalabilidade de texto.
- Botões: primary Plum, secondary, tertiary, destructive; foco, disabled, loading e erro; sombra discreta.
- Formulários: labels visíveis; mensagens junto ao campo sem apagar dados.

## Contrato de motion
- Priorizar CSS para estados simples da web e Reanimated no Expo; avaliar Motion JS/GSAP somente em contextos comprovados.
- Three.js é experimental e não deve bloquear entrega V0 nem integrar feed/booking/dashboard por padrão.
- Movimento deve informar mudança de estado; `prefers-reduced-motion`/redução nativa obrigatória.
- Motion nunca atrasa confirmação de reserva, interação de formulário ou feedback de erro.

## Escopo de componentes
Buttons, fields, select, chips, badges semânticos, card de serviço, card social, avatar/capa/cropper, toast, loading SPARK, skeleton, empty/error/offline, dialogs, header e bottom nav.
- Cliente: Início, Explorar, Reservas, Favoritos, Perfil.
- Pro: Painel, Agenda, Serviços, Clientes, Mais.
- Business: Painel, Agenda, Equipe, Serviços, Mais.
- Troca de contexto explícita pelo avatar; Criar contextual. FE-DEC-021–030.
- Feed masonry e CTA legítimo; não usar mocks em produção. FE-DEC-031–040.

## Evidências necessárias antes do aceite
- Matrizes por rota/tela, plataforma, viewport, light/dark, estado, FE-DEC, arquivo, teste e PR.
- 320/375/430/768/1024/1280/1440px quando aplicáveis; teclado, leitor de tela e textos ampliados.
- Contraste WCAG AA e foco visível; feedback loading/empty/error/offline e permissões.
- Regressão de reserva, autenticação, agenda, perfis, serviços e contextos.
- Não declarar concluído só por documentação, PR aberto ou CI verde.

## Regras para PR
1. Branch específica sobre main atual; 1 unidade de alteração coesa por PR; merges permanecem humanos.
2. Descrever FE-DEC, arquivos, risco, testes realizados/não realizados, screenshots e rollback.
3. Não adicionar dependências de animação antes de medir impacto e verificar licença.
4. Respeitar arquitetura Flask/Jinja e Expo React Native; não migrar stack por estética.
5. Documentar implementação real e atualizar o Notion com evidência após merge.
