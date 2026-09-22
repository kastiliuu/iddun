# Como aplicar — Core Profiles V1

## 1. Preserve estes itens da sua máquina

Não apague:

- `.env`
- `.venv/`

O ZIP desta entrega não contém nenhum dos dois.

## 2. Substitua o código do projeto

Faça uma cópia da pasta atual e copie o conteúdo desta entrega por cima do `iddun-master`.

## 3. Ative o ambiente

```powershell
.venv\Scripts\Activate.ps1
```

## 4. Sincronize dependências

```powershell
pip install -r requirements.txt
```

## 5. Confira seu `.env`

O mínimo continua sendo:

```env
SECRET_KEY=sua-chave-local
DATABASE_URL=postgresql+psycopg2://iddun_app:SUA_SENHA@localhost:5432/iddun_dev
```

Opcionalmente adicione:

```env
APP_ENV=development
```

## 6. Aplique a migration já incluída

Não rode `db init` e não precisa rodar `db migrate`.

Rode apenas:

```powershell
flask --app run.py db upgrade
```

O banco passará a ter:

- `users`
- `client_profiles`
- `professional_profiles`
- `establishments`
- `professional_establishment_memberships`
- `alembic_version`

O usuário cliente que você já criou recebe `ClientProfile` automaticamente pela migration.

## 7. Testes

```powershell
pytest -q
```

Esperado nesta entrega:

`18 passed`

## 8. Inicie

```powershell
python run.py
```

## 9. Smoke test manual

Teste:

- `/`
- `/experiencias`
- `/profissionais`
- `/para-profissionais`
- `/login`
- `/cadastro`
- `/minha-conta` autenticado
- editar e salvar perfil
- logout e verificar toast desaparecendo sozinho
- mobile 390x844
- mobile 320x608
- desktop 1366x768

