import type {
  AuditEvent,
  CandidateUrl,
  EvidenceRecord,
  KeywordTarget,
  ReviewRecord,
  SitePublicHandle,
} from "../domain/contracts"
import { demoSeed } from "../fixtures/demo"

export type WorkspaceState = {
  readonly targets: readonly KeywordTarget[]
  readonly candidates: readonly CandidateUrl[]
  readonly evidence: readonly EvidenceRecord[]
  readonly handles: readonly SitePublicHandle[]
  readonly reviews: readonly ReviewRecord[]
  readonly audit: readonly AuditEvent[]
}

export const initialState: WorkspaceState = {
  targets: [],
  candidates: demoSeed.candidateUrls,
  evidence: demoSeed.evidenceRecords,
  handles: demoSeed.publicHandles,
  reviews: demoSeed.reviewDecisions,
  audit: [],
}

export const nowIso = () => new Date().toISOString()
