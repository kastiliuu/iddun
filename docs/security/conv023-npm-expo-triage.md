# CONV-02.3 — Triagem de vulnerabilidades npm/Expo

## Proveniência e alcance

- Baseline: `main@8fa86cc2b18992f607434ff6143cf546b3d1d14e`, depois do merge do PR #148.
- Evidência: [workflow IDDUN #653](https://github.com/kastiliuu/iddun/actions/runs/39658136585), artifact `iddun-mobile-npm-audit` (JSON full e production).
- Ferramenta: `npm audit --json` e `npm audit --omit=dev --json`, Node 22 no GitHub Actions.
- Totais **em ambos os modos**: 23 entradas no mapa de vulnerabilidades npm, sendo 1 critical, 19 high, 3 moderate, 0 low.
- Interpretar `--omit=dev` corretamente: ele não equivale a comprovar explorabilidade no binário iOS/Android. Ferramentas de build e CLI podem aparecer na árvore de dependências declaradas para produção.
- O CI verde do #148 significa **coleta executada**, não significa ausência de CVEs. O scanner npm ainda é consultivo.

## Achados e caminhos de ação

| Pacote afetado | Severidade npm | Dependência direta? | Direção |
| --- | --- | --- | --- |
| `shell-quote` | **critical** | Não | Corrigir primeiro. Advisory [GHSA-pqg4-j6r4-53mv](https://github.com/advisories/GHSA-pqg4-j6r4-53mv). Faixa afetada `>=1.8.4 <1.11.0`; `fixAvailable: true`. Examinar origem da dependência e atualizar para versão não vulnerável por via compatível; validar install + toolchain e repetir audit. |
| `node-forge` | high | Não | Advisory [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv); transita pelo sistema de certificados do Expo. Verificar versão resolvida, patch e impacto em signing/CLI, sem downgrade do Expo. |
| `braces`, `micromatch`, `metro-file-map` | high | Não | Cadeia de tooling/Metro. Inspecionar versões e caminho da dependência, avaliar correção transitiva compatível. |
| `metro`, `metro-config`, `metro-transform-worker` | high | Não | Revisar cadeia Metro e vulnerabilidades subjacentes; `metro-transform-worker` aparece em mais de um caminho; evitar mudança direta sem garantir compatibilidade RN/Expo. |
| `@expo/cli`, `@expo/code-signing-certificates`, `@expo/metro`, `@expo/metro-config` | high | Não | Reflexos de avisos transitivos; tratar causas-raiz antes de atualizar SDK. |
| `expo` | high | Sim | Herda alertas do CLI/Metro; `npm audit fix` sugere `expo@44.0.6` (**downgrade incompatível** com SDK 57). **Não executar --force**. |
| `react-native`, `@react-native/community-cli-plugin`, `@react-native/metro-config`, `@react-native/virtualized-lists` | high | RN direto | Heranças de Metro; o audit sugere `react-native@0.72.17`, incompatível com o baseline 0.86.3. Não aplicar downgrade automático. |
| `react-native-reanimated`, `react-native-worklets`, `@gorhom/bottom-sheet` | high | Diretas | Revisar árvore e aconselhamento de versões; sugeridas pelo npm algumas versões antigas/major. Validar matriz Expo 57, Gesture Handler, Reanimated e Worklets em build nativo. |
| `expo-router`, `query-string`, `decode-uri-component` | moderate | Router direto | Investigar patch de query-string/decode-uri-component; npm sugere `expo-router@58.0.24`, potencialmente fora do SDK 57. |

**Nota:** esta tabela reúne e agrupa as 23 entradas do JSON, que incluem efeitos transitivos em vários pais. Não representa 23 CVEs independentes nem prova 23 explorações possíveis.

## Plano de remediação testável

1. **Critical shell-quote (próximo PR de código):** obter árvore `npm ls shell-quote`, verificar versão vulnerável e solução compatível; modificar `package-lock.json` por npm real (jamais editar integridade SHA manualmente). Rodar `npm ci`, `npx expo install --check`, `npm run typecheck`, `npm run lint`, novo `npm audit`. Conferir que critical passou de 1 para 0 sem aumento nas demais severidades. Se update transitivo exigir override, justificar e testar.
2. **High patch-only:** analisar node-forge, braces, micromatch e seus pais; preferir patches sem mudança de Expo SDK.
3. **High estrutural:** revisar o conjunto Expo/Metro/React Native/Reanimated/Worklets. Não usar `npm audit fix --force` nem aceitar recomendações de downgrade como se fossem patches.
4. **Moderate/router:** avaliar patches dentro do SDK, fixar versão e rodar testes de rotas e deep linking.
5. **Gate final:** só converter npm audit em bloqueante após estabilizar dependências, registrar exceções específicas com evidência e considerar riscos por ambiente/tooling. Não reduzir severidade por mera conveniência.

## Critérios de aceite de cada correção

- Diff mínimo e versões justificadas por advisory + compatibilidade do Expo.
- `package.json` e `package-lock.json` íntegros; `npm ci` reprodutível.
- Expo dependency check, TypeScript e ESLint verdes.
- Testar fluxo de início, navegação e, quando muda pacote nativo, build de desenvolvimento iOS/Android.
- Comparar auditoria **antes/depois** em JSON; não afirmar vulnerabilidade eliminada se persistir.
- Registrar riscos e limitações na descrição de PR. Merge permanece com o proprietário.

## Fora deste PR

Este PR é triagem rastreável e não altera dependências, runtimes, migrations, telas ou política de CI. A vulnerabilidade crítica permanece aberta até uma correção validada.