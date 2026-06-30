import { describe, expect, it } from "vitest"
import {
  parseCandidateUrl,
  parseCapturePayload,
  parseEvidenceRecord,
  parseReportPackageRecord,
} from "../src/domain/contracts"
import { PrivateIdentityFieldError, findPrivateIdentityFields } from "../src/domain/safety"
import { demoSeed } from "../src/fixtures/demo"

const validCandidate = {
  id: "candidate-test",
  targetId: "target-test",
  source: "manual",
  query: "article URL",
  url: "https://news.example.test/story/1",
  title: "Story 1",
  discoveryMethod: "manual",
  robotsSafetyNote: "Manual URL entry only. No page fetch.",
  status: "queued",
  createdAt: "2026-06-26T00:00:00.000Z",
}

const validCapture = {
  candidateUrlId: "candidate-test",
  pageUrl: "https://news.example.test/story/1",
  pageTitle: "Story 1",
  selectedText: "Visible text selected by the reviewer.",
  publicHandle: "sitePublicHandle",
  visibleTimestamp: "2026-06-26 09:00",
  domSnippet: "<p>Visible text selected by the reviewer.</p>",
  capturedAt: "2026-06-26T00:01:00.000Z",
}

describe("T2 domain contracts", () => {
  it("parses candidate URLs and capture payloads at the boundary", () => {
    // Given: valid local-first boundary payloads.
    const candidateInput = validCandidate
    const captureInput = validCapture

    // When: the schemas parse the payloads.
    const candidate = parseCandidateUrl(candidateInput)
    const capture = parseCapturePayload(captureInput)

    // Then: public URL evidence fields are retained.
    expect(candidate.url).toBe("https://news.example.test/story/1")
    expect(capture.selectedText).toContain("Visible text")
  })

  it("rejects private identity fields before schema parsing", () => {
    // Given: a payload that tries to include private identity data.
    const unsafeInput = {
      ...validCapture,
      email: "person@example.test",
      nested: {
        ipAddress: "192.0.2.10",
        inferredIdentity: "same person across sites",
      },
    }

    // When: the capture boundary parses the unsafe payload.
    const action = () => parseCapturePayload(unsafeInput)

    // Then: private fields fail parsing explicitly.
    expect(action).toThrow(PrivateIdentityFieldError)
    expect(findPrivateIdentityFields(unsafeInput)).toEqual([
      "email",
      "nested.inferredIdentity",
      "nested.ipAddress",
    ])
  })

  it("parses immutable evidence and report package records", () => {
    // Given: valid immutable evidence and report package inputs.
    const evidenceInput = demoSeed.evidenceRecords[0]
    const reportInput = {
      id: "report-001",
      status: "draft",
      evidenceIds: ["evidence-001"],
      clusterIds: ["cluster-001"],
      createdAt: "2026-06-26T00:10:00.000Z",
    }

    // When: report contracts parse both records.
    const evidence = parseEvidenceRecord(evidenceInput)
    const report = parseReportPackageRecord(reportInput)

    // Then: immutability and reviewed package references are represented.
    expect(evidence.immutable).toBe(true)
    expect(report.evidenceIds).toEqual(["evidence-001"])
  })

  it("ships duplicate, near-duplicate, false-positive, and candidate URL fixtures", () => {
    // Given: the demo seed used by local surface QA.
    const seed = demoSeed

    // When: fixture classes are queried.
    const exactDuplicate = seed.clusters.find((cluster) => cluster.kind === "exact_duplicate")
    const nearDuplicate = seed.clusters.find(
      (cluster) => cluster.kind === "near_duplicate_suggestion",
    )
    const falsePositive = seed.reviewDecisions.find(
      (review) => review.decision === "false_positive",
    )

    // Then: each MVP fixture class is present.
    expect(seed.candidateUrls.length).toBeGreaterThanOrEqual(2)
    expect(exactDuplicate?.reviewerConfirmed).toBe(true)
    expect(nearDuplicate?.reviewerConfirmed).toBe(false)
    expect(falsePositive?.evidenceId).toBe("evidence-004")
  })
})
