# IDDUN — Upgrade Admin V1

## O que esta entrega adiciona

- Painel administrativo em `/admin/`
- Cadastro e edição de profissionais
- Cadastro e edição de estabelecimentos
- Criação e edição de vínculos profissional ↔ estabelecimento
- Cadastro, edição, publicação e pausa de experiências reais
- Nova tabela `experiences`
- Integração gradual dos dados reais do PostgreSQL com Home, Marketplace e Profissionais
- Mocks mantidos apenas como fallback temporário
- CLI para promover um usuário existente a administrador
- Interface Admin responsiva, com navegação inferior estilo app no mobile

## Atualização local

1. Preserve seu `.env` e sua `.venv` atuais.
2. Substitua os arquivos do projeto pelos desta entrega.
3. Ative o ambiente virtual:

```powershell
.venv\Scripts\Activate.ps1
```

4. Garanta dependências:

```powershell
pip install -r requirements.txt
```

5. Aplique a migration:

```powershell
flask --app run.py db upgrade
```

A nova migration é:

```text
f31c9a72d6e4_admin_catalog_v1.py
```

6. Promova sua conta existente para admin:

```powershell
flask --app run.py make-admin SEU_EMAIL
```

7. Rode os testes:

```powershell
pytest -q
```

Resultado esperado nesta entrega:

```text
22 passed
```

8. Inicie o sistema:

```powershell
python run.py
```

9. Acesse:

```text
http://127.0.0.1:5000/admin/
```

## Ordem recomendada no Admin

1. Cadastrar estabelecimento
2. Cadastrar profissional
3. Criar vínculo entre profissional e estabelecimento
4. Criar experiência como rascunho
5. Revisar conteúdo/preço
6. Publicar
7. Conferir `/experiencias` e a Home

## Observação sobre mocks

Os mocks ainda existem de propósito. O catálogo real do PostgreSQL entra primeiro e os mocks completam a interface enquanto a base real ainda é pequena. Conforme cadastrarmos parceiros reais, poderemos remover os mocks sem reescrever as rotas públicas.
