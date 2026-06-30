export type OcrAdapterStatus = {
  readonly kind: "disabled"
  readonly activeExtractionMethod: "dom"
  readonly label: "OCR 비활성"
  readonly reason: "현재 MVP는 DOM 선택과 표시된 댓글 영역 캡처를 사용합니다."
}

export function getOcrAdapterStatus(): OcrAdapterStatus {
  return {
    kind: "disabled",
    activeExtractionMethod: "dom",
    label: "OCR 비활성",
    reason: "현재 MVP는 DOM 선택과 표시된 댓글 영역 캡처를 사용합니다.",
  }
}
