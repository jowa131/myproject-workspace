import { describe, expect, it } from "vitest"
import { createCandidateUrl, officialSearchEnabled } from "../src/domain/candidate"

const baseCandidate = {
  targetId: "target-001",
  source: "manual",
  query: "sample",
  url: "https://news.nate.com/view/123",
  title: "Sample article",
  discoveryMethod: "manual" as const,
  createdAt: "2026-06-26T00:00:00.000Z",
}

describe("T3 candidate queue", () => {
  it("stores candidate article URLs without fetching comment bodies", () => {
    // Given: a reviewer supplied article URL.
    const input = baseCandidate

    // When: the candidate queue accepts the URL.
    const result = createCandidateUrl(input)

    // Then: only URL metadata and a no-fetch safety note are stored.
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.candidate.url).toBe("https://news.nate.com/view/123")
      expect(result.candidate.robotsSafetyNote).toContain("댓글 본문을 가져오거나")
    }
  })

  it("rejects direct comment endpoints", () => {
    // Given: a comment endpoint URL.
    const input = { ...baseCandidate, url: "https://news.nate.com/comment/list" }

    // When: the candidate queue validates it.
    const result = createCandidateUrl(input)

    // Then: comment endpoints are blocked.
    expect(result).toEqual({
      ok: false,
      reason: "댓글 전용 주소는 후보 URL로 받을 수 없습니다.",
    })
  })

  it("keeps official search disabled when no API key exists", () => {
    // Given: no configured official search key.
    const apiKey = undefined

    // When: the adapter gate is checked.
    const enabled = officialSearchEnabled(apiKey)

    // Then: the UI must use manual/import-stub mode.
    expect(enabled).toBe(false)
  })
})
