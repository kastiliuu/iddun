#!/usr/bin/env node
/**
 * CONV-02.6: block newly introduced GHSA advisories without claiming that
 * already-triaged upstream vulnerabilities are resolved.
 * Known baseline: workflow #656, 2026-10-21 (PR #150).
 */
const fs = require("node:fs");

const KNOWN_ADVISORIES = new Set([
  "GHSA-vfj7-8cjw-p6xm", // braces: no upstream fix as of baseline
  "GHSA-86w9-cpqp-85rv", // node-forge: no upstream fix as of baseline
  "GHSA-vcc3-ghjq-m6fr", // decode-uri-component
]);

function readAudit(path) {
  const json = JSON.parse(fs.readFileSync(path, "utf8"));
  if (!json.vulnerabilities || !json.metadata?.vulnerabilities) {
    throw new Error("npm audit JSON is missing required vulnerability data");
  }
  return json;
}

function collectRootAdvisories(report) {
  const advisories = new Set();
  for (const [name, vulnerability] of Object.entries(report.vulnerabilities)) {
    if (!["moderate", "high", "critical"].includes(vulnerability.severity)) continue;
    for (const via of vulnerability.via || []) {
      if (typeof via === "string") continue; // inherited vulnerability
      if (!via.url || !via.url.includes("/advisories/GHSA-")) {
        throw new Error("Unidentified advisory in " + name + ": " + JSON.stringify(via));
      }
      const match = via.url.match(/GHSA-[a-z0-9-]+/);
      if (!match) throw new Error("Malformed GHSA reference in " + name);
      advisories.add(match[0]);
    }
  }
  return advisories;
}

const path = process.argv[2] || "npm-audit-production.json";
try {
  const data = readAudit(path);
  const counts = data.metadata.vulnerabilities;
  const found = collectRootAdvisories(data);
  const unknown = [...found].filter(id => !KNOWN_ADVISORIES.has(id));
  const summary = [
    "## NPM advisory regression gate",
    "- Critical: " + (counts.critical || 0),
    "- Known GHSA: " + [...found].filter(id => KNOWN_ADVISORIES.has(id)).join(", "),
    "- NEW GHSA: " + (unknown.join(", ") || "none"),
    "- Existing findings remain open; this gate does NOT waive them.",
  ].join("\n");
  console.log(summary);
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary + "\n");
  if (counts.critical > 0 || unknown.length > 0) process.exitCode = 1;
} catch (error) {
  console.error("npm advisory gate INCONCLUSIVE, failing closed:", error.message);
  process.exitCode = 1;
}
