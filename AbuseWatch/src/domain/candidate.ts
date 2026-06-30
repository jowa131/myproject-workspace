import type { CandidateUrl, KeywordTarget } from "./contracts"
import { parseCandidateUrl, parseKeywordTarget } from "./contracts"

export type CandidateInput = {
  readonly targetId: string
  readonly source: string
  readonly query: string
  readonly url: string
  readonly title: string
  readonly discoveryMethod: "manual" | "official_search" | "import_stub"
  readonly createdAt: string
}

export type CandidateResult =
  | { readonly ok: true; readonly candidate: CandidateUrl }
  | { readonly ok: false; readonly reason: string }

const forbiddenCommentPath = /\/(comment|Comment)(\/|$)/u

export function createKeywordTarget(
  label: string,
  keywordText: string,
  createdAt: string,
): KeywordTarget {
  const keywords = keywordText
    .split(",")
    .map((keyword) => keyword.trim())
    .filter((keyword) => keyword.length > 0)

  return parseKeywordTarget({
    id: `target-${stableId(label, createdAt)}`,
    kind: "topic",
    label: label.trim(),
    keywords,
    createdAt,
  })
}

export function createCandidateUrl(input: CandidateInput): CandidateResult {
  const parsedUrl = safeUrl(input.url)
  if (parsedUrl === null) {
    return { ok: false, reason: "후보 URL은 공개 웹 주소여야 합니다." }
  }

  if (forbiddenCommentPath.test(parsedUrl.pathname)) {
    return { ok: false, reason: "댓글 전용 주소는 후보 URL로 받을 수 없습니다." }
  }

  const candidate = parseCandidateUrl({
    id: `candidate-${stableId(input.url, input.createdAt)}`,
    targetId: input.targetId,
    source: input.source.trim(),
    query: input.query.trim(),
    url: parsedUrl.toString(),
    title: input.title.trim(),
    discoveryMethod: input.discoveryMethod,
    robotsSafetyNote:
      "후보 URL만 저장합니다. 앱은 댓글 본문을 가져오거나 다음 페이지를 스스로 열지 않습니다.",
    status: "queued",
    createdAt: input.createdAt,
  })

  return { ok: true, candidate }
}

export function officialSearchEnabled(apiKey: string | undefined): boolean {
  return apiKey !== undefined && apiKey.trim().length > 0
}

function safeUrl(input: string): URL | null {
  try {
    const url = new URL(input)
    if (url.protocol !== "https:" && url.protocol !== "http:") {
      return null
    }
    return url
  } catch {
    return null
  }
}

function stableId(value: string, salt: string): string {
  return `${value}-${salt}`
    .replace(/[^a-z0-9]+/giu, "-")
    .replace(/^-|-$/gu, "")
    .slice(0, 48)
}
