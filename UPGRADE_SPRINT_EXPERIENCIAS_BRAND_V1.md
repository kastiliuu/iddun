# Sprint — Experiências IDDUN Brand V1

## Objetivo

Redesenhar a rota `/experiencias` para a identidade oficial IDDUN e corrigir os dois problemas estruturais da página: colisão entre busca e navegação no header e primeiro card expandido de forma acidental dentro do grid.

## Entregas

- Header sticky em Ink, CTA Plum → Deep Violet e busca aberta em `dialog`, sem disputar espaço com a navegação.
- Busca mobile em overlay de tela inteira até 760 px.
- Hero editorial com glow assimétrico, textura sutil, assinatura ✦ e busca glass com foco Plum.
- Filtros com contadores, estado selecionado, scroll horizontal, foco visível e painel mobile.
- Ordenação por recomendação, preço, avaliação e itens mais recentes.
- Card “Destaque da semana” isolado e intencional acima da grade.
- Grid regular uniforme em 3, 2 e 1 colunas.
- Cards com imagem 4:3, duração, próxima disponibilidade, profissional, localização, desconto calculado, preço e CTA.
- Favoritos persistidos em `localStorage`, com `aria-pressed`, texto acessível e animação de confirmação.
- Filtro de categoria client-side progressivo na visão completa, mantendo URLs e fallback server-side.
- Skeleton durante filtros/buscas e estado vazio com ação para limpar filtros.
- Estados de hover, focus-visible e active, além de suporte a `prefers-reduced-motion`.
- Contraste e tipografia revisados com os tokens oficiais Ink, Graphite, Mist, Plum, Deep Violet e White.

## Arquivos principais alterados

- `app/templates/components/header.html`
- `app/templates/components/catalog-experience-card.html`
- `app/templates/public/experiences.html`
- `app/templates/layouts/base.html`
- `app/static/css/components.css`
- `app/static/css/marketplace.css`
- `app/static/css/tokens.css`
- `app/static/css/visual-v2.css`
- `app/static/js/navigation.js`
- `app/static/js/marketplace.js`
- `app/routes/public.py`
- `app/services/experience_service.py`
- `tests/test_experiences.py`

## Decisões de UX

- A busca saiu do fluxo horizontal do header e virou uma ação independente. Isso elimina a colisão em larguras intermediárias sem retirar a busca da navegação.
- O primeiro resultado deixou de depender de `:first-child`. O destaque agora é um componente semântico próprio; os demais resultados nunca mudam de formato por posição.
- Plum aparece somente em ações, foco, descontos, urgência e pequenos elementos de marca. Mist sustenta a área de descoberta e Ink/Deep Violet criam profundidade no hero.
- O filtro client-side melhora a resposta percebida, mas links e parâmetros GET permanecem funcionais sem JavaScript.

## Validação

- `60 passed` na suíte Pytest.
- Sintaxe validada com `node --check` em `marketplace.js` e `navigation.js`.
- Nenhuma migração ou alteração de estrutura do banco de dados foi necessária.
