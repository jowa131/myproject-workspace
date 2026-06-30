import { mkdir, writeFile } from "node:fs/promises"
import { dirname, resolve } from "node:path"
import { buildReportPackage } from "../src/domain/report.ts"
import { demoSeed } from "../src/fixtures/demo.ts"

const outIndex = process.argv.indexOf("--out")
const outBase = resolve(
  outIndex >= 0 ? (process.argv[outIndex + 1] ?? ".omo/evidence/report") : ".omo/evidence/report",
)
const report = buildReportPackage({
  evidence: demoSeed.evidenceRecords,
  handles: demoSeed.publicHandles,
  clusters: demoSeed.clusters,
  reviews: demoSeed.reviewDecisions,
})

await mkdir(dirname(outBase), { recursive: true })
await writeFile(`${outBase}.md`, report.markdown, "utf8")
await writeFile(`${outBase}.csv`, report.csv, "utf8")
await writeFile(`${outBase}.html`, report.html, "utf8")

console.log(
  JSON.stringify(
    {
      ok: true,
      files: [`${outBase}.md`, `${outBase}.csv`, `${outBase}.html`],
    },
    null,
    2,
  ),
)
