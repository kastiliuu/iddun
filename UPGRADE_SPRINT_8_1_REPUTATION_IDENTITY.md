# Upgrade — Sprint 8.1 Reputation & Professional Identity

Partindo da Sprint 8 Platform Foundation.

## 1. Faça backup do banco
Especialmente em ambiente com dados reais.

## 2. Atualize os arquivos do projeto
Use o pacote completo da Sprint 8.1.

## 3. Preserve seu `.env`
O pacote não deve substituir segredos locais/produção.

## 4. Ative o ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

## 5. Aplique a migration

```powershell
flask --app run.py db upgrade
```

Head esperado:

```text
f8a14d6c2e31
```

A migration cria:
- `professional_certifications`
- `reviews`
- `contact_clicks`
- `professional_profiles.whatsapp_enabled`
- `establishments.whatsapp_enabled`

## 6. Rode os testes

```powershell
pytest -q
```

Referência desta entrega: **50 passed**.

## 7. Suba o projeto

```powershell
python run.py
```

## QA recomendado
1. Profissional: editar perfil e habilitar WhatsApp.
2. Abrir perfil público e validar botão/mensagem do WhatsApp.
3. Cadastrar certificado em `/pro/certificacoes`.
4. Validar certificado no perfil público.
5. Marcar uma reserva como concluída no fluxo administrativo.
6. Logar como cliente e abrir `Minhas reservas`.
7. Avaliar profissional e, quando houver, estabelecimento.
8. Confirmar nota/recomendação nas páginas públicas.
9. Confirmar métricas nos dashboards Pro e Business.
10. Repetir QA no mobile, principalmente cards de avaliações e CTAs do Hero de perfil.

## Rollback técnico

```powershell
flask --app run.py db downgrade e7f6a3b92c11
```

Faça rollback somente depois de backup, pois remove reviews, certificados e métricas de contato da Sprint 8.1.
