# IDDUN — Limpeza de dados sem remover a estrutura

O comando `reset-data` remove todos os registros das tabelas da aplicação e preserva:

- tabelas e colunas;
- índices e constraints;
- migrations;
- registro atual da `alembic_version`;
- arquivos presentes em `app/static/uploads`.

São removidos usuários, administradores, perfis, profissionais, estabelecimentos, acessos, vínculos, experiências, horários, reservas, avaliações, certificações, integrações de calendário e métricas de contato.

## 1. Conferir o banco alvo

Execute primeiro a simulação:

```powershell
flask --app run.py reset-data --dry-run
```

O comando mostra a URL do banco com a senha escondida, a quantidade total e o número de registros por tabela. Nenhum dado é alterado.

## 2. Fazer a limpeza

Em desenvolvimento:

```powershell
flask --app run.py reset-data
```

Será solicitada uma confirmação antes da exclusão.

Para execução não interativa em um banco de desenvolvimento já conferido:

```powershell
flask --app run.py reset-data --yes
```

## Produção

Quando `APP_ENV=production`, a limpeza é bloqueada por padrão. Depois de confirmar o backup e o alvo exibido pelo `--dry-run`, use:

```powershell
flask --app run.py reset-data --allow-production
```

Ainda será solicitada confirmação interativa. `--yes` só deve ser acrescentado em automações controladas.

## Resultado esperado

```text
Limpeza concluída: N registro(s) removido(s). Tabelas, índices e migrations foram preservados.
```

Depois da limpeza, a primeira conta cadastrada volta a usar o primeiro identificador disponível. Nenhum administrador é preservado: o sistema fica realmente sem contas, como uma instalação nova.

## Arquivos de upload

O comando limpa somente o banco. Imagens e documentos físicos não são apagados automaticamente, evitando exclusão acidental de arquivos fora do banco. Sem os registros, esses arquivos não aparecem no sistema.
