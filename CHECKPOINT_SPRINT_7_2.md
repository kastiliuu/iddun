# Checkpoint — Sprint 7.2

## Correções
- NumberStepper transformado em componente de altura estável, com label/control/helper alinhados.
- Action bar dos cards administrativos em grid de duas ações com dimensões idênticas para `<a>` e `<button>`.
- Cards de experiência e profissional recebem dimensões padronizadas independentes da resolução/proporção da mídia original.
- Media Focus V1 para ProfessionalProfile e Experience (`focus_x`, `focus_y`).
- Seletor visual de enquadramento por pointer/touch/teclado no upload do Admin.
- Foco de imagem propagado para Home, Marketplace, diretório de profissionais, detalhe da experiência e confirmação de reserva.
- Teste antigo de `Usar padrão` corrigido para a regra aprovada `Ex.: 60`.
- Testes de persistência de foco adicionados.

## Migration
`d2c7f4a91b20_media_focus_ui_consistency.py`
