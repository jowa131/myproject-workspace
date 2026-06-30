import type {
  CandidateUrl,
  CapturePayload,
  EvidenceCluster,
  EvidenceRecord,
  ReviewRecord,
  SitePublicHandle,
} from "../domain/contracts"
import {
  EvidenceClusterSchema,
  EvidenceRecordSchema,
  ReviewRecordSchema,
  SitePublicHandleSchema,
  parseCandidateUrl,
  parseCapturePayload,
} from "../domain/contracts"

const hashes = {
  first: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  second: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  near: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  falsePositive: "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  capture: "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
} as const

export type DemoSeed = {
  readonly candidateUrls: readonly CandidateUrl[]
  readonly capturePayloads: readonly CapturePayload[]
  readonly evidenceRecords: readonly EvidenceRecord[]
  readonly publicHandles: readonly SitePublicHandle[]
  readonly clusters: readonly EvidenceCluster[]
  readonly reviewDecisions: readonly ReviewRecord[]
}

export const demoSeed: DemoSeed = {
  candidateUrls: [
    parseCandidateUrl({
      id: "candidate-001",
      targetId: "target-001",
      source: "manual-demo",
      query: "시연 기사 언급",
      url: "https://news.example.test/article/alpha",
      title: "시연 기사 알파",
      discoveryMethod: "manual",
      robotsSafetyNote: "검토자가 입력한 URL입니다. 댓글을 자동으로 수집하지 않습니다.",
      status: "queued",
      createdAt: "2026-06-26T00:00:00.000Z",
    }),
    parseCandidateUrl({
      id: "candidate-002",
      targetId: "target-001",
      source: "official-search-stub",
      query: "시연 기사 언급",
      url: "https://news.example.test/article/beta",
      title: "시연 기사 베타",
      discoveryMethod: "import_stub",
      robotsSafetyNote: "후보 URL 예시만 저장합니다. 페이지 내용은 가져오지 않습니다.",
      status: "queued",
      createdAt: "2026-06-26T00:01:00.000Z",
    }),
  ],
  capturePayloads: [
    parseCapturePayload({
      candidateUrlId: "candidate-001",
      pageUrl: "https://news.example.test/article/alpha",
      pageTitle: "시연 기사 알파",
      selectedText: "반복 악성 문구 시연용 동일 문장입니다.",
      publicHandle: "공개핸들A",
      visibleTimestamp: "2026-06-26 09:00",
      domSnippet: "<article><p>반복 악성 문구 시연용 동일 문장입니다.</p></article>",
      capturedAt: "2026-06-26T00:02:00.000Z",
      screenshotDataUrlSha256: hashes.capture,
      reviewerNote: "동일 문구 시연 데이터입니다.",
    }),
    parseCapturePayload({
      candidateUrlId: "candidate-002",
      pageUrl: "https://news.example.test/article/beta",
      pageTitle: "시연 기사 베타",
      selectedText: "반복 악성 문구와 거의 같은 시연용 문장입니다",
      publicHandle: "공개핸들B",
      visibleTimestamp: "2026-06-26 09:03",
      domSnippet: "<article><p>반복 악성 문구와 거의 같은 시연용 문장입니다</p></article>",
      capturedAt: "2026-06-26T00:03:00.000Z",
    }),
  ],
  evidenceRecords: [
    EvidenceRecordSchema.parse({
      id: "evidence-001",
      candidateUrlId: "candidate-001",
      kind: "comment_text",
      originalText: "반복 악성 문구 시연용 동일 문장입니다.",
      normalizedTextHash: hashes.first,
      sourceUrl: "https://news.example.test/article/alpha",
      capturedAt: "2026-06-26T00:02:00.000Z",
      captureHash: hashes.capture,
      immutable: true,
      attachments: [],
    }),
    EvidenceRecordSchema.parse({
      id: "evidence-002",
      candidateUrlId: "candidate-001",
      kind: "comment_text",
      originalText: "반복 악성 문구 시연용 동일 문장입니다.",
      normalizedTextHash: hashes.first,
      sourceUrl: "https://news.example.test/article/alpha",
      capturedAt: "2026-06-26T00:02:30.000Z",
      captureHash: hashes.second,
      immutable: true,
      attachments: [],
    }),
    EvidenceRecordSchema.parse({
      id: "evidence-003",
      candidateUrlId: "candidate-002",
      kind: "comment_text",
      originalText: "반복 악성 문구와 거의 같은 시연용 문장입니다",
      normalizedTextHash: hashes.near,
      sourceUrl: "https://news.example.test/article/beta",
      capturedAt: "2026-06-26T00:03:00.000Z",
      captureHash: hashes.near,
      immutable: true,
      attachments: [],
    }),
    EvidenceRecordSchema.parse({
      id: "evidence-004",
      candidateUrlId: "candidate-002",
      kind: "comment_text",
      originalText: "오탐 제외 예시로 기록된 일반적인 의견 차이입니다.",
      normalizedTextHash: hashes.falsePositive,
      sourceUrl: "https://news.example.test/article/beta",
      capturedAt: "2026-06-26T00:04:00.000Z",
      captureHash: hashes.falsePositive,
      immutable: true,
      attachments: [],
    }),
  ],
  publicHandles: [
    SitePublicHandleSchema.parse({
      id: "handle-001",
      siteHost: "news.example.test",
      publicHandle: "공개핸들A",
      evidenceIds: ["evidence-001", "evidence-002"],
      note: "사이트 안에서 보이는 공개 핸들만 기록합니다. 실제 인물 추정은 하지 않습니다.",
    }),
  ],
  clusters: [
    EvidenceClusterSchema.parse({
      id: "cluster-001",
      kind: "exact_duplicate",
      evidenceIds: ["evidence-001", "evidence-002"],
      score: 1,
      reviewerConfirmed: true,
      rationale: "정규화된 텍스트 해시가 같습니다.",
    }),
    EvidenceClusterSchema.parse({
      id: "cluster-002",
      kind: "near_duplicate_suggestion",
      evidenceIds: ["evidence-001", "evidence-003"],
      score: 0.88,
      reviewerConfirmed: false,
      rationale: "사람의 검토가 필요한 유사 문구 예시입니다.",
    }),
  ],
  reviewDecisions: [
    ReviewRecordSchema.parse({
      id: "review-approved-001",
      evidenceId: "evidence-001",
      decision: "approved",
      reviewerNote: "신고 패키지 내보내기 예시로 승인했습니다.",
      reviewedAt: "2026-06-26T00:05:00.000Z",
    }),
    ReviewRecordSchema.parse({
      id: "review-approved-002",
      evidenceId: "evidence-002",
      decision: "approved",
      reviewerNote: "동일 문구 내보내기 예시로 승인했습니다.",
      reviewedAt: "2026-06-26T00:05:30.000Z",
    }),
    ReviewRecordSchema.parse({
      id: "review-001",
      evidenceId: "evidence-004",
      decision: "false_positive",
      reviewerNote: "악성으로 보기 어려운 캡처는 제외할 수 있음을 보여주는 예시입니다.",
      reviewedAt: "2026-06-26T00:05:00.000Z",
    }),
  ],
}
