# IDDUN — Checkpoint salvo em 16/09/2026

Base recebida do usuário: `iddun-master(4).zip`.

## Estado funcional consolidado
- Flask modular + Jinja
- PostgreSQL + SQLAlchemy + Alembic
- Auth + ClientProfile
- ProfessionalProfile
- Establishment
- vínculo Professional ↔ Establishment
- Admin V1
- Experience
- ExperienceSlot
- Booking V1
- cutoff configurável
- hold temporário
- bloqueio manual/externo
- reconciliação preparada para providers de calendário
- tzdata incluído em requirements
- utilitários de timezone restaurados (`utcnow`, `as_utc`, `to_local`, `local_naive_to_utc`)

## Próxima sprint planejada
Google Calendar V1 + polimento integrado de UI/UX e débitos técnicos.

### Backlog de polimento já acumulado
- upload visual de avatar/imagem em vez de URL textual
- timezone como select
- ajuda contextual para antecedência/cutoff em desktop e mobile
- substituir `slug` na UI por `Seu endereço no IDDUN`
- dashboards Admin e Estabelecimento
- alinhamento de Editar/Pausar em experiências no Admin
- melhorar botão Cancelar em oportunidades/nova
- corrigir spinner branco do input number
- dar mais respiro à Home
- substituir o X azul nativo dos campos de busca por controle compatível com a paleta
- revisar tudo em desktop + mobile app-like

## Segurança/higiene do snapshot
Este checkpoint sanitizado NÃO contém `.env`, `.venv`, caches Python/pytest ou segredos locais.
