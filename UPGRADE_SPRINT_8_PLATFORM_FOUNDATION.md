# Upgrade — Sprint 8 · Platform Foundation

## 1. Faça backup do projeto e banco

Antes da migration, preserve sua versão atual.

## 2. Substitua os arquivos pelo pacote desta sprint

O ZIP entregue já contém o projeto integrado.

O `.env` não deve ser substituído por um arquivo de outra máquina. Preserve o seu `.env` local.

## 3. Ative o ambiente virtual

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## 4. Instale dependências, se necessário

```powershell
pip install -r requirements.txt
```

Não foram adicionadas bibliotecas novas nesta sprint.

## 5. Aplique a migration

```powershell
flask --app run.py db upgrade
```

Migration nova:

```text
e7f6a3b92c11_platform_profiles_foundation.py
```

## 6. Rode os testes

```powershell
pytest -q
```

Resultado validado no pacote:

```text
46 passed
```

## 7. Execute

```powershell
python run.py
```

## Rotas principais para QA

```text
/para-profissionais
/pro/comecar
/pro/onboarding
/pro/painel
/estabelecimentos
/business/onboarding
/profissionais/<slug>
/estabelecimentos/<slug>
```

## Cenário de QA recomendado

1. Crie uma conta comum.
2. Abra `Para profissionais`.
3. Clique `Começar grátis`.
4. Selecione `Atendo como profissional`.
5. Complete o onboarding com 3 fotos de portfólio.
6. Confira o dashboard Pro.
7. Abra `Ver como cliente`.
8. Volte para a conta.
9. Adicione contexto e escolha `Tenho ou represento um estabelecimento`.
10. Complete o Business onboarding.
11. Confira se a mesma conta agora possui Cliente + Pro + Business.
12. No Business, adicione um profissional usando o e-mail de uma conta que já possui IDDUN Pro.
13. Abra a página pública da empresa e navegue Empresa → Profissional.
14. No perfil do profissional, navegue Profissional → Empresa.

## Uploads

Cada imagem aceita JPG, JPEG, PNG ou WEBP e possui limite individual de 5 MB.

O request total está limitado a 30 MB para permitir portfólios sem liberar uploads excessivamente grandes.

## Observação de produto

O vínculo de equipe nesta sprint é propositalmente simples: um gestor informa o e-mail de uma conta IDDUN que já possui perfil profissional e o vínculo é criado.

Antes de produção aberta, a recomendação é trocar isso por fluxo de convite/aceite para impedir vínculo unilateral.
