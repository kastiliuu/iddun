const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createServer } = require("node:http");
const { lanAddresses, selectLanIp, verifyHealth } = require("./start-local.cjs");

const interfaces = {
  WiFi: [{ family: "IPv4", internal: false, address: "192.168.0.8" }],
  loopback: [{ family: "IPv4", internal: true, address: "127.0.0.1" }],
};

test("seleciona o único IPv4 privado não interno", () => {
  assert.deepEqual(lanAddresses(interfaces), ["192.168.0.8"]);
  assert.equal(selectLanIp(interfaces), "192.168.0.8");
});

test("exige seleção explícita se há redes múltiplas", () => {
  const multiple = {
    ...interfaces,
    virtual: [{ family: "IPv4", internal: false, address: "172.17.0.1" }],
  };
  assert.throws(() => selectLanIp(multiple), /IDDUN_LAN_IP/);
  assert.equal(selectLanIp(multiple, "192.168.0.8"), "192.168.0.8");
  assert.throws(() => selectLanIp(multiple, "192.168.0.99"), /não pertence/);
  assert.throws(() => selectLanIp(multiple, "999.1.1.1"), /IPv4 válido/);
});

async function withServer(handler, fn) {
  const server = createServer(handler);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    return await fn(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
}

test("health aceita somente JSON status ok e HTTP 2xx", async () => {
  await withServer((req, res) => {
    assert.equal(req.url, "/health");
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ status: "ok" }));
  }, async url => assert.doesNotReject(verifyHealth(url)));
});

test("health recusa HTTP 503, evitando Expo conectado a backend não pronto", async () => {
  await withServer((_req, res) => {
    res.writeHead(503, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "unhealthy" }));
  }, async url => assert.rejects(verifyHealth(url), /HTTP 503/));
});

test("health recusa resposta inválida ou backend desligado", async () => {
  await withServer((_req, res) => res.end("not json"), async url => {
    await assert.rejects(verifyHealth(url), /não JSON/);
  });
  await assert.rejects(verifyHealth("http://127.0.0.1:1"), /não responde/);
});
