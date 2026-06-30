import { demoSeed } from "../src/fixtures/demo.ts"

const formatFlagIndex = process.argv.indexOf("--format")
const format = formatFlagIndex >= 0 ? process.argv[formatFlagIndex + 1] : "json"

if (format !== "json") {
  throw new Error(`Unsupported seed print format: ${format ?? "missing"}`)
}

console.log(JSON.stringify(demoSeed, null, 2))
