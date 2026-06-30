import type { EvidenceCluster, EvidenceRecord, ReviewRecord, SitePublicHandle } from "./contracts"

export type ReportPackage = {
  readonly markdown: string
  readonly csv: string
  readonly html: string
}

export function buildReportPackage(input: {
  readonly evidence: readonly EvidenceRecord[]
  readonly handles: readonly SitePublicHandle[]
  readonly clusters: readonly EvidenceCluster[]
  readonly reviews: readonly ReviewRecord[]
}): ReportPackage {
  const approvedEvidenceIds = new Set(
    input.reviews
      .filter((review) => review.decision === "approved")
      .map((review) => review.evidenceId),
  )
  const approvedEvidence = input.evidence.filter((record) => approvedEvidenceIds.has(record.id))
  const confirmedClusters = input.clusters.filter(
    (cluster) => cluster.kind === "exact_duplicate" && cluster.reviewerConfirmed,
  )
  const suggestions = input.clusters.filter(
    (cluster) => cluster.kind === "near_duplicate_suggestion",
  )

  return {
    markdown: buildMarkdown(approvedEvidence, input.handles, confirmedClusters, suggestions),
    csv: buildCsv(approvedEvidence, input.handles),
    html: buildHtml(approvedEvidence, confirmedClusters, suggestions),
  }
}

export function safeCsvCell(input: string): string {
  const protectedInput = /^[=+\-@]/u.test(input) ? `'${input}` : input
  return `"${protectedInput.replace(/"/gu, '""')}"`
}

function buildMarkdown(
  evidence: readonly EvidenceRecord[],
  handles: readonly SitePublicHandle[],
  clusters: readonly EvidenceCluster[],
  suggestions: readonly EvidenceCluster[],
): string {
  const evidenceSections = evidence
    .map((record) => {
      const handle = handles.find((item) => item.evidenceIds.includes(record.id))
      return [
        `### 증거 ${escapeMarkdown(record.id)}`,
        `- 출처 URL: ${escapeMarkdown(record.sourceUrl)}`,
        `- 사이트별 공개 핸들: ${escapeMarkdown(handle?.publicHandle ?? "미확인")}`,
        `- 캡처 해시: ${record.captureHash}`,
        "",
        "```text",
        record.originalText.replace(/```/gu, "'''"),
        "```",
      ].join("\n")
    })
    .join("\n\n")

  return [
    "# 검토된 신고 패키지",
    "",
    "이 패키지는 사람이 검토한 뒤 직접 제출하기 위한 자료입니다.",
    "",
    "## 확인된 동일 문구 묶음",
    clusters.map((cluster) => `- ${cluster.id}: ${cluster.evidenceIds.join(", ")}`).join("\n") ||
      "- 없음",
    "",
    "## 검토가 필요한 유사 문구 후보",
    suggestions.map((cluster) => `- ${cluster.id}: score ${cluster.score.toFixed(2)}`).join("\n") ||
      "- 없음",
    "",
    "## 증거",
    evidenceSections || "승인된 증거가 없습니다.",
  ].join("\n")
}

function buildCsv(
  evidence: readonly EvidenceRecord[],
  handles: readonly SitePublicHandle[],
): string {
  const header = ["출처_URL", "공개_핸들", "원문_댓글", "캡처_해시"].map(safeCsvCell)
  const rows = evidence.map((record) => {
    const handle = handles.find((item) => item.evidenceIds.includes(record.id))
    return [
      safeCsvCell(record.sourceUrl),
      safeCsvCell(handle?.publicHandle ?? "unknown"),
      safeCsvCell(record.originalText),
      safeCsvCell(record.captureHash),
    ].join(",")
  })
  return [header.join(","), ...rows].join("\r\n")
}

function buildHtml(
  evidence: readonly EvidenceRecord[],
  clusters: readonly EvidenceCluster[],
  suggestions: readonly EvidenceCluster[],
): string {
  return `<!doctype html><html lang="ko"><meta charset="utf-8"><title>검토된 신고 패키지</title><body><main><h1>검토된 신고 패키지</h1><p>사람이 검토한 뒤 직접 제출하기 위한 자료입니다.</p><h2>확인된 동일 문구 묶음</h2><p>${clusters.length}</p><h2>검토가 필요한 유사 문구 후보</h2><p>${suggestions.length}</p><h2>승인된 증거</h2><p>${evidence.length}</p></main></body></html>`
}

function escapeMarkdown(input: string): string {
  return Array.from(input.replace(/[|\\]/gu, "\\$&"))
    .map((character) => {
      const code = character.charCodeAt(0)
      return code < 32 || code === 127 ? " " : character
    })
    .join("")
}
