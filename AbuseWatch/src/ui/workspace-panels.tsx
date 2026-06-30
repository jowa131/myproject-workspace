import type { FormEvent } from "react"
import type {
  CandidateUrl,
  EvidenceCluster,
  EvidenceRecord,
  SitePublicHandle,
} from "../domain/contracts"
import type { ReportPackage } from "../domain/report"
import { DataList, ListEmpty, Panel } from "./components"

export function InterestTargetsPanel(props: {
  readonly targetCount: number
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <Panel title="관심 키워드/대상">
      <form className="form-grid" onSubmit={props.onSubmit}>
        <label>
          이름
          <input name="label" required placeholder="관심 주제 또는 대상" />
        </label>
        <label>
          키워드
          <input name="keywords" required placeholder="쉼표로 구분한 검색어" />
        </label>
        <button type="submit">대상 저장</button>
      </form>
      <ListEmpty show={props.targetCount === 0} text="아직 저장된 관심 대상이 없습니다." />
    </Panel>
  )
}

export function CandidateQueuePanel(props: {
  readonly candidates: readonly CandidateUrl[]
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  return (
    <Panel title="후보 URL 큐">
      <form className="form-grid" onSubmit={props.onSubmit}>
        <label>
          출처
          <input name="source" defaultValue="수동" required />
        </label>
        <label>
          검색어
          <input name="query" defaultValue="수동 URL" required />
        </label>
        <label>
          URL
          <input name="url" type="url" required placeholder="https://news.nate.com/view/123" />
        </label>
        <label>
          제목
          <input name="title" required placeholder="후보 기사 또는 게시물 제목" />
        </label>
        <button type="submit">URL 추가</button>
      </form>
      <DataList
        items={props.candidates.slice(0, 4).map((candidate) => ({
          id: candidate.id,
          primary: candidate.title,
          secondary: candidate.url,
          action: (
            <a className="row-link" href={candidate.url} rel="noopener noreferrer" target="_blank">
              열기
            </a>
          ),
        }))}
      />
    </Panel>
  )
}

export function EvidenceRecordsPanel(props: {
  readonly evidence: readonly EvidenceRecord[]
  readonly onApprove: (record: EvidenceRecord) => void
  readonly onSplit: (record: EvidenceRecord) => void
}) {
  return (
    <Panel title="증거 기록">
      <DataList
        items={props.evidence.slice(0, 5).map((record) => ({
          id: record.id,
          primary: record.originalText,
          secondary: record.sourceUrl,
          action: (
            <span className="row-actions">
              <button type="button" onClick={() => props.onApprove(record)}>
                승인
              </button>
              <button type="button" onClick={() => props.onSplit(record)}>
                제외
              </button>
            </span>
          ),
        }))}
      />
    </Panel>
  )
}

export function ClustersPanel(props: { readonly clusters: readonly EvidenceCluster[] }) {
  return (
    <Panel title="중복/유사 문구 묶음">
      <DataList
        items={props.clusters.map((cluster) => ({
          id: cluster.id,
          primary:
            cluster.kind === "exact_duplicate"
              ? "확인된 동일 문구"
              : "검토가 필요한 유사 문구 후보",
          secondary: `${cluster.evidenceIds.join(", ")} | 점수 ${cluster.score.toFixed(2)}`,
        }))}
      />
    </Panel>
  )
}

export function HandlesPanel(props: { readonly handles: readonly SitePublicHandle[] }) {
  return (
    <Panel title="사이트별 공개 핸들">
      <DataList
        items={props.handles.map((handle) => ({
          id: handle.id,
          primary: handle.publicHandle,
          secondary: `${handle.siteHost} | 증거 ${handle.evidenceIds.length}건`,
        }))}
      />
    </Panel>
  )
}

export function ExportPanel(props: {
  readonly approvedCount: number
  readonly report: ReportPackage | null
  readonly onExport: () => void
}) {
  return (
    <Panel title="사람이 검토한 신고 패키지">
      <button type="button" onClick={props.onExport} disabled={props.approvedCount === 0}>
        신고 패키지 생성
      </button>
      {props.report === null ? (
        <p className="muted">증거를 하나 이상 사람이 승인하면 내보낼 수 있습니다.</p>
      ) : (
        <pre data-testid="report-preview">{props.report.markdown.slice(0, 900)}</pre>
      )}
    </Panel>
  )
}
