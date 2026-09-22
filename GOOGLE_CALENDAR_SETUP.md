# IDDUN — Google Calendar V1

## Objetivo

A integração conecta um `ProfessionalProfile` a uma agenda Google para:

1. ler períodos ocupados;
2. retirar do marketplace somente os `ExperienceSlot` conflitantes;
3. restaurar slots quando o conflito externo desaparecer e o cutoff ainda permitir;
4. criar um evento Google quando uma reserva IDDUN for confirmada;
5. remover o evento criado pelo IDDUN quando a reserva for cancelada.

O IDDUN continua sendo responsável apenas pelas **Oportunidades IDDUN**. Ele não tenta substituir toda a agenda do profissional.

## Configuração no Google Cloud

1. Crie ou selecione um projeto no Google Cloud.
2. Ative **Google Calendar API**.
3. Em **Google Auth Platform**, configure Branding/Audience/Data Access.
4. Durante desenvolvimento, mantenha o app em modo de teste e adicione as contas Google que poderão conectar como *test users*.
5. Crie um OAuth Client do tipo **Web application**.
6. Adicione como Authorized redirect URI exatamente o mesmo valor usado no `.env`, por exemplo:

   `http://localhost:5000/integracoes/google/callback`

7. Copie Client ID e Client Secret para o `.env`.

## `.env`

```env
GOOGLE_CLIENT_ID=seu-client-id
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5000/integracoes/google/callback
TOKEN_ENCRYPTION_KEY=
```

`TOKEN_ENCRYPTION_KEY` é opcional em desenvolvimento. Quando não for fornecida, o IDDUN deriva a chave a partir da `SECRET_KEY`. Em produção, use uma chave dedicada e estável.

> O Redirect URI precisa ser idêntico no Google Cloud e no `.env`.

## Escopos utilizados

- `calendar.calendarlist.readonly`
- `calendar.events.freebusy`
- `calendar.events`

O objetivo é solicitar somente os acessos necessários para escolher a agenda, consultar disponibilidade e criar/remover eventos de reservas.

## Fluxo no IDDUN

Admin → Profissionais → Editar profissional → **Gerenciar integração**.

Depois:

1. Conectar Google Calendar;
2. autorizar a conta;
3. selecionar a agenda usada pelo profissional;
4. ativar/desativar proteção de conflitos;
5. ativar/desativar criação de eventos de reserva;
6. executar **Sincronizar agora**.

A aplicação também faz uma sincronização oportunística quando:

- novas oportunidades são publicadas;
- uma página de experiência real é aberta e a última sincronização já está antiga.

Para sincronização programada em produção existe o comando:

```powershell
flask --app run.py sync-calendars
```

Esse comando foi pensado para ser acionado futuramente por scheduler/cron do ambiente de produção.

## Observação sobre produção

Enquanto o OAuth estiver em modo de teste, somente usuários adicionados como test users poderão conectar. Antes de abrir a integração para qualquer profissional, revise os requisitos de verificação OAuth do Google.
