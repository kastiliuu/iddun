# IDDUN — Checkpoint Sprint 8.1.1
## QA Hotfix & Profile Polish

**Data:** 2026-09-18

## Resultado

A Sprint 8.1.1 fecha os pontos críticos encontrados no QA de perfis Pro e Business e consolida o consentimento no vínculo profissional.

## Correções funcionais

- Vínculo Business → Profissional agora nasce como `PENDING`.
- O profissional recebe o convite no dashboard e pode aceitar ou recusar.
- Aceite altera o vínculo para `ACTIVE`; recusa altera para `REJECTED`.
- Remoção posterior pelo estabelecimento altera para `INACTIVE`.
- Somente vínculos `ACTIVE` aparecem em páginas públicas, contadores e serviços.
- O painel Business diferencia equipe ativa de convites aguardando resposta.
- O Admin reconhece os quatro estados do vínculo.
- Categoria Tatuagem foi adicionada à Home com asset próprio.

## Lapidação visual e UX

- Fade das capas foi reduzido para preservar a imagem sem perder contraste do texto.
- Hero da Home e heros de perfil ficaram mais compactos.
- WhatsApp agora usa a mesma geometria dos demais CTAs.
- Upload de avatar, logo e capa usa um único componente reutilizável.
- Editor de perfil e editor Business receberam o mesmo padrão visual do onboarding.
- Avatar, logo e capa possuem controle de enquadramento horizontal e vertical sem destruir o arquivo original.
- Portfólio e galeria pública agora funcionam como trilhos navegáveis com controles.
- A ação de adicionar trabalhos ganhou dropzone, prévia e instrução mais clara.
- Hover de “Ver perfil/página pública” foi corrigido para o contexto claro do editor.
- Onboarding Business explica consentimento, identidade e reputações separadas.

## Banco e migration

Nova migration: `a91c5e7d3b20_profile_media_and_membership_consent.py`.

Campos adicionados:

- `professional_profiles.cover_focus_x`
- `professional_profiles.cover_focus_y`
- `establishments.logo_focus_x`
- `establishments.logo_focus_y`
- `establishments.cover_focus_x`
- `establishments.cover_focus_y`

Vínculos existentes não são alterados. O novo comportamento `PENDING` vale para convites criados pelo IDDUN Business.

## Validação executada

- Suite completa: **54 passed**.
- Python compileall: OK.
- 49 templates Jinja parseados: OK.
- JavaScript `platform.js` e `professionals.js`: sintaxe OK.
- Estrutura de chaves CSS: OK.
- Alembic upgrade do zero: OK.
- Downgrade 8.1.1 → 8.1: OK.
- Upgrade 8.1 → 8.1.1: OK.

## Limpeza controlada do banco

- Novo comando `flask --app run.py reset-data`.
- `--dry-run` informa o alvo e os registros sem alterar dados.
- Confirmação interativa obrigatória por padrão.
- Produção exige também `--allow-production`.
- Todos os registros da aplicação são removidos.
- Schema, índices, constraints e `alembic_version` são preservados.
- Sequências de IDs são reiniciadas quando o banco suporta a operação.
- Arquivos em `app/static/uploads` não são apagados.
