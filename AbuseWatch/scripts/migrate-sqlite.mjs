import { mkdir, readFile } from "node:fs/promises"
import { dirname, resolve } from "node:path"
import { DatabaseSync } from "node:sqlite"

const dbFlagIndex = process.argv.indexOf("--db")
const defaultDbPath = "data/abuse-tracker.sqlite"
const dbPath = resolve(
  dbFlagIndex >= 0 ? (process.argv[dbFlagIndex + 1] ?? defaultDbPath) : defaultDbPath,
)
const migrationPath = resolve("db/migrations/001_initial.sql")

await mkdir(dirname(dbPath), { recursive: true })

const migrationSql = await readFile(migrationPath, "utf8")
const database = new DatabaseSync(dbPath)
database.exec(migrationSql)
database.close()

console.log(
  JSON.stringify(
    {
      ok: true,
      dbPath,
      migrations: [migrationPath],
    },
    null,
    2,
  ),
)
