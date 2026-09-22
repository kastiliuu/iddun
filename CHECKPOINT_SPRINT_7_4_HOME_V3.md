# IDDUN — Sprint 7.4 Home V3

## Escopo
Reformulação exclusivamente da página inicial. Nenhuma regra de negócio, banco, rota funcional, Admin, Marketplace, Profissionais, Reservas ou IDDUN Pro foi alterada.

## Direção visual
- Home mais limpa e premium, baseada na direção aprovada em protótipo.
- Hero cinematográfico com retrato à direita e conteúdo concentrado à esquerda.
- Apenas um campo de busca visível na Home (o campo do header é ocultado nesta página).
- Headline: “Descubra o que combina com você.”
- Microcopy reduzida.
- CTA primário + CTA profissional.
- Trust row compacta.
- Categoria em rail horizontal.
- Experiências em cards editoriais mais leves.
- Profissionais em faixa compacta.
- “Como funciona” reduzido a três passos.

## Motion
- glow pulsante em arcos de luz;
- light trails com brilho sutil;
- partículas discretas;
- shimmer no campo de busca;
- brilho periódico no CTA principal;
- glow suave na assinatura;
- parallax de scroll existente;
- micro-parallax de ponteiro no desktop;
- reveals via IntersectionObserver já existente;
- `prefers-reduced-motion` respeitado.

## Asset
`app/static/img/hero-woman-v3.webp` — derivado do asset existente `hero-model.png`, espelhado para posicionar a modelo à direita e otimizado para WebP (~73 KB).

## Arquivos alterados
- `app/templates/public/home.html`
- `app/static/css/home.css`
- `app/static/js/home.js`
- `app/templates/components/header.html` (apenas comportamento/brand copy condicionado à Home)
- `tests/test_home.py`
- `app/static/img/hero-woman-v3.webp`

## Banco / migration
Nenhuma migration nova.
