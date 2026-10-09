# IDDUN Pro Dashboard V1

## Escopo

A V1 do IDDUN Pro é a área operacional do profissional dentro do IDDUN. Ela não substitui a experiência de cliente e não é um ERP de salão.

Rotas principais:

- `/pro/painel` — visão operacional do dia;
- `/pro/clientes` — CRM baseado em reservas reais;
- `/pro/insights` — desempenho financeiro e operacional;
- `/pro/jornada` — jornada semanal e capacidade real.

## Regras de identidade

O usuário continua sendo cliente por padrão no IDDUN. O contexto profissional é uma camada separada.

O profissional só pode operar reservas, horários, clientes, métricas e jornada vinculados ao próprio `ProfessionalProfile`.

## Painel

O painel usa dados reais para:

- agenda do dia;
- próximo atendimento;
- receita prevista do dia;
- horários publicados e livres;
- bloqueio e liberação manual de horário;
- conclusão de atendimento;
- no-show;
- cancelamento;
- sinalização automática de IDDUN Now;
- resumo de CRM;
- resumo financeiro;
- ocupação quando existe jornada configurada.

Remarcação completa não faz parte da V1.

## CRM

A base de clientes é derivada de reservas reais do profissional.

Classificação:

- primeiro agendamento — ainda sem atendimento concluído;
- nova — um atendimento concluído;
- recorrente — dois ou mais atendimentos concluídos.

Oportunidade de retorno só existe quando o último serviço concluído possui `recommended_return_days` configurado e não existe nova reserva confirmada.

Não existe prazo global de manutenção inventado pelo sistema.

O WhatsApp usa mensagem sugerida e exige ação do profissional. A V1 não dispara mensagens automaticamente.

Dados clínicos, alergias e outros dados sensíveis não fazem parte desta camada de CRM.

## Insights

Receita realizada:

`soma(price_at_booking) de bookings COMPLETED no período`

Receita prevista:

`soma(price_at_booking) de bookings CONFIRMED futuros dentro do período`

Ticket médio:

`receita realizada / atendimentos concluídos`

Taxa de cancelamento:

`CANCELLED / (COMPLETED + CANCELLED + NO_SHOW)`

Taxa de no-show:

`NO_SHOW / (COMPLETED + CANCELLED + NO_SHOW)`

As comparações mensais usam o período anterior equivalente.

## Jornada e ocupação

A V1 possui uma janela recorrente de trabalho por dia da semana e uma pausa recorrente opcional.

Dia sem regra = folga recorrente.

Capacidade:

`minutos da jornada - minutos da pausa`

Estados que consomem capacidade:

- `CONFIRMED`;
- `COMPLETED`;
- `NO_SHOW`.

`CANCELLED` não consome capacidade.

Reservas são recortadas aos limites da jornada. Uma reserva fora da jornada não aumenta artificialmente a ocupação. Intervalos sobrepostos são unidos para impedir ocupação acima de 100%.

Sem jornada configurada, ocupação é exibida como não calculada. Não existe fallback fictício de 8 horas por dia.

## Acessibilidade e mobile

As quatro telas Pro compartilham:

- navegação mobile com Hoje, Agenda, Clientes, Insights e Jornada;
- item atual marcado com `aria-current="page"`;
- skip link para o conteúdo principal;
- alvo principal focável;
- foco visível;
- áreas de toque reforçadas em telas pequenas;
- suporte a `prefers-reduced-motion` no shell principal.

## Performance

Consultas de CRM, Insights e Capacidade usam eager loading das relações de Booking necessárias para evitar N+1 conforme a base cresce.

## Fora da V1

Itens intencionalmente adiados:

- remarcação completa;
- férias e folgas por data;
- múltiplas janelas de jornada no mesmo dia;
- capacidade por cadeira, sala ou recurso;
- campanhas automáticas;
- LTV;
- custos, despesas e lucro líquido;
- repasses e comissões;
- metas de ocupação;
- previsão por IA.

Esses itens são evolução pós-V1 e não bloqueiam o fechamento do Pro Dashboard.
