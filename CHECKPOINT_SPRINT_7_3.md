# IDDUN — Sprint 7.3 — Visual Direction V2

Data: 16/09/2026

## Objetivo
Reformular a camada visual do IDDUN sem alterar as regras de negócio já validadas, incorporando aprendizados das referências Lando Norris, Frans Hals Museum, Stripe e Koox.

## Eixos visuais
- Lando Norris: movimento sutil, narrativa por scroll, fotografia protagonista.
- Frans Hals Museum: editorialidade, assimetria, tipografia estrutural e ritmo visual.
- Stripe: clareza, confiança, componentes consistentes e demonstração do produto.
- Koox: energia, desejo, prova social e mensagens curtas.

## Implementado
- Design tokens V2 para motion, espaços editoriais, superfícies e acentos.
- `visual-v2.css` global com tratamento compartilhado para web, mobile e Admin.
- `motion.js` global com reveal por IntersectionObserver, header glass ao scroll e parallax sutil no hero.
- Respeito a `prefers-reduced-motion`.
- Home completamente reformulada com:
  - hero editorial/cinematográfico;
  - busca como ação principal;
  - categorias em cards fotográficos maiores;
  - experiência destaque editorial;
  - trilho de outras experiências;
  - demonstração visual do conceito agenda/oportunidade;
  - profissionais como conteúdo editorial;
  - trust layer e CTA final.
- Mobile Home com carrosséis/scroll-snap, bottom nav flutuante glass, touch targets e hierarquia própria.
- Marketplace passa a ter primeiro resultado em composição editorial maior no desktop.
- Diretório de profissionais passa a ter primeiro perfil em destaque editorial no desktop.
- Maior respiro vertical em Marketplace, Profissionais e Conta.
- Admin recebe hierarquia/superfícies mais sofisticadas sem mudar fluxos operacionais.
- Botão nativo de limpar `input[type=search]` deixa de injetar azul na paleta.
- Reveals adicionados a Marketplace, Profissionais, Minha Conta e Dashboard Admin.

## Sem alteração de banco
Esta sprint não possui migration nova.

## Validação executada no pacote
- 36 templates Jinja: parse OK.
- Todos os arquivos JS: `node --check` OK.
- Python: `compileall` OK.
- CSS: balanço estrutural de chaves OK.
- `pytest` completo deve ser executado na `.venv` local do projeto.
