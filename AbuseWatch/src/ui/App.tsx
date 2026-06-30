import { useEffect, useMemo, useRef, useState } from "react"
import { createCandidateUrl, createKeywordTarget } from "../domain/candidate"
import {
  createEvidenceBatchFromCaptureBatch,
  createEvidenceFromCapture,
  makeBookmarklet,
  parseSafeCaptureBatchPayload,
  parseSafeCapturePayload,
} from "../domain/capture"
import { buildEvidenceClusters } from "../domain/cluster"
import type { EvidenceRecord } from "../domain/contracts"
import { ReviewRecordSchema, SitePublicHandleSchema } from "../domain/contracts"
import { type ReportPackage, buildReportPackage } from "../domain/report"
import { demoSeed } from "../fixtures/demo"
import { CaptureTool, StatusMessage, WorkflowCounters, WorkspaceHeader } from "./components"
import {
  CandidateQueuePanel,
  ClustersPanel,
  EvidenceRecordsPanel,
  ExportPanel,
  HandlesPanel,
  InterestTargetsPanel,
} from "./workspace-panels"
import { type WorkspaceState, initialState, nowIso } from "./workspace-state"

export function App() {
  const [state, setState] = useState<WorkspaceState>(initialState)
  const [message, setMessage] = useState("후보 URL 검토와 원클릭 증거 캡처를 시작할 수 있습니다.")
  const [report, setReport] = useState<ReportPackage | null>(null)
  const captureImportedRef = useRef(false)
  const bookmarkletRef = useRef<HTMLAnchorElement>(null)
  const clusters = useMemo(
    () => [
      ...buildEvidenceClusters(state.evidence),
      ...demoSeed.clusters.filter((cluster) => cluster.kind === "near_duplicate_suggestion"),
    ],
    [state.evidence],
  )
  const bookmarklet = useMemo(
    () => makeBookmarklet(globalThis.location?.origin ?? "http://127.0.0.1:4173"),
    [],
  )
  const approvedCount = state.reviews.filter((review) => review.decision === "approved").length

  useEffect(() => {
    const searchParams = new URLSearchParams(globalThis.location.search)
    const encodedBatch = searchParams.get("captures")
    const encodedCapture = searchParams.get("capture")
    if (encodedBatch === null && encodedCapture === null) {
      return
    }
    if (captureImportedRef.current) {
      return
    }
    captureImportedRef.current = true
    if (encodedBatch !== null) {
      void importCaptureBatch(encodedBatch)
      return
    }
    if (encodedCapture !== null) {
      void importCapture(encodedCapture)
    }
  }, [])

  useEffect(() => {
    bookmarkletRef.current?.setAttribute("href", bookmarklet)
  }, [bookmarklet])

  const importCapture = async (encodedCapture: string) => {
    try {
      const parsedJson: unknown = JSON.parse(encodedCapture)
      const parsed = parseSafeCapturePayload(parsedJson)
      if (!parsed.ok) {
        setMessage(parsed.reason)
        return
      }
      const evidence = await createEvidenceFromCapture(parsed.payload, `evidence-${Date.now()}`)
      const handle = SitePublicHandleSchema.parse({
        id: `handle-${Date.now()}`,
        siteHost: new URL(parsed.payload.pageUrl).host,
        publicHandle: parsed.payload.publicHandle,
        evidenceIds: [evidence.id],
        note: "사이트 안에서 보이는 공개 핸들만 기록합니다.",
      })
      setState((current) => ({
        ...current,
        evidence: [evidence, ...current.evidence],
        handles: [handle, ...current.handles],
      }))
      setMessage("열린 페이지에서 증거를 저장했습니다. 내보내기 전 사람이 검토해야 합니다.")
      globalThis.history.replaceState(null, "", globalThis.location.pathname)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "캡처 가져오기에 실패했습니다.")
    }
  }

  const importCaptureBatch = async (encodedBatch: string) => {
    try {
      const parsedJson: unknown = JSON.parse(encodedBatch)
      const parsed = parseSafeCaptureBatchPayload(parsedJson)
      if (!parsed.ok) {
        setMessage(parsed.reason)
        return
      }
      const importId = Date.now()
      const evidence = await createEvidenceBatchFromCaptureBatch(
        parsed.payload,
        `evidence-${importId}`,
      )
      const handles = evidence.map((record, index) => {
        const capture = parsed.payload.captures[index]
        if (capture === undefined) {
          throw new Error("배치 캡처와 증거 기록 수가 일치하지 않습니다.")
        }
        return SitePublicHandleSchema.parse({
          id: `handle-${importId}-${index + 1}`,
          siteHost: new URL(capture.pageUrl).host,
          publicHandle: capture.publicHandle,
          evidenceIds: [record.id],
          note: "사이트 안에서 보이는 공개 핸들만 기록합니다.",
        })
      })
      setState((current) => ({
        ...current,
        evidence: [...evidence, ...current.evidence],
        handles: [...handles, ...current.handles],
      }))
      setMessage(
        `보이는 댓글 ${evidence.length}건을 저장했습니다. 내보내기 전 사람이 검토해야 합니다.`,
      )
      globalThis.history.replaceState(null, "", globalThis.location.pathname)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "배치 캡처 가져오기에 실패했습니다.")
    }
  }

  const addTarget = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const label = String(form.get("label") ?? "")
    const keywords = String(form.get("keywords") ?? "")
    const target = createKeywordTarget(label, keywords, nowIso())
    setState((current) => ({ ...current, targets: [target, ...current.targets] }))
    event.currentTarget.reset()
    setMessage("관심 대상을 저장했습니다. 이제 사람이 열 후보 URL을 추가할 수 있습니다.")
  }

  const addCandidate = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const createdAt = nowIso()
    const targetId = state.targets[0]?.id ?? "target-001"
    const result = createCandidateUrl({
      targetId,
      source: String(form.get("source") ?? "manual"),
      query: String(form.get("query") ?? "manual"),
      url: String(form.get("url") ?? ""),
      title: String(form.get("title") ?? "제목 없는 후보"),
      discoveryMethod: "manual",
      createdAt,
    })
    if (!result.ok) {
      setMessage(result.reason)
      return
    }
    setState((current) => ({ ...current, candidates: [result.candidate, ...current.candidates] }))
    event.currentTarget.reset()
    setMessage("후보 URL을 추가했습니다. 증거 캡처 전 사용자가 직접 열어 확인하세요.")
  }

  const approveEvidence = (record: EvidenceRecord) => {
    const review = ReviewRecordSchema.parse({
      id: `review-${Date.now()}`,
      evidenceId: record.id,
      decision: "approved",
      reviewerNote: "사람이 검토한 증거를 신고 패키지에 포함하도록 승인했습니다.",
      reviewedAt: nowIso(),
    })
    setState((current) => ({ ...current, reviews: [review, ...current.reviews] }))
    setMessage("사람이 검토한 내보내기 대상으로 증거를 승인했습니다.")
  }

  const markFalsePositive = (record: EvidenceRecord) => {
    const review = ReviewRecordSchema.parse({
      id: `review-${Date.now()}`,
      evidenceId: record.id,
      decision: "false_positive",
      reviewerNote: "검토자가 이 기록을 오탐으로 제외했습니다.",
      reviewedAt: nowIso(),
    })
    setState((current) => ({ ...current, reviews: [review, ...current.reviews] }))
    setMessage("오탐 제외를 기록했습니다. 다른 증거를 검토해 승인할 수 있습니다.")
  }

  const exportReport = () => {
    const nextReport = buildReportPackage({
      evidence: state.evidence,
      handles: state.handles,
      clusters,
      reviews: state.reviews,
    })
    setReport(nextReport)
    setMessage("사람이 검토할 신고 패키지를 생성했습니다. 자동 제출은 하지 않았습니다.")
  }

  return (
    <main className="workspace" data-testid="abusewatch-app-shell">
      <WorkspaceHeader />

      <StatusMessage message={message} />

      <WorkflowCounters
        approvedCount={approvedCount}
        candidateCount={state.candidates.length}
        evidenceCount={state.evidence.length}
      />

      <section className="workspace__columns">
        <InterestTargetsPanel onSubmit={addTarget} targetCount={state.targets.length} />
        <CandidateQueuePanel candidates={state.candidates} onSubmit={addCandidate} />
      </section>

      <CaptureTool bookmarkletRef={bookmarkletRef} />

      <section className="workspace__columns">
        <EvidenceRecordsPanel
          evidence={state.evidence}
          onApprove={approveEvidence}
          onSplit={markFalsePositive}
        />
        <ClustersPanel clusters={clusters} />
      </section>

      <section className="workspace__columns">
        <HandlesPanel handles={state.handles} />
        <ExportPanel approvedCount={approvedCount} onExport={exportReport} report={report} />
      </section>
    </main>
  )
}
