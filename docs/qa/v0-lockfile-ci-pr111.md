# PR #111 — Estabilização do lockfile e CI

Base: `main` após PR #110 (`49f9d1ff`). Regras revisadas no Notion: DEC-ID-195/196 e TC-CLI-RES-034–040.

## Evidências executadas no GitHub Actions

O workflow **temporário e restrito à branch** `Reparar lockfile PR111` executou em dois pushes:

- [Execução 38923342501](https://github.com/kastiliuu/iddun/actions/runs/38923342501): **success**. Passos `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` e `npm ci --ignore-scripts --no-audit --no-fund` concluídos.
- [Execução 38923418760](https://github.com/kastiliuu/iddun/actions/runs/38923418760): **success**, mesmos passos.

A dependência foi reprocessada pelo npm oficial no runner. O lockfile resultante ainda não exibe `integrity` no bloco `expo-calendar`; **a ausência desse campo isoladamente não prova falha de instalação**, porque as duas instalações concluíram com sucesso. O hash nunca foi inventado manualmente.

O workflow temporário com permissão `contents: write` foi **removido da branch** após o reparo.

## Proteções permanentes

No CI padrão de qualidade mobile, depois do `npm ci`, foram incluídos:
- `npx expo install --check` (compatibilidade de dependências com Expo SDK).
- `npm ls expo-calendar --depth=0` (instalação esperada).

As jobs já existentes continuam executando TypeScript, ESLint, pytest com cobertura XML, migrações, Playwright e concorrência PostgreSQL.

## Validações que ainda dependem do PR e de dispositivo

As execuções acima **não equivalem** a `npm ci` normal com scripts, lint, typecheck, pytest ou device build; verificar os checks normais que iniciarão ao abrir o PR e registrar resultado antes do merge.

Também continuam pendentes os testes em iOS/Android development build: permissões, sincronização e cancelamento do calendário, acessibilidade VoiceOver/TalkBack e reconciliação em falhas de persistência local.

Nenhuma funcionalidade de produto foi adicionada.
