export function normalizeEvidenceText(input: string): string {
  return input
    .normalize("NFKC")
    .replace(/[^\P{C}\n\t]/gu, "")
    .trim()
    .replace(/\s+/gu, " ")
    .replace(/[A-Z]/g, (letter) => letter.toLowerCase())
}

export function evidenceTokens(input: string): readonly string[] {
  const matches = normalizeEvidenceText(input).match(
    /[\p{Script=Hangul}\p{Alphabetic}\p{Number}]+/gu,
  )
  return matches ?? []
}
