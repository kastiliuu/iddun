# Client Feed V1 — Auditoria, referências e arquitetura

## Objetivo

Transformar o IDDUN web autenticado em uma rede social profissional vertical de beleza, em que descoberta visual leva a confiança, experiência, disponibilidade e reserva.

A nova Home autenticada é:

```text
/feed
```

`/minha-conta` continua sendo a área pessoal e de edição do cliente.

---

## Auditoria da main antes desta branch

### ALREADY DONE — reutilizado

- `WorkPost` real para profissionais e estabelecimentos.
- `feed_service.feed_page()` com modos `for-you` e `following`.
- Beauty Graph real:
  - Follow profissional;
  - Follow estabelecimento;
  - Save profissional;
  - Save estabelecimento;
  - Save experiência;
  - Save portfólio;
  - Save WorkPost.
- `/api/v1/feed` paginado por cursor.
- `/api/v1/search` global para:
  - profissionais;
  - estabelecimentos;
  - experiências;
  - posts.
- notificações reais e preferências.
- IDDUN Now real baseado em slots disponíveis.
- reservas reais.
- reputação real por reviews.
- páginas públicas de profissionais e estabelecimentos.
- Design System oficial em `tokens.css`.
- autenticação web Flask-Login.
- APIs Graph aceitando sessão web, além de Bearer do mobile.
- media resolver preparado para local/object storage.

### PARTIAL — corrigido nesta branch

- Home web autenticada inexistente.
- login/cadastro caíam em `/minha-conta`.
- `/minha-conta` acumulava perfil, atividade e formulário.
- Feed real existia, mas sem superfície web.
- Follow/Save real existiam, mas não estavam integrados à Home web.
- busca global existia como API, mas não como busca inline da Home autenticada.
- notificações existiam como API/mobile, mas sem presença real no header web autenticado.
- IDDUN Now existia, mas não como rail de descoberta na Home web.
- feed `following` existia no backend, mas não tinha seletor web.
- bottom navigation autenticada ainda tratava a Home pública como Início.

### MISSING — implementado nesta branch

- rota `/feed`;
- header autenticado próprio;
- busca global com autocomplete real;
- sidebar do cliente;
- feed masonry;
- estados `Para você` / `Seguindo`;
- Save real no card;
- Follow real no card;
- compartilhamento;
- paginação progressiva;
- card de completude contextual;
- próxima reserva;
- rail IDDUN Now;
- recomendações públicas;
- menu de conta;
- navegação mobile específica do feed;
- estados vazios sem conteúdo inventado.

### FORA DO ESCOPO DESTA TELA

- tela dedicada de Salvos no web;
- tela dedicada de Notificações no web;
- perfil público customizado do cliente/username;
- comentários;
- likes/reactions;
- mensagens diretas;
- ranking ML/IA;
- criação de post pelo cliente;
- CRUD mobile de serviços.

---

## Referências pesquisadas

### LinkedIn

Referência: arquitetura profissional e separação entre Follow e Connection.

Pontos absorvidos:
- seguir alguém deve permitir acompanhar conteúdo sem obrigar relação bilateral;
- feed profissional mistura rede seguida e conteúdo recomendado;
- relevância deve considerar identidade, conteúdo e atividade;
- recomendações precisam manter qualidade e contexto profissional.

Fontes:
- https://www.linkedin.com/help/linkedin/answer/a540791
- https://www.linkedin.com/help/linkedin/answer/a1339724
- https://www.linkedin.com/help/linkedin/answer/a525212/feed-do-linkedin-resumo

### Pinterest

Referência: descoberta visual e persistência por Save.

Pontos absorvidos:
- visual deve ser dominante;
- Home combina conteúdo seguido + recomendações;
- conteúdo não precisa ter altura uniforme;
- salvar e seguir são sinais centrais;
- pesquisa/atividade podem futuramente ajustar recomendações.

Fontes:
- https://help.pinterest.com/pt-br/article/explore-the-home-feed
- https://help.pinterest.com/pt-br/article/tune-your-home-feed
- https://help.pinterest.com/pt-br/guide/all-about-pinterest

### Fresha / Booksy

Referência: marketplace vertical de beleza.

