# IDDUN — Checkpoint Sprint 7

Data: 16/09/2026

## Estado

- Flask modular + Jinja
- PostgreSQL + SQLAlchemy + Alembic
- Auth / ClientProfile / ProfessionalProfile / Establishment
- Admin V1
- Experience + ExperienceSlot + Booking
- cutoff configurável
- hold e prevenção de dupla reserva
- bloqueios manuais e externos
- Google Calendar V1
- upload visual de mídia local
- dashboards Admin e estabelecimento
- UI/UX hardening web + mobile

## Google Calendar V1

`CalendarConnection` armazena a configuração do profissional e os tokens criptografados. O motor de sync traduz a agenda Google para `BusyWindow` e usa a mesma regra agnóstica já existente de reconciliação.

Estados continuam:

- AVAILABLE
- HELD
- BOOKED
- BLOCKED_EXTERNAL
- BLOCKED_MANUAL
- EXPIRED

A agenda conectada afeta o slot individual, nunca derruba a Experience inteira.

## Validação da entrega

- 35 testes pytest aprovados
- 36 templates Jinja parseados
- JavaScript validado com `node --check`
- Python compilado
- migration chain aplicada do zero
- `flask db check` sem operações pendentes

## Próxima direção

Depois do QA desta sprint: **IDDUN Pro V1**, dando ao profissional/estabelecimento acesso próprio para gerenciar agenda conectada, oportunidades, reservas, clientes e indicadores sem depender do Admin.
