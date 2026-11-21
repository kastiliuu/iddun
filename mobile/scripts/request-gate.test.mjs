// P-003 · Testes funcionais do versionamento de leituras da lista Expo.
import assert from "node:assert/strict";
import test from "node:test";
import { createLatestRequestGate } from "../src/services/latestRequestGate.ts";

test("retry invalida resultado anterior e mantém apenas o mais recente", async () => {
  const gate = createLatestRequestGate();
  const first = gate.begin();
  let resolveFirst;
  const older = new Promise((resolve) => { resolveFirst = resolve; });
  const latest = gate.begin();
  const visible = [];

  await Promise.resolve("lista atual").then((value) => {
    if (gate.isCurrent(latest)) visible.push(value);
  });
  resolveFirst("lista antiga");
  await older.then((value) => {
    if (gate.isCurrent(first)) visible.push(value);
  });

  assert.deepEqual(visible, ["lista atual"]);
});

test("sair da tela invalida a leitura pendente", () => {
  const gate = createLatestRequestGate();
  const pending = gate.begin();
  gate.invalidate(pending);
  assert.equal(gate.isCurrent(pending), false);
});

test("limpeza de uma leitura antiga não invalida o retry atual", () => {
  const gate = createLatestRequestGate();
  const old = gate.begin();
  const current = gate.begin();
  gate.invalidate(old);
  assert.equal(gate.isCurrent(current), true);
  gate.invalidate(current);
  assert.equal(gate.isCurrent(current), false);
});

test("sair da tela após retry invalida também a leitura nova", () => {
  const gate = createLatestRequestGate();
  gate.begin(); // leitura iniciada ao abrir o catálogo
  const retry = gate.begin(); // usuário tenta novamente
  gate.invalidateAll(); // limpeza do foco deve cancelar ambas
  assert.equal(gate.isCurrent(retry), false);
});
