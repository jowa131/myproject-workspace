import { describe, expect, it } from "vitest"
import { buildReportPackage, safeCsvCell } from "../src/domain/report"
import { demoSeed } from "../src/fixtures/demo"

describe("T5 report export", () => {
  it("exports reviewed evidence while separating suggestions", () => {
    // Given: approved duplicate evidence and unconfirmed near-duplicate suggestions.
    const input = {
      evidence: demoSeed.evidenceRecords,
      handles: demoSeed.publicHandles,
      clusters: demoSeed.clusters,
      reviews: demoSeed.reviewDecisions,
    }

    // When: a report package is built.
    const report = buildReportPackage(input)

    // Then: reviewed evidence is included, private fields are absent, suggestions are labelled.
    expect(report.markdown).toContain("검토된 신고 패키지")
    expect(report.markdown).toContain("검토가 필요한 유사 문구 후보")
    expect(report.markdown).not.toContain("ipAddress")
    expect(report.csv).toContain("출처_URL")
    expect(report.html).toContain("사람이 검토한 뒤 직접 제출하기 위한 자료입니다.")
  })

  it("makes CSV cells formula-injection safe", () => {
    // Given: spreadsheet formula-leading values.
    const dangerous = "=cmd"

    // When: the CSV cell is escaped.
    const cell = safeCsvCell(dangerous)

    // Then: a leading quote neutralizes formula interpretation.
    expect(cell).toBe('"\'=cmd"')
  })
})
