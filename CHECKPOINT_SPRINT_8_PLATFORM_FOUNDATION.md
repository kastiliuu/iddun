# IDDUN — Checkpoint Sprint 8 · Platform Foundation

Data: 17/09/2026

## Objetivo

Transformar a arquitetura de perfis existente em uma plataforma multi-contexto real, onde a mesma conta IDDUN pode atuar como:

- Cliente
- Profissional (`IDDUN Pro`)
- Gestor/proprietário de estabelecimento (`IDDUN Business`)

Sem duplicar contas e sem prender a identidade profissional a um salão.

## Implementado

### Entrada profissional

Novo fluxo em `/pro/comecar` com a pergunta:

**Como você trabalha hoje?**

Opções:

- Atendo como profissional
- Tenho ou represento um estabelecimento

O acesso continua usando a mesma conta IDDUN.

### IDDUN Pro

Onboarding em `/pro/onboarding` com wizard visual em 5 etapas:

1. Identidade
2. Atuação
3. Sobre você
4. Portfólio
5. Publicar

Regras iniciais:

- foto de perfil obrigatória;
- nome profissional;
- especialidade principal;
- bio mínima;
- cidade/UF;
- mínimo de 3 imagens de portfólio;
- plano inicial `free`;
- página pública própria.

Dashboard profissional em `/pro/painel` com:

- progresso do perfil;
- reservas confirmadas;
- experiências publicadas;
- quantidade de trabalhos no portfólio;
- estabelecimentos vinculados;
- atalho para ver o perfil como cliente;
- edição do perfil.

### IDDUN Business

Onboarding em `/business/onboarding` com:

1. Marca
2. Empresa
3. Localização
4. Galeria
5. Publicar

Cada empresa ganha:

- logo;
- capa;
- descrição;
- categoria;
- endereço;
- galeria;
- plano `free`;
- página pública;
- painel próprio;
- quadro de profissionais.

Foi criado `EstablishmentUserAccess` para separar quem administra a empresa de quem trabalha nela. Isso prepara o produto para múltiplos gestores no futuro.

### Árvore profissional ↔ estabelecimento

A navegação agora funciona nos dois sentidos:

`Empresa → Equipe → Profissional`

`Profissional → Onde atende → Empresa`

O vínculo continua usando `ProfessionalEstablishmentMembership`, preservando a identidade portátil do profissional.

### Perfil público estilo marketplace

Novas páginas:

- `/profissionais/<slug>`
- `/estabelecimentos/<slug>`
- `/estabelecimentos`

O perfil profissional passa a ter composição de apresentação semelhante a uma mistura de LinkedIn/portfólio/marketplace:

- capa;
- avatar;
- headline;
- especialidades;
- bio;
- portfólio;
- experiências;
- locais onde atende.

A empresa possui:

- capa/logo;
- descrição;
- galeria;
- equipe;
- experiências;
- localização.

### Conta multi-contexto

`/minha-conta` agora funciona como hub da conta IDDUN e mostra os ambientes disponíveis:

- Cliente
- IDDUN Pro
- IDDUN Business

O campo legado `User.role` foi preservado para compatibilidade e Admin; os novos contextos são derivados das relações da conta, evitando a limitação de um único papel por usuário.

### Free agora, freemium depois

Foram adicionados campos `plan_tier` em profissional e estabelecimento.

Nesta fase:

- Professional = `free`
- Business = `free`

A arquitetura já está preparada para planos pagos futuros sem reconstruir os perfis.

### Barbearia e tatuagem

Foi criada a base de temas visuais:

- `beauty`
- `barber`
- `tattoo`

Perfis públicos usam o mesmo design system com atmosferas diferentes.

O marketplace também passa a mudar o Hero quando o filtro é:

- `barbearia`
- `tatuagem`

Isso é a fundação. Um redesign completo e específico dessas verticais fica para uma sprint visual posterior.

### Navegação

O Header agora inclui `Estabelecimentos`.

Cards de profissional na Home e diretório agora abrem o perfil público do profissional, não apenas uma busca por nome.

Na página de experiência, profissional e estabelecimento passam a ser links navegáveis quando houver dados estruturados.

## Modelo de dados novo

### ProfessionalProfile

Novos campos:

- `headline`
- `specialties_text`
- `cover_url`
- `visual_theme`
- `plan_tier`
- `onboarding_completed`
- `published_at`

Nova entidade:

- `ProfessionalPortfolioItem`

### Establishment

Novos campos:

- `category`
- `visual_theme`
- `plan_tier`
- `onboarding_completed`
- `published_at`
- `cover_url`

Novas entidades:

- `EstablishmentGalleryItem`
- `EstablishmentUserAccess`

## Migration

Nova migration:

`e7f6a3b92c11_platform_profiles_foundation.py`

Down revision:

`d2c7f4a91b20`

## Validação

- `46 passed` no pytest
- 46 templates Jinja parseados com sucesso
- Python `compileall` aprovado
- JavaScript validado com `node --check`
- cadeia de migrations aplicada do zero em SQLite
- downgrade Sprint 8 → Sprint 7.2 e upgrade novamente executados com sucesso

## Próximos passos sugeridos

1. QA visual do onboarding Pro em desktop e mobile.
2. QA visual do onboarding Business.
3. Refinar dashboard Pro para oportunidades/agenda/reservas reais.
4. Refinar dashboard Business para gestão de equipe e unidades.
5. Criar convites reais de equipe por token/e-mail em vez de vínculo imediato por e-mail.
6. Adicionar avaliações verificadas.
7. Criar páginas específicas completas de Barbearia e Tatuagem.
8. Depois desenhar experiência completa do cliente.
