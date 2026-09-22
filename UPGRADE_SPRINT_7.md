# Upgrade — Sprint 7

## Sprint

**Sprint 7 — Google Calendar V1 + UI/UX Hardening**

Baseline: checkpoint IDDUN 16/09/2026.

## Instalação

Preserve `.env` e `.venv` da sua máquina.

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app run.py db upgrade
pytest -q
python run.py
```

Resultado esperado da suíte desta entrega:

```text
35 passed
```

## Migration nova

`b7d2f9a1c410_google_calendar_ui_polish_v1.py`

Cria:

- `calendar_connections`

Adiciona:

- `establishments.logo_url`

## Google Calendar

Leia `GOOGLE_CALENDAR_SETUP.md`.

A aplicação funciona normalmente mesmo sem configurar o Google. Nesse caso, a tela da integração mostra o checklist de configuração e as demais funcionalidades continuam disponíveis.

## Refinamentos incluídos

- upload visual de avatar/fotos no lugar de URL manual;
- avatar do cliente também pode ser selecionado por arquivo;
- fuso horário virou select;
- ajuda contextual da antecedência de reserva;
- controle numérico customizado, sem spinner branco nativo;
- `slug` deixa de aparecer como termo técnico para profissional/estabelecimento;
- campo **Seu endereço no IDDUN** com `iddun.com/...`, normalização e verificação de disponibilidade;
- identificação pública globalmente validada entre profissionais e estabelecimentos no backend;
- dashboard de estabelecimento;
- dashboard Admin enriquecido;
- ações Editar/Pausar alinhadas nos cards de experiências;
- botão Cancelar de Nova Oportunidade refeito;
- Home desktop com mais respiro;
- botão nativo de limpar busca ajustado para a paleta IDDUN;
- Google Calendar com OAuth, seleção de agenda, FreeBusy, reconciliação e eventos de reservas;
- comando `sync-calendars` para sincronização programada futura.

## Uploads locais

No desenvolvimento, uploads ficam em `app/static/uploads/`. A pasta é ignorada pelo Git, mantendo apenas `.gitkeep`.

A arquitetura continua pronta para substituir o storage local por Cloudinary/S3-like sem mudar os campos de banco (`avatar_url`, `image_url`, `logo_url`).
