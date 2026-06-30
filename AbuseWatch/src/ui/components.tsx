import type { ReactNode, RefObject } from "react"
import { getOcrAdapterStatus } from "../domain/ocr"

export function WorkspaceHeader() {
  return (
    <header className="workspace__header">
      <div>
        <p className="workspace__label">증거 수집 보조 도구</p>
        <h1>AbuseWatch 검토 작업 공간</h1>
        <p className="workspace__subcopy">
          후보 URL 발견과 열린 화면의 증거 캡처를 분리해서 다룹니다.
        </p>
      </div>
      <a className="workspace__action" href="/api/health">
        API 상태
      </a>
    </header>
  )
}

export function StatusMessage(props: { readonly message: string }) {
  return (
    <output className="notice" data-testid="status-message">
      {props.message}
    </output>
  )
}

export function CaptureTool(props: {
  readonly bookmarkletRef: RefObject<HTMLAnchorElement | null>
}) {
  const ocrStatus = getOcrAdapterStatus()

  return (
    <section className="panel panel--wide">
      <div className="panel__header">
        <h2>원클릭 캡처 도구</h2>
        <a
          className="bookmarklet"
          href="/"
          ref={props.bookmarkletRef}
          data-testid="bookmarklet-link"
        >
          보이는 증거 저장
        </a>
      </div>
      <p>
        캡처 링크를 북마크 바로 끌어다 놓으세요. 후보 URL을 직접 연 뒤 보이는 댓글 영역을 한 번
        선택하고 북마클릿을 누르면 여러 댓글이 한 번에 증거 기록으로 저장됩니다.
      </p>
      <p className="muted">
        앱은 댓글 페이지를 스스로 넘겨 보지 않습니다. 현재 열린 화면에서 사용자가 명령한 순간의 표시
        텍스트만 구조화하며, 폼, 숨은 필드, 계정 화면 요소, 이메일, 전화번호, IP처럼 보이는 문자열,
        인증 정보, 쿠키는 거부합니다.
      </p>
      <p className="muted" data-testid="ocr-status">
        <strong>{ocrStatus.label}</strong>
        {" | "}
        <span>{ocrStatus.reason}</span>
      </p>
    </section>
  )
}

export function Metric(props: { readonly title: string; readonly value: number }) {
  return (
    <article className="panel metric">
      <h2>{props.title}</h2>
      <strong>{props.value}</strong>
    </article>
  )
}

export function WorkflowCounters(props: {
  readonly candidateCount: number
  readonly evidenceCount: number
  readonly approvedCount: number
}) {
  return (
    <section className="workspace__grid" aria-label="작업 흐름 통계">
      <Metric title="후보 URL" value={props.candidateCount} />
      <Metric title="증거 기록" value={props.evidenceCount} />
      <Metric title="승인된 증거" value={props.approvedCount} />
    </section>
  )
}

export function Panel(props: { readonly title: string; readonly children: ReactNode }) {
  return (
    <section className="panel">
      <h2>{props.title}</h2>
      {props.children}
    </section>
  )
}

export function DataList(props: {
  readonly items: readonly {
    readonly id: string
    readonly primary: string
    readonly secondary: string
    readonly action?: ReactNode
  }[]
}) {
  return (
    <div className="data-list">
      {props.items.map((item) => (
        <div className="data-row" key={item.id}>
          <div>
            <strong>{item.primary}</strong>
            <span>{item.secondary}</span>
          </div>
          {item.action}
        </div>
      ))}
      <ListEmpty show={props.items.length === 0} text="아직 표시할 항목이 없습니다." />
    </div>
  )
}

export function ListEmpty(props: { readonly show: boolean; readonly text: string }) {
  return props.show ? <p className="empty-state">{props.text}</p> : null
}
