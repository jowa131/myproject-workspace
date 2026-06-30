import { z } from "zod"
import { parseBoundary } from "./safety"

const isoDateTime = z.string().datetime({ offset: true })
const sha256Hex = z.string().regex(/^[a-f0-9]{64}$/u)

export const TargetKindSchema = z.enum(["person", "organization", "topic"])
export const CandidateStatusSchema = z.enum(["queued", "opened", "captured", "dismissed"])
export const DiscoveryMethodSchema = z.enum(["manual", "official_search", "import_stub"])
export const EvidenceKindSchema = z.enum([
  "comment_text",
  "page_context",
  "screenshot",
  "attachment",
])
export const ClusterKindSchema = z.enum(["exact_duplicate", "near_duplicate_suggestion"])
export const ReviewDecisionSchema = z.enum([
  "needs_review",
  "approved",
  "false_positive",
  "excluded",
])
export const AuditEventKindSchema = z.enum([
  "candidate_created",
  "capture_received",
  "evidence_created",
  "review_recorded",
  "report_package_created",
])
export const ReportPackageStatusSchema = z.enum(["draft", "ready", "exported"])

export const KeywordTargetSchema = z
  .object({
    id: z.string().min(1).brand("KeywordTargetId"),
    kind: TargetKindSchema,
    label: z.string().min(1).max(160),
    keywords: z.array(z.string().min(1).max(80)).min(1).readonly(),
    createdAt: isoDateTime,
  })
  .strict()

export const CandidateUrlSchema = z
  .object({
    id: z.string().min(1).brand("CandidateUrlId"),
    targetId: z.string().min(1).brand("KeywordTargetId"),
    source: z.string().min(1).max(80),
    query: z.string().min(1).max(240),
    url: z.string().url(),
    title: z.string().min(1).max(240),
    discoveryMethod: DiscoveryMethodSchema,
    robotsSafetyNote: z.string().min(1).max(400),
    status: CandidateStatusSchema,
    createdAt: isoDateTime,
  })
  .strict()

export const AttachmentMetadataSchema = z
  .object({
    id: z.string().min(1).brand("AttachmentId"),
    evidenceId: z.string().min(1).brand("EvidenceId"),
    fileName: z.string().min(1).max(180),
    mediaType: z.string().min(1).max(120),
    byteLength: z.number().int().nonnegative(),
    sha256: sha256Hex,
    storagePath: z.string().min(1).max(400),
  })
  .strict()

export const CapturePayloadSchema = z
  .object({
    candidateUrlId: z.string().min(1).brand("CandidateUrlId"),
    pageUrl: z.string().url(),
    pageTitle: z.string().min(1).max(240),
    selectedText: z.string().min(1).max(10_000),
    publicHandle: z.string().min(1).max(120),
    visibleTimestamp: z.string().min(1).max(120),
    domSnippet: z.string().min(1).max(20_000),
    capturedAt: isoDateTime,
    screenshotDataUrlSha256: sha256Hex.optional(),
    reviewerNote: z.string().max(1000).optional(),
  })
  .strict()

export const CaptureBatchPayloadSchema = z
  .object({
    captures: z.array(CapturePayloadSchema).min(1).max(50).readonly(),
  })
  .strict()

export const EvidenceRecordSchema = z
  .object({
    id: z.string().min(1).brand("EvidenceId"),
    candidateUrlId: z.string().min(1).brand("CandidateUrlId"),
    kind: EvidenceKindSchema,
    originalText: z.string().min(1).max(20_000),
    normalizedTextHash: sha256Hex,
    sourceUrl: z.string().url(),
    capturedAt: isoDateTime,
    captureHash: sha256Hex,
    immutable: z.literal(true),
    attachments: z.array(AttachmentMetadataSchema).readonly(),
  })
  .strict()

export const SitePublicHandleSchema = z
  .object({
    id: z.string().min(1).brand("SitePublicHandleId"),
    siteHost: z.string().min(1).max(160),
    publicHandle: z.string().min(1).max(120),
    evidenceIds: z.array(z.string().min(1).brand("EvidenceId")).readonly(),
    note: z.string().max(400).optional(),
  })
  .strict()

export const EvidenceClusterSchema = z
  .object({
    id: z.string().min(1).brand("EvidenceClusterId"),
    kind: ClusterKindSchema,
    evidenceIds: z.array(z.string().min(1).brand("EvidenceId")).min(2).readonly(),
    score: z.number().min(0).max(1),
    reviewerConfirmed: z.boolean(),
    rationale: z.string().min(1).max(400),
  })
  .strict()

export const ReviewRecordSchema = z
  .object({
    id: z.string().min(1).brand("ReviewId"),
    evidenceId: z.string().min(1).brand("EvidenceId"),
    decision: ReviewDecisionSchema,
    reviewerNote: z.string().min(1).max(1000),
    reviewedAt: isoDateTime,
  })
  .strict()

export const AuditEventSchema = z
  .object({
    id: z.string().min(1).brand("AuditEventId"),
    kind: AuditEventKindSchema,
    subjectId: z.string().min(1),
    message: z.string().min(1).max(500),
    createdAt: isoDateTime,
  })
  .strict()

export const ReportPackageRecordSchema = z
  .object({
    id: z.string().min(1).brand("ReportPackageId"),
    status: ReportPackageStatusSchema,
    evidenceIds: z.array(z.string().min(1).brand("EvidenceId")).readonly(),
    clusterIds: z.array(z.string().min(1).brand("EvidenceClusterId")).readonly(),
    createdAt: isoDateTime,
    exportBasePath: z.string().min(1).max(400).optional(),
  })
  .strict()

export type KeywordTarget = Readonly<z.infer<typeof KeywordTargetSchema>>
export type CandidateUrl = Readonly<z.infer<typeof CandidateUrlSchema>>
export type CapturePayload = Readonly<z.infer<typeof CapturePayloadSchema>>
export type CaptureBatchPayload = Readonly<z.infer<typeof CaptureBatchPayloadSchema>>
export type EvidenceRecord = Readonly<z.infer<typeof EvidenceRecordSchema>>
export type SitePublicHandle = Readonly<z.infer<typeof SitePublicHandleSchema>>
export type EvidenceCluster = Readonly<z.infer<typeof EvidenceClusterSchema>>
export type ReviewRecord = Readonly<z.infer<typeof ReviewRecordSchema>>
export type AuditEvent = Readonly<z.infer<typeof AuditEventSchema>>
export type AttachmentMetadata = Readonly<z.infer<typeof AttachmentMetadataSchema>>
export type ReportPackageRecord = Readonly<z.infer<typeof ReportPackageRecordSchema>>

export function parseCandidateUrl(input: unknown): CandidateUrl {
  return parseBoundary(CandidateUrlSchema, input)
}

export function parseKeywordTarget(input: unknown): KeywordTarget {
  return parseBoundary(KeywordTargetSchema, input)
}

export function parseCapturePayload(input: unknown): CapturePayload {
  return parseBoundary(CapturePayloadSchema, input)
}

export function parseCaptureBatchPayload(input: unknown): CaptureBatchPayload {
  return parseBoundary(CaptureBatchPayloadSchema, input)
}

export function parseEvidenceRecord(input: unknown): EvidenceRecord {
  return parseBoundary(EvidenceRecordSchema, input)
}

export function parseReportPackageRecord(input: unknown): ReportPackageRecord {
  return parseBoundary(ReportPackageRecordSchema, input)
}
