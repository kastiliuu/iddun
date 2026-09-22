# Upgrade — Sprint 8.1.1 QA Hotfix

Partindo da Sprint 8.1.

## 1. Preserve o ambiente

Faça backup do banco e mantenha o `.env` do ambiente. Não copie credenciais do pacote de desenvolvimento para produção.

## 2. Aplique a migration

```powershell
flask --app run.py db upgrade
```

Head esperado:

```text
a91c5e7d3b20
```

## 3. Rode a regressão

```powershell
pytest -q
```

Referência desta entrega: `54 passed`.

## Limpeza opcional dos dados

Para deixar o banco sem contas ou registros, preservando toda a estrutura:

```powershell
flask --app run.py reset-data --dry-run
flask --app run.py reset-data
```

Consulte `DATABASE_RESET.md` antes de executar em produção.

## QA recomendado

1. Convidar um profissional no dashboard Business.
2. Confirmar que ele permanece pendente e não aparece na página pública.
3. Entrar na conta profissional e recusar um convite.
4. Reenviar o convite pelo Business, depois aceitar.
5. Confirmar que o profissional passa a aparecer na equipe pública.
6. Ajustar enquadramento de avatar/capa/logo e salvar.
7. Validar portfólio e galeria em 320, 360, 375, 390 e 430 px.
8. Validar Home e perfis em 1366, 1440 e 1920 px.
9. Confirmar Tatuagem na Home e no filtro de experiências.
10. Confirmar WhatsApp com a mesma geometria visual dos CTAs vizinhos.

## Rollback técnico

```powershell
flask --app run.py db downgrade f8a14d6c2e31
```

O rollback remove somente os novos pontos focais. Faça backup antes de qualquer downgrade.
