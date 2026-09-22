# IDDUN — Sprint 7.1.1 · UI Controls Hotfix

## Correção principal
- Stepper numérico (`-` / `+`) reestruturado como um único componente de formulário.
- Os botões agora vivem dentro do mesmo container/borda do input e não podem extrapolar o campo.
- Desktop e mobile têm alturas/touch targets coerentes.
- Ícones `plus` e `minus` centralizados no componente SVG global.

## Padronização
- Tokens semânticos de controles adicionados ao design system (`tokens.css`).
- Inputs/selects/steppers do Admin passam a compartilhar altura, raio, fundo, borda e estados de foco.
- Criada classe reutilizável `.admin-action-button` para ações compactas de cards, evitando diferenças entre `<a>` e `<button>`.
- Ações Editar/Publicar/Pausar e ações de Oportunidades usam o mesmo contrato visual.

## Sem alteração de regra de negócio
- O placeholder de antecedência específica da experiência permanece `Ex.: 60`; o hotfix trata o problema visual dos controles e não altera a semântica do campo.
