# Upgrade — IDDUN Opportunities + Booking V1

Base esperada: Admin V1 (`f31c9a72d6e4`).

## 1. Preserve arquivos locais
Não substitua nem compartilhe:
- `.env`
- `.venv/`

## 2. Instale dependências
Nenhuma dependência nova é exigida além do `requirements.txt` atual, mas rode:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Aplique a migration

```powershell
flask --app run.py db upgrade
```

A migration nova é:

`e4b19c7a2f10_opportunities_booking_v1.py`

Ela adiciona:
- `experience_slots`
- `bookings`
- timezone e cutoff padrão ao profissional
- timezone ao estabelecimento
- cutoff opcional por experiência

## 4. Rode a suíte

```powershell
pytest -q
```

Esperado neste checkpoint: `32 passed`.

## 5. Inicie o IDDUN

```powershell
python run.py
```

## Fluxo de QA recomendado
1. `/admin/experiencias` — tenha uma experiência real publicada.
2. `/admin/oportunidades/nova` — escolha a experiência, uma data futura e horários como `10:00, 14:00, 16:00`.
3. `/admin/oportunidades` — confirme que os slots aparecem como disponíveis.
4. Abra `/experiencias/<slug>` — somente slots disponíveis devem aparecer.
5. Entre como cliente e escolha um horário.
6. O slot entra em `HELD` por 8 minutos.
7. Confirme a reserva.
8. Verifique `/minhas-reservas` e `/admin/reservas`.
9. Em `/admin/oportunidades`, use `Simular Google` somente para QA: o slot deve sair do marketplace sem derrubar os demais.
10. Recalcule a disponibilidade e confirme o retorno do slot caso o cutoff ainda permita.

## Regras já implementadas
- cutoff aplicado no backend, não apenas na interface;
- precedência: cutoff do slot > experiência > padrão do profissional;
- slots: `AVAILABLE`, `HELD`, `BOOKED`, `BLOCKED_EXTERNAL`, `BLOCKED_MANUAL`, `EXPIRED`;
- um conflito externo bloqueia somente o slot afetado;
- hold expira automaticamente;
- dois clientes não conseguem segurar o mesmo slot em sequência;
- um cliente não consegue confirmar duas reservas sobrepostas;
- conflito externo durante hold cancela o pending e bloqueia o slot;
- cancelamento antes do cutoff pode devolver a vaga ao marketplace;
- preço da experiência é fotografado em `price_at_booking`.

## O que ainda NÃO é integração real
O botão `Simular Google` é um gancho de QA. A arquitetura de reconciliação já existe em `calendar_sync_service.py`, mas OAuth/Google Calendar API ainda não foi conectado.

## O que ainda NÃO cobra dinheiro
A confirmação atual é piloto sem cobrança. O modelo de sinal/deposito parcial será implementado somente após estabilizar reserva e calendário.
