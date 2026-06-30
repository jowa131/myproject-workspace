import { execFileSync } from "node:child_process"
import { existsSync } from "node:fs"
import { mkdir, rm } from "node:fs/promises"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

describe("T1 foundation", () => {
  it("creates the SQLite schema when the migration harness runs", async () => {
    // Given: an isolated test database path.
    const dbDir = resolve(".tmp/test-db")
    const dbPath = resolve(dbDir, "foundation.sqlite")
    await rm(dbDir, { force: true, recursive: true })
    await mkdir(dbDir, { recursive: true })

    // When: the local migration harness is invoked.
    const output = execFileSync(process.execPath, ["scripts/migrate-sqlite.mjs", "--db", dbPath], {
      encoding: "utf8",
    })

    // Then: the observable artifact exists and the harness reports success.
    expect(existsSync(dbPath)).toBe(true)
    expect(output).toContain('"ok": true')
    expect(output).toContain("001_initial.sql")
  })

  it("declares the local-only server marker for surface QA", () => {
    // Given: the application shell HTML.
    const indexPath = resolve("index.html")

    // When: the shell is read as the HTTP root served by Vite.
    const html = execFileSync(
      process.execPath,
      ["-e", `console.log(require("fs").readFileSync(${JSON.stringify(indexPath)}, "utf8"))`],
      {
        encoding: "utf8",
      },
    )

    // Then: the marker used by curl/browser evidence is present.
    expect(html).toContain("abusewatch-app-shell")
  })
})
