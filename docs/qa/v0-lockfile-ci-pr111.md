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


## Correção adicional após falha do check Expo — 16/10/2026

O CI do PR detectou oito versões incompatíveis com o Expo SDK instalado. Foram atualizados **somente** os pacotes apontados pelo `npx expo install --check`:
`@expo/ui ~57.0.25`, `expo ~57.0.30`, `expo-constants ~57.0.22`,
`expo-image-manipulator ~57.0.21`, `expo-linking ~57.0.13`,
`expo-router ~57.0.28`, `expo-splash-screen ~57.0.10`,
`expo-calendar ~57.0.5`.

[GitHub Actions 38927452855](https://github.com/kastiliuu/iddun/actions/runs/38927452855): **success** ao executar, na branch do PR, `npm install --package-lock-only --ignore-scripts --no-audit --no-fund`, `npm ci --no-audit --no-fund` (instalação completa) e `npx expo install --check`. O lockfile gerado pelo npm contém `integrity` verificável para `expo-calendar@57.0.5`. O workflow de escrita foi removido após sua conclusão. Esta seção substitui a situação anterior de lockfile sem `integrity`.

**Pendente:** conferir jobs do workflow principal no commit final (pytest, Playwright, lint, typecheck e migrations); desenvolvimento e testes em aparelhos físicos continuam necessários.
