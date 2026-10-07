# Deploy do IDDUN no Render

O `render.yaml` atual descreve o ambiente de **desenvolvimento/preview hospedado** do IDDUN.

Ele não representa a infraestrutura definitiva da V1 pública.

## Decisão atual de infraestrutura

Durante o desenvolvimento:

- Web Service Render no plano gratuito.
- PostgreSQL Render no plano gratuito.
- Storage de mídia local (`MEDIA_STORAGE_BACKEND=local`).
- Rate limiting em memória (`RATELIMIT_STORAGE_URI=memory://`).
- Migrações Alembic executadas durante o build.
- Health check em `/health`.
- Deploy automático da branch `main`.

Antes da divulgação pública para clientes e profissionais, a infraestrutura será reavaliada considerando:

- custo total;
- persistência;
- backups;
- confiabilidade;
- disponibilidade;
- tráfego/egress;
- CDN;
- crescimento esperado;
- facilidade operacional.

O projeto não fica acoplado antecipadamente a R2, S3 ou outro fornecedor de object storage.

## Importante: este ambiente não é produção definitiva

O Render Free serve para desenvolvimento, demonstração e preview.

Não tratar o filesystem local deste ambiente como armazenamento permanente de mídia.

O código usa uma abstração de storage. Em desenvolvimento, o backend é local. Antes da V1 pública, um backend persistente poderá ser conectado sem mudar o contrato de mídia salvo no domínio.

O banco gratuito também não deve ser tratado como banco definitivo da plataforma. Backup, retenção e estratégia de recuperação precisam ser definidos antes do release público.

## Primeiro deploy / preview

1. No Render, conecte a conta GitHub.
2. Acesse **New → Blueprint**.
3. Escolha o repositório do IDDUN e mantenha o caminho `render.yaml`.
4. Confirme os recursos gratuitos do ambiente de preview.
5. Aguarde build, migrations e health check ficarem verdes.

## Por que APP_ENV continua como production no preview hospedado?

Embora o ambiente seja operacionalmente um preview, ele é servido publicamente por HTTPS.

Por isso `APP_ENV=production` continua habilitado no Render para manter proteções como cookies `Secure` e exigência de secrets reais.

Isso não significa que o Render Free foi aprovado como infraestrutura definitiva da V1.

## Google Calendar

Depois que a URL `onrender.com` for criada, configure manualmente no Web Service:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI=https://SEU-SUBDOMINIO.onrender.com/integracoes/google/callback`

Cadastre exatamente a mesma URI de callback no Google Cloud Console. Nunca salve esses valores no GitHub.

## Comandos usados pelo Render

```text
Build:  pip install -r requirements.txt && flask --app run:app db upgrade
Start:  gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT run:app
Health: GET /health
```

## Mídia

No preview atual:

```text
MEDIA_STORAGE_BACKEND=local
UPLOAD_FOLDER=/opt/render/project/src/app/static/uploads
```

Esse caminho é temporário. Não existe garantia de persistência para mídia no ambiente gratuito.

Quando a produção pública for definida, comparar object storage e/ou filesystem persistente pelo custo-benefício real naquele momento.

### Backend S3-compatible disponível

O código já aceita um backend persistente compatível com a API S3 sem vincular o IDDUN a um fornecedor específico.

Para ativar:

```text
MEDIA_STORAGE_BACKEND=s3
MEDIA_S3_BUCKET=seu-bucket
MEDIA_S3_REGION=regiao-ou-auto
MEDIA_S3_ENDPOINT_URL=https://endpoint-do-provider
MEDIA_S3_ACCESS_KEY_ID=...
MEDIA_S3_SECRET_ACCESS_KEY=...
MEDIA_S3_PUBLIC_BASE_URL=https://dominio-publico-ou-cdn
```

Regras:

- `MEDIA_S3_BUCKET` e `MEDIA_S3_PUBLIC_BASE_URL` são obrigatórios quando o backend é `s3`;
- `MEDIA_S3_ENDPOINT_URL` é opcional para provedores que usam o endpoint padrão da AWS e necessário para muitos provedores S3-compatible;
- credenciais nunca devem ser salvas no GitHub;
- o banco continua armazenando chaves no formato `uploads/...`, portanto trocar o backend não altera o contrato de domínio;
- o adapter não define ACL pública. A exposição deve ser feita por bucket/CDN conforme a política do provedor;
- a aplicação não faz `HEAD` remoto para cada imagem durante serialização, evitando latência e custo N+1.

Antes de ativar em produção, validar upload, leitura pública, exclusão, CORS/CDN, política de retenção e backup com o provedor escolhido.

## Rate limiting

No preview atual:

```text
RATELIMIT_STORAGE_URI=memory://
```

Isso é suficiente para uma única instância de desenvolvimento.

Caso a produção utilize múltiplas instâncias, o rate limit deverá usar um storage compartilhado compatível, como Redis ou alternativa equivalente.

## Gate para produção pública

Antes de tratar qualquer deploy como produção oficial:

- banco persistente e estratégia de backup aprovados;
- mídia persistente aprovada;
- processo de restore validado;
- secrets revisados;
- observabilidade ativa;
- rate limiting compatível com a topologia;
- política de privacidade e exclusão de conta prontas;
- testes backend/mobile verdes;
- release checklist aprovado.
