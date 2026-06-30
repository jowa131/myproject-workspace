import { execFileSync } from "node:child_process"
import { mkdirSync, writeFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

describe("T7 guardrails", () => {
  it("passes the production source guardrail scan", () => {
    // Given: the production source tree.
    const command = ["--experimental-strip-types", "scripts/scan-guardrails.ts", "--source", "src"]

    // When: the guardrail scanner runs.
    const output = execFileSync(process.execPath, command, { encoding: "utf8" })

    // Then: no crawler or auto-reporting patterns are present.
    expect(output).toContain("guardrail_scan: ok")
  })

  it("scans every provided source root", () => {
    // Given: a second source root contains a forbidden platform request.
    const fixtureRoot = join(".tmp", "guardrail-multisource")
    const safeRoot = join(fixtureRoot, "safe")
    const blockedRoot = join(fixtureRoot, "blocked")
    mkdirSync(safeRoot, { recursive: true })
    mkdirSync(blockedRoot, { recursive: true })
    writeFileSync(join(safeRoot, "safe.ts"), "export const marker = 'safe'\\n", "utf8")
    writeFileSync(
      join(blockedRoot, "blocked.ts"),
      "export const blocked = () => fetch('https://news.nate.com/comment/list')\\n",
      "utf8",
    )

    // When: the scanner is given both roots.
    const command = [
      "--experimental-strip-types",
      "scripts/scan-guardrails.ts",
      "--source",
      safeRoot,
      "--source",
      blockedRoot,
    ]

    // Then: the second root is scanned and rejected.
    expect(() => execFileSync(process.execPath, command, { encoding: "utf8" })).toThrow(
      /forbidden platform network request/u,
    )
  })

  it("rejects broad extension host permissions in manifest JSON", () => {
    // Given: a manifest fixture asks for broad remote host access.
    const fixtureRoot = join(".tmp", "guardrail-manifest")
    mkdirSync(fixtureRoot, { recursive: true })
    writeFileSync(
      join(fixtureRoot, "manifest.json"),
      JSON.stringify({
        manifest_version: 3,
        permissions: ["activeTab", "scripting"],
        host_permissions: ["https://*.nate.com/*"],
      }),
      "utf8",
    )

    // When: the scanner is given the manifest source root.
    const command = [
      "--experimental-strip-types",
      "scripts/scan-guardrails.ts",
      "--source",
      fixtureRoot,
    ]

    // Then: broad host permissions are rejected.
    expect(() => execFileSync(process.execPath, command, { encoding: "utf8" })).toThrow(
      /forbidden extension host permission/u,
    )
  })

  it("rejects alternate platform request and browser automation APIs", () => {
    // Given: fixtures contain non-fetch request APIs and tab automation.
    const fixtureRoot = join(".tmp", "guardrail-browser-apis")
    mkdirSync(fixtureRoot, { recursive: true })
    writeFileSync(
      join(fixtureRoot, "blocked.js"),
      [
        "new WebSocket('wss://news.naver.com/comment')",
        "navigator.sendBeacon('https://news.nate.com/comment/list')",
        "chrome.tabs.create({ url: 'https://news.nate.com/view/1' })",
      ].join("\n"),
      "utf8",
    )

    // When: the scanner is given the fixture root.
    const command = [
      "--experimental-strip-types",
      "scripts/scan-guardrails.ts",
      "--source",
      fixtureRoot,
    ]

    // Then: the forbidden request/automation APIs are rejected.
    expect(() => execFileSync(process.execPath, command, { encoding: "utf8" })).toThrow(
      /forbidden/u,
    )
  })
})
