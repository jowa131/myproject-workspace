import { describe, expect, it } from "vitest"
import {
  createEvidenceBatchFromCaptureBatch,
  createEvidenceFromCapture,
  parseSafeCaptureBatchPayload,
  parseSafeCapturePayload,
} from "../src/domain/capture"
import { buildEvidenceClusters, jaccardScore } from "../src/domain/cluster"
import { normalizeEvidenceText } from "../src/domain/normalize"
import { demoSeed } from "../src/fixtures/demo"

const safePayload = {
  candidateUrlId: "candidate-001",
  pageUrl: "https://news.example.test/article/alpha",
  pageTitle: "Demo",
  selectedText: "같은 댓글입니다 같은 댓글입니다 같은 댓글입니다 같은 댓글입니다 repeated phrase",
  publicHandle: "publicHandleA",
  visibleTimestamp: "2026-06-26 09:00",
  domSnippet:
    '<article data-abusewatch-comment="true"><p>같은 댓글입니다 같은 댓글입니다 같은 댓글입니다 같은 댓글입니다 repeated phrase</p></article>',
  capturedAt: "2026-06-26T00:00:00.000Z",
}

describe("T4 capture and clustering", () => {
  it("accepts selected comment-container captures and hashes immutable evidence", async () => {
    // Given: a safe selected/comment-container capture payload.
    const parsed = parseSafeCapturePayload(safePayload)

    // When: evidence is created.
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }
    const evidence = await createEvidenceFromCapture(parsed.payload, "evidence-safe")

    // Then: original text is preserved and hashes are SHA-256 shaped.
    expect(evidence.originalText).toBe(safePayload.selectedText)
    expect(evidence.captureHash).toMatch(/^[a-f0-9]{64}$/u)
    expect(evidence.immutable).toBe(true)
  })

  it("rejects unsafe account chrome and private identity content", () => {
    // Given: a capture containing form chrome and private identifiers.
    const unsafePayload = {
      ...safePayload,
      selectedText: "Contact person@example.test at 010-1234-5678",
      domSnippet: '<form data-account-chrome="true"><input type="hidden" value="secret"></form>',
    }

    // When: the capture boundary parses it.
    const parsed = parseSafeCapturePayload(unsafePayload)

    // Then: unsafe content is rejected before storage.
    expect(parsed).toEqual({
      ok: false,
      reason: "캡처 내용에 개인정보 또는 계정 화면 요소가 포함되어 있습니다.",
    })
  })

  it("accepts normal visible timestamp markup in a safe comment capture", () => {
    // Given: a visible comment includes ordinary timestamp markup.
    const timestampPayload = {
      ...safePayload,
      visibleTimestamp: "2026-06-27 01:20",
      domSnippet:
        '<article data-abusewatch-comment="true"><time>2026-06-27 01:20</time><p>보이는 댓글입니다</p></article>',
    }

    // When: the capture boundary parses it.
    const parsed = parseSafeCapturePayload(timestampPayload)

    // Then: date/time text is not treated as a phone number.
    expect(parsed.ok).toBe(true)
  })

  it("rejects hidden marked comment DOM even when it has the capture marker", () => {
    // Given: a marked comment came from hidden DOM.
    const hiddenPayload = {
      ...safePayload,
      domSnippet:
        '<article data-abusewatch-comment="true" hidden><p>숨겨진 댓글은 저장하면 안 됩니다</p></article>',
    }

    // When: the capture boundary parses it.
    const parsed = parseSafeCapturePayload(hiddenPayload)

    // Then: hidden DOM is rejected before storage.
    expect(parsed).toEqual({
      ok: false,
      reason: "화면에 보이지 않는 댓글 DOM은 캡처할 수 없습니다.",
    })
  })

  it("accepts a user-triggered visible batch and creates one evidence per comment", async () => {
    // Given: a single user action produced two visible comment payloads from the opened page.
    const batch = {
      captures: [
        safePayload,
        {
          ...safePayload,
          selectedText: "두 번째 보이는 댓글입니다 repeated phrase for batch capture",
          publicHandle: "publicHandleB",
          domSnippet:
            '<article data-abusewatch-comment="true"><p>두 번째 보이는 댓글입니다 repeated phrase for batch capture</p></article>',
        },
      ],
    }

    // When: the batch crosses the app boundary and becomes evidence records.
    const parsed = parseSafeCaptureBatchPayload(batch)
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }
    const evidence = await createEvidenceBatchFromCaptureBatch(parsed.payload, "evidence-batch")

    // Then: every visible comment is stored as an immutable evidence record.
    expect(evidence).toHaveLength(2)
    expect(evidence.map((record) => record.id)).toEqual([
      "evidence-batch-001",
      "evidence-batch-002",
    ])
    expect(evidence.map((record) => record.originalText)).toEqual([
      safePayload.selectedText,
      "두 번째 보이는 댓글입니다 repeated phrase for batch capture",
    ])
  })

  it("rejects the whole visible batch when one comment is unsafe", () => {
    // Given: the second visible comment includes private contact information.
    const batch = {
      captures: [
        safePayload,
        {
          ...safePayload,
          selectedText: "Contact person@example.test",
          domSnippet:
            '<article data-abusewatch-comment="true"><p>Contact person@example.test</p></article>',
        },
      ],
    }

    // When: the batch crosses the safe capture boundary.
    const parsed = parseSafeCaptureBatchPayload(batch)

    // Then: the batch is rejected as a whole with the unsafe item index.
    expect(parsed).toEqual({
      ok: false,
      reason: "2번째 댓글: 캡처 내용에 개인정보 또는 계정 화면 요소가 포함되어 있습니다.",
    })
  })

  it("normalizes exact duplicates and suggests only long near-duplicates", () => {
    // Given: demo evidence records.
    const records = demoSeed.evidenceRecords

    // When: clusters are built.
    const clusters = buildEvidenceClusters(records)
    const score = jaccardScore(
      "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu".split(" "),
      "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu changed".split(" "),
    )
    const shortScore = jaccardScore(["same", "short"], ["same", "tiny"])

    // Then: exact duplicates cluster, long near duplicates can suggest, short text cannot.
    expect(normalizeEvidenceText("  SAME\u200b   Text  ")).toBe("same text")
    expect(clusters.some((cluster) => cluster.kind === "exact_duplicate")).toBe(true)
    expect(score).toBeGreaterThanOrEqual(0.86)
    expect(shortScore).toBe(0)
  })
})
