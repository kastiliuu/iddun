# QA-01 — PostgreSQL e concorrência de reservas

## Proteção comprovada por esta PR
- Executa migrações reais em PostgreSQL 16 descartável no GitHub Actions.
- Duas transações independentes tentam reservar o **mesmo slot**.
- A restrição parcial `uq_bookings_active_slot` precisa aceitar uma única reserva ativa e rejeitar a outra.
- Verifica a existência do índice criado pela migration no próprio PostgreSQL.

## Limitação crítica — NÃO solucionada nesta PR
A unicidade de `bookings.slot_id` não impede que o mesmo profissional tenha **dois slots distintos com horários sobrepostos**, possivelmente relacionados a estabelecimentos diferentes. A função `create_slots_batch` verifica sobreposição antes de inserir, mas a consulta seguida de inserção não é, sozinha, uma garantia transacional quando duas publicações ocorrem ao mesmo tempo.

**Próximo gate obrigatório para agenda compartilhada:** adicionar e testar uma proteção transacional no PostgreSQL para sobreposição por profissional, cobrindo intervalos cruzados em duas empresas. A implementação deve considerar estados ativo/bloqueado, cancelamento, vínculo, Google Calendar e comportamentos de disponibilidade já aprovados na V6. Não publicar agenda multiempresa como protegida até esse cenário passar.

## Operação
- Job: `PostgreSQL / concorrência de reservas`.
- Roda apenas com um serviço PostgreSQL descartável `iddun_qa`, sem credenciais de produção.
- A suíte geral SQLite continua separada. O teste PG é explicitamente `skip` fora do ambiente de CI PostgreSQL.
- Se houver falha, bloquear merge e investigar; não desativar a asserção.