Pontos absorvidos:
- descoberta deve terminar em intenção comercial;
- serviço, preço, reputação e disponibilidade reduzem atrito;
- localização e disponibilidade são relevantes para decisão;
- o perfil profissional precisa gerar demanda e reserva.

Fontes:
- https://www.fresha.com/pt/for-business/features/marketplace
- https://booksy.com/pt-br/
- https://biz.booksy.com/pt-br/recursos/marketplace

---

## Arquitetura da tela

```text
ClientFeed
├── FeedHeader
│   ├── Logo
│   ├── GlobalSearch
│   ├── Home
│   ├── Discover
│   ├── Bookings
│   ├── NotificationPopover
│   └── AccountMenu
│
├── ClientSidebar
│   ├── IdentityCard
│   ├── FollowingCount
│   ├── SavedCount
│   ├── ProfileCompletion (somente < 100%)
│   └── ContextSwitch / BecomeProfessional
│
├── FeedMain
│   ├── ForYouTab
│   ├── FollowingTab
│   ├── MasonryGrid
│   ├── WorkPostCard
│   │   ├── Media
│   │   ├── Save
│   │   ├── Author
│   │   ├── Follow
│   │   ├── Reputation
│   │   ├── RelatedExperience
│   │   ├── Share
│   │   └── CommercialCTA
│   └── ProgressivePagination
│
└── DiscoveryRail
    ├── NextBooking
    ├── IDDUNNow
    ├── ProfessionalRecommendations
    └── EstablishmentRecommendations
```

---

## Regra de produto

O Feed não inventa sinais sociais.

Não mostrar:
- likes fictícios;
- comentários fictícios;
- seguidores fictícios;
- horários fictícios;
- notificações fictícias;
- posts mockados em produção.

A ausência de dados deve gerar empty state honesto.

---

## Ranking V1

O backend atual mantém o feed público por atualidade e o modo Seguindo por autoria seguida.

Nesta V1:
- Feed principal reutiliza o contrato existente;
- recomendações laterais priorizam cidade do cliente quando informada;
- perfis já seguidos são excluídos das recomendações;
- verificados aparecem antes quando os demais sinais empatam.

IA/ML não é necessário para lançar a V1.

---

## Critérios de aceite

1. Login sem `next` redireciona para `/feed`.
2. Cadastro sem `next` redireciona para `/feed`.
3. `/minha-conta` permanece acessível e não é substituída.
4. Visitante não acessa `/feed`.
5. Feed usa apenas WorkPosts publicados e autores públicos.
6. Seguindo mostra somente autores seguidos.
7. Follow e Save persistem no Beauty Graph.
8. Busca usa `/api/v1/search`.
9. Badge de notificações usa unread real.
10. IDDUN Now usa slots reais.
11. Próxima reserva usa booking real.
12. Completude desaparece a 100%.
13. Comentários/likes não são simulados.
14. Desktop usa 3 zonas quando houver espaço.
15. Tablet reduz a arquitetura.
16. Mobile usa fluxo vertical + bottom nav.
17. Navegação por teclado preservada.
18. `prefers-reduced-motion` respeitado.
19. Paginação usa cursor real.
20. CI precisa permanecer verde.

---

## QA exploratório

### Autenticação
- login;
- cadastro;
- logout;
- `next` válido;
- `next` externo rejeitado.

### Feed
- Para você populado;
- Para você vazio;
- Seguindo populado;
- Seguindo vazio;
- carregar mais;
- post sem experiência;
- post com experiência;
- mídia ausente/fallback.

### Graph
- seguir;
- deixar de seguir;
- salvar;
- remover salvo;
- estado sincronizado entre card e recomendação.

### Search
- 0 caracteres;
- 1 caractere;
- 2+ caracteres;
- profissional;
- estabelecimento;
- experiência;
- post;
- nenhum resultado;
- Escape;
- clique fora.

### Rail
- próxima reserva presente/ausente;
- IDDUN Now presente/ausente;
- recomendações com e sem cidade;
- usuário que já segue todos os resultados.

### Responsividade
- 1440+;
- 1366;
- 1024;
- 768;
- 430;
- 390;
- 320.

### Acessibilidade
- tab order;
- foco visível;
- aria-expanded;
- aria-pressed;
- labels de ícones;
- reduced motion;
- contraste.
