/** Start Expo Go against the Flask instance reachable on the local Wi-Fi. */
const os = require("node:os");
const { spawn } = require("node:child_process");

const DEFAULT_PORT = 5000;

function lanAddresses(interfaces = os.networkInterfaces()) {
  const addresses = new Set();
  for (const entries of Object.values(interfaces)) {
    for (const address of entries || []) {
      if (address.family !== "IPv4" || address.internal) continue;
      if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(address.address)) {
        addresses.add(address.address);
      }
    }
  }
  return [...addresses];
}

function selectLanIp(interfaces, override) {
  const addresses = lanAddresses(interfaces);
  if (override) {
    if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(override) ||
        override.split(".").some(part => Number(part) > 255)) {
      throw new Error("IDDUN_LAN_IP deve ser um endereço IPv4 válido.");
    }
    if (!addresses.includes(override)) {
      throw new Error(`IDDUN_LAN_IP=${override} não pertence a uma interface local. Opções: ${addresses.join(", ") || "nenhuma"}`);
    }
    return override;
  }
  if (addresses.length !== 1) {
    throw new Error(`Informe IDDUN_LAN_IP no PowerShell. Interfaces encontradas: ${addresses.join(", ") || "nenhuma"}`);
  }
  return addresses[0];
}

async function verifyHealth(url, fetchImpl = fetch) {
  let response;
  try {
    response = await fetchImpl(`${url}/health`, { signal: AbortSignal.timeout(5000) });
  } catch (error) {
    throw new Error(`API não responde em ${url}/health. Confira Flask, PostgreSQL, IP e firewall. (${error.name || "erro de rede"})`);
  }
  if (!response.ok) {
    throw new Error(`API em ${url}/health retornou HTTP ${response.status}. Confira Flask e PostgreSQL.`);
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Resposta não JSON em ${url}/health.`);
  }
  if (payload?.status !== "ok") {
    throw new Error(`API em ${url}/health não retornou status ok.`);
  }
}

async function main() {
  const port = Number(process.env.IDDUN_BACKEND_PORT || DEFAULT_PORT);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("IDDUN_BACKEND_PORT precisa ser uma porta TCP entre 1 e 65535.");
  }
  const ip = selectLanIp(os.networkInterfaces(), process.env.IDDUN_LAN_IP?.trim());
  const url = `http://${ip}:${port}`;

  await verifyHealth(`http://127.0.0.1:${port}`);
  await verifyHealth(url);

  console.log(`IDDUN Mobile: backend local verificado em ${url}`);
  console.log("Conecte o iPhone à mesma rede e abra o QR Code no Expo Go.");
  const command = process.platform === "win32" ? "npm.cmd" : "npm";
  const child = spawn(command, ["run", "start", "--", "--clear"], {
    env: { ...process.env, EXPO_PUBLIC_API_URL: url },
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  child.on("error", error => {
    console.error(`Falha ao iniciar Expo: ${error.message}`);
    process.exitCode = 1;
  });
  child.on("exit", (code, signal) => {
    process.exitCode = code === null ? (signal ? 1 : 0) : code;
  });
}

if (require.main === module) {
  main().catch(error => {
    console.error(`[IDDUN Mobile] ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = { lanAddresses, selectLanIp, verifyHealth };
