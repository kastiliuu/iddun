// P-002 no app: regras puras do Wizard A (mesmas da Web e do servidor).
// Roda com: node --experimental-strip-types --test scripts/service-wizard.test.mjs
import assert from "node:assert/strict";
import test from "node:test";

import {
  SERVICE_STATUS_LABELS,
  SERVICE_STEPS,
  parseBatchTimes,
  buildPayload,
  firstReachableStep,
  formatMoney,
  parseMoney,
  stepErrors,
  stepForServerError,
} from "../src/services/serviceWizard.ts";

const valid = {
  name: "Mechas",
  category: "cabelo",
  shortDescription: "Mechas com tonalização.",
  description: "",
  regularPrice: "300,00",
  price: "280",
  duration: "150",
  establishmentId: null,
};

test("five steps in the same order as the Web", () => {
  assert.deepEqual(SERVICE_STEPS.map((step) => step.label), [
    "Básico", "Preço e duração", "Local e disponibilidade", "Imagem", "Revisão",
  ]);
});

test("money accepts Brazilian and dotted input and rejects garbage", () => {
  assert.equal(parseMoney("1.200,50"), 1200.5);
  assert.equal(parseMoney("120.5"), 120.5);
  assert.equal(parseMoney("R$ 80"), 80);
  assert.equal(parseMoney(""), null);
  assert.ok(Number.isNaN(parseMoney("12,345")));
  assert.ok(Number.isNaN(parseMoney("-5")));
  assert.equal(formatMoney(280), "R$ 280,00");
});

test("basic step requires name, category and short description within limits", () => {
  const errors = stepErrors(0, { ...valid, name: " ", shortDescription: "x".repeat(221), category: "outra" });
  assert.deepEqual(Object.keys(errors).sort(), ["category", "name", "shortDescription"]);
  assert.deepEqual(stepErrors(0, valid), {});
});

test("price step blocks IDDUN price above the regular price and bad duration", () => {
  const errors = stepErrors(1, { ...valid, price: "320", duration: "5" });
  assert.equal(errors.price, "O preço IDDUN não pode ser maior que o preço regular.");
  assert.ok(errors.duration);
  assert.deepEqual(stepErrors(1, valid), {});
});

test("cannot jump past an invalid step", () => {
  assert.equal(firstReachableStep(4, { ...valid, name: "" }), 0);
  assert.equal(firstReachableStep(4, { ...valid, price: "999" }), 1);
  assert.equal(firstReachableStep(4, valid), 4);
});

test("payload keeps the regular price instead of copying the IDDUN price", () => {
  const payload = buildPayload(valid);
  assert.equal(payload.regularPrice, 300);
  assert.equal(payload.price, 280);
  assert.equal(payload.durationMinutes, 150);
  assert.equal(buildPayload({ ...valid, duration: "" }), null);
});

test("server errors send the person back to the right step", () => {
  assert.equal(stepForServerError("invalid_title"), 0);
  assert.equal(stepForServerError("invalid_price"), 1);
  assert.equal(stepForServerError("establishment_not_allowed"), 2);
  assert.equal(stepForServerError("service_has_slots"), 2);
  assert.equal(stepForServerError("unauthorized"), null);
});

test("status labels follow the model (V1-CONV-D07)", () => {
  assert.equal(SERVICE_STATUS_LABELS.published, "Publicada");
  assert.equal(SERVICE_STATUS_LABELS.paused, "Pausada");
});

test("batch times follow the server parser", () => {
  assert.deepEqual(parseBatchTimes("11:00, 9:00;10:30\n9:00"), { times: ["09:00", "10:30", "11:00"] });
  assert.equal("error" in parseBatchTimes("  ,  "), true);
  assert.match(parseBatchTimes("9h").error, /Horário inválido: 9h/);
  assert.match(parseBatchTimes("24:00").error, /Horário inválido/);
  const many = Array.from({ length: 21 }, (_, i) => `${String(i).padStart(2, "0")}:00`).join(",");
  assert.match(parseBatchTimes(many).error, /no máximo 20/);
});
