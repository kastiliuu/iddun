# IDDUN — Checkpoint Sprint 8.1
## Reputation & Professional Identity

**Data:** 2026-09-18

## Objetivo
Fazer o perfil IDDUN ganhar valor profissional por si só, adicionando contato mensurável, reputação verificável e certificações sem transformar o produto em um ERP.

## Entregas

### WhatsApp em perfis públicos
- Profissional e estabelecimento podem habilitar/desabilitar o botão.
- Usa o telefone/WhatsApp já cadastrado.
- Link abre `wa.me` com mensagem IDDUN pré-preenchida.
- Cada clique é registrado em `contact_clicks` para futura mensuração de demanda.
- Dashboard mostra quantidade de cliques originados pelo IDDUN.

### Avaliações verificadas
- Nova entidade `Review`.
- Só reservas com status `COMPLETED` podem ser avaliadas.
- Profissional e estabelecimento possuem reputações independentes.
- Cada avaliação inclui:
  - 1 a 5 estrelas;
  - comentário opcional;
  - recomendaria / não recomendaria;
  - vínculo com a reserva e o cliente.
- Apenas uma avaliação por reserva para cada alvo (`professional` / `establishment`).
- Página pública mostra média, quantidade, percentual de recomendação e selo de atendimento verificado.
- Em páginas públicas o primeiro nome do cliente é exibido, reduzindo exposição desnecessária.

### Certificações profissionais
- Nova entidade `ProfessionalCertification`.
- Campos:
  - certificação;
  - instituição;
  - emissão;
  - validade opcional;
  - credencial opcional;
  - URL de verificação opcional;
  - comprovante opcional PDF/JPG/PNG/WEBP;
  - visibilidade pública.
- Tela de gestão em `/pro/certificacoes`.
- Certificações públicas aparecem no perfil do profissional.
- Nesta fase são autodeclaradas; não existe selo de verificação manual IDDUN ainda.

### Dashboard IDDUN Pro
Novas métricas:
- média de avaliações;
- percentual que recomenda;
- quantidade de certificações;
- cliques no WhatsApp.

Novos painéis:
- avaliações recentes;
- formação e certificações.

### Dashboard IDDUN Business
Novas métricas:
- nota do estabelecimento;
- percentual de recomendação;
- cliques no WhatsApp.

A reputação da empresa permanece separada da reputação dos profissionais.

## Arquitetura
Novos arquivos principais:
- `app/models/reputation.py`
- `app/models/certification.py`
- `app/services/reputation_service.py`
- `app/services/contact_service.py`
- `app/forms/reputation.py`
- `app/templates/bookings/review.html`
- `app/templates/platform/professional-certifications.html`

Migration:
- `f8a14d6c2e31_reputation_identity_v1.py`

## Fora de escopo desta sprint
- feed;
- seguidores/conexões;
- Resultado IDDUN;
- mensagens privadas;
- vagas;
- horários normais vs. oportunidades;
- verificação manual de certificados;
- resposta pública do profissional às avaliações;
- moderação/admin de reviews.

Esses pontos permanecem no roadmap para sprints seguintes.

## Validações executadas
- `python -m compileall`: OK
- suite completa: **50 passed**
- Alembic upgrade do zero: OK
- downgrade Sprint 8.1 → Sprint 8: OK
- upgrade Sprint 8 → Sprint 8.1: OK
