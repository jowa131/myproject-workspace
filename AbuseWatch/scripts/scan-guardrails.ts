import { readFile, readdir } from "node:fs/promises"
import { join } from "node:path"

const sourceIndex = process.argv.indexOf("--source")
const sourceRoots = collectSourceRoots(process.argv)
const violations: string[] = []

for (const sourceRoot of sourceRoots) {
  for (const filePath of await listFiles(sourceRoot)) {
    const content = await readFile(filePath, "utf8")
    const compact = content.replace(/\s+/gu, " ")
    const automationSearchText = compact.replace(/"?forbiddenAutomation"?\s*:\s*\[[^\]]*\]/giu, "")
    if (
      /\b(fetch|http\.request|https\.request)\s*\(/u.test(compact) &&
      /(nate|naver)\.com/iu.test(compact)
    ) {
      violations.push(`${filePath}: forbidden platform network request`)
    }
    if (
      /\b(XMLHttpRequest|sendBeacon|WebSocket)\b/u.test(compact) &&
      /(nate|naver)\.com/iu.test(compact)
    ) {
      violations.push(`${filePath}: forbidden platform network request`)
    }
    if (
      /\b(autoSubmitReport|bulkReport|captchaBypass|loginAutomation|hiddenEndpoint|chrome\.tabs\.create|chrome\.cookies)\b/u.test(
        automationSearchText,
      ) ||
      /\b(?:captcha|login|rate[-_ ]?limit)\s*[-_ ]?(?:bypass|automation)\b/iu.test(
        automationSearchText,
      )
    ) {
      violations.push(`${filePath}: forbidden automation concept`)
    }
    if (
      /"host_permissions"\s*:\s*\[\s*"(?:<all_urls>|\*:\/\/[^"]+|https?:\/\/[^"]+)"/iu.test(compact)
    ) {
      violations.push(`${filePath}: forbidden extension host permission`)
    }
  }
}

if (violations.length > 0) {
  console.error(violations.join("\n"))
  process.exit(1)
}

console.log("guardrail_scan: ok")

function collectSourceRoots(args: readonly string[]): readonly string[] {
  if (sourceIndex < 0) {
    return ["src"]
  }

  const roots: string[] = []
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === "--source") {
      const root = args[index + 1]
      if (root !== undefined) {
        roots.push(root)
      }
    }
  }

  return roots.length > 0 ? roots : ["src"]
}

async function listFiles(root: string): Promise<readonly string[]> {
  const entries = await readdir(root, { withFileTypes: true })
  const files: string[] = []
  for (const entry of entries) {
    const fullPath = join(root, entry.name)
    if (entry.isDirectory()) {
      files.push(...(await listFiles(fullPath)))
    } else if (
      entry.name !== "scan-guardrails.ts" &&
      /\.(ts|tsx|js|jsx|mjs|json)$/u.test(entry.name)
    ) {
      files.push(fullPath)
    }
  }
  return files
}
