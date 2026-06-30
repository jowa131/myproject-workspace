import { describe, expect, it } from "vitest"
import { getOcrAdapterStatus } from "../src/domain/ocr"

describe("T6 OCR adapter status", () => {
  it("reports OCR as disabled while DOM extraction remains primary", () => {
    // Given: the MVP has no OCR engine configured.
    const status = getOcrAdapterStatus()

    // When: the review workspace asks how text extraction is handled.
    // Then: OCR is explicit and DOM extraction remains the active method.
    expect(status).toEqual({
      kind: "disabled",
      activeExtractionMethod: "dom",
      label: "OCR 비활성",
      reason: "현재 MVP는 DOM 선택과 표시된 댓글 영역 캡처를 사용합니다.",
    })
  })
})
