# IDDUN — Sprint 7.3.1 · Visual Rebalance (sem imagens)

Data: 16/09/2026

## Objetivo
Reequilibrar a Visual Direction V2 após QA da Sprint 7.3, removendo dependência de fotografias nesta etapa para validar primeiro hierarquia, ritmo, conversão, componentes e responsividade.

## Decisões
- Hero deixou de usar fotografia e headline experimental gigante.
- Headline volta a ser clara e orientada a produto: "Descubra sua próxima experiência de beleza."
- Busca e CTA principal permanecem na primeira dobra.
- Coluna visual do hero passa a demonstrar o produto (oportunidades/disponibilidade) sem imagens.
- Categorias usam ícones, tipografia, números e composição editorial sem background fotográfico.
- Experiência em destaque usa um palco abstrato/placeholder editorial, pronto para receber imagem posteriormente.
- Cards de experiências e profissionais na Home não dependem de fotos nesta versão; usam blocos visuais e monogramas.
- Mantidos motion system, reveals, header glass, scroll-snap mobile e Visual Direction V2 global.
- Nenhuma regra de negócio ou schema de banco foi alterado.

## Princípio
Primeiro aprovar layout, hierarquia, espaçamento e UX. Fotografias entram depois como camada de conteúdo, sem definir a arquitetura do layout.

## Validação técnica
- 36 templates Jinja parseados.
- Python compilado sem erro.
- JavaScript relevante validado com `node --check`.
- CSS com chaves balanceadas.
