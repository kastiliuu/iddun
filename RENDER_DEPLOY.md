# Deploy do IDDUN no Render

O repositório já contém `render.yaml`, portanto o fluxo recomendado é criar um **Blueprint** no Render conectado à branch `main`.

## Recursos criados

- Web Service Python pago: `iddun-web`.
- PostgreSQL pago: `iddun-db`.
- Disco persistente de 5 GB: `iddun-uploads`.
- Migrações Alembic antes de cada deploy.
- Health check em `/health`.
- Deploy automático em cada commit da branch `main`.

## Primeiro deploy

1. No Render, conecte a conta GitHub em **Account Settings → Git Deployment Credentials**.
2. Acesse **New → Blueprint**.
3. Escolha o repositório do IDDUN e mantenha o caminho `render.yaml`.
4. Revise os custos dos recursos pagos e confirme a criação.
5. Aguarde o build, a migração e o health check ficarem verdes.

## Google Calendar

Depois que a URL `onrender.com` for criada, adicione manualmente no Web Service:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI=https://SEU-SUBDOMINIO.onrender.com/integracoes/google/callback`

Cadastre exatamente a mesma URI de callback no Google Cloud Console. Nunca salve esses valores no GitHub.

## Comandos usados pelo Render

```text
Build:      pip install -r requirements.txt
Pre-deploy: flask --app run:app db upgrade
Start:      gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT run:app
Health:     GET /health
```

## Observação sobre uploads

Arquivos enviados por profissionais e estabelecimentos ficam em `app/static/uploads`, montado como disco persistente. O serviço permanece com uma instância, pois serviços com disco anexado não podem ser escalados horizontalmente.
