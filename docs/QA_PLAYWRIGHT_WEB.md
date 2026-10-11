# QA-01 — E2E Web com Playwright

## Primeira camada
O workflow `Qualidade IDDUN` executa Chromium em uma instância Flask temporária, com SQLite de CI atualizado pelas migrations Alembic. O navegador verifica:
- Home pública → descoberta;
- login inválido não autentica e apresenta mensagem de erro;
- navegação login → cadastro → login.

## Execução
No CI o job `Chromium / Playwright Web E2E` instala `pytest-playwright`, Chromium e suas dependências Linux, migra a base SQLite isolada e sobe Flask apenas em `127.0.0.1:8765`. Capturas de falha são anexadas como artifact `iddun-web-e2e-evidence`.

Para reproduzir localmente: instale `pytest-playwright` e `python -m playwright install chromium`, prepare um banco local de **teste** com migrations, suba Flask em `127.0.0.1:8765` e rode:
```bash
python -m pytest e2e -q --browser chromium --base-url http://127.0.0.1:8765 --screenshot only-on-failure
```

## Limites e expansão
Os primeiros casos são *smoke E2E* e não provam fluxos completos de reserva ou de onboarding. A próxima evolução deve criar dados de teste descartáveis, executar login válido e o fluxo completo Cliente → reserva → Pro, além de reproduzir no Chromium um gestor Business e as proteções de autorização. Não usar Render compartilhado ou produção como destino dos testes mutáveis.

## Fase seguinte — autenticação real e isolamento
- O CI executa `python -m e2e.seed_client` após as migrations e antes do servidor iniciar.
- O seed recusa qualquer execução sem `IDDUN_E2E_SEED=1`, `APP_ENV=development` e URL exatamente `sqlite:////tmp/iddun-web-e2e.db`. Não usar em Render ou banco persistente.
- Os testes acessam a interface real de login, conferem chegada ao Feed, navegação para Minhas Reservas e retorno à página autenticada.
- Outro teste, em contexto de navegador limpo, confirma que `/feed` exige login.
- **Não é ainda E2E de agendamento completo**: a próxima etapa precisa semear serviço/slot válido em base descartável, respeitando antecedência, disponibilidade e aprovação.
