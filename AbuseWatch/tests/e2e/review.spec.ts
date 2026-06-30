import { expect, test } from "@playwright/test"

const capturePayload = {
  candidateUrlId: "candidate-001",
  pageUrl: "https://news.nate.com/view/123",
  pageTitle: "NATE sample opened by reviewer",
  selectedText: "반복 문구 증거 반복 문구 증거 반복 문구 증거 repeated phrase for capture",
  publicHandle: "samplePublicHandle",
  visibleTimestamp: "2026-06-26 09:00",
  domSnippet:
    '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">samplePublicHandle</span><p>반복 문구 증거 반복 문구 증거 반복 문구 증거 repeated phrase for capture</p></article>',
  capturedAt: "2026-06-26T00:00:00.000Z",
}

const captureBatchPayload = {
  captures: [
    capturePayload,
    {
      ...capturePayload,
      selectedText: "두 번째 보이는 댓글 증거 두 번째 보이는 댓글 증거 repeated batch phrase",
      publicHandle: "secondPublicHandle",
      visibleTimestamp: "2026-06-26 09:01",
      domSnippet:
        '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">secondPublicHandle</span><p>두 번째 보이는 댓글 증거 두 번째 보이는 댓글 증거 repeated batch phrase</p></article>',
    },
  ],
}

test("reviewer can queue, capture, review, and export without platform requests", async ({
  page,
}) => {
  const blockedRequests: string[] = []
  await page.route("**/*", (route) => {
    const requestUrl = new URL(route.request().url())
    if (
      /(?:^|\.)nate\.com$/u.test(requestUrl.hostname) ||
      /(?:^|\.)naver\.com$/u.test(requestUrl.hostname)
    ) {
      blockedRequests.push(route.request().url())
      return route.abort()
    }
    return route.continue()
  })

  await page.goto("/")
  await expect(page.getByRole("heading", { name: "AbuseWatch 검토 작업 공간" })).toBeVisible()
  await expect(page.getByTestId("ocr-status")).toContainText("OCR 비활성")
  await expect(page.getByTestId("ocr-status")).toContainText("DOM 선택")

  await page.getByLabel("이름").fill("NATE 후보")
  await page.getByLabel("키워드").fill("sample, phrase")
  await page.getByRole("button", { name: "대상 저장" }).click()
  await expect(page.getByTestId("status-message")).toContainText("관심 대상을 저장했습니다")

  await page.getByLabel("URL").fill("https://news.nate.com/view/123")
  await page.getByLabel("제목").fill("NATE sample article")
  await page.getByRole("button", { name: "URL 추가" }).click()
  await expect(page.getByText("NATE sample article")).toBeVisible()

  await page.goto(`/?capture=${encodeURIComponent(JSON.stringify(capturePayload))}`)
  await expect(page.getByTestId("status-message")).toContainText("증거를 저장했습니다")
  await expect(page.getByText("samplePublicHandle")).toBeVisible()

  await page.getByRole("button", { name: "승인" }).first().click()
  await page.getByRole("button", { name: "신고 패키지 생성" }).click()
  await expect(page.getByTestId("report-preview")).toContainText("검토된 신고 패키지")
  await expect(page.getByText("검토가 필요한 유사 문구 후보").first()).toBeVisible()

  expect(blockedRequests).toEqual([])
  await page.screenshot({
    fullPage: true,
    path: ".omo/evidence/task-7-abuse-comment-tracker-desktop.png",
  })
})

test("mobile workspace has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/")
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
  await page.screenshot({
    fullPage: true,
    path: ".omo/evidence/task-7-abuse-comment-tracker-mobile.png",
  })
})

test("unsafe capture is rejected with visible validation", async ({ page }) => {
  const unsafePayload = {
    ...capturePayload,
    selectedText: "Contact sample@example.test",
    domSnippet: '<form data-account-chrome="true"><input type="hidden" value="secret"></form>',
  }
  await page.goto(`/?capture=${encodeURIComponent(JSON.stringify(unsafePayload))}`)
  await expect(page.getByTestId("status-message")).toContainText("개인정보 또는 계정 화면 요소")
})

test("capture import preserves percent characters", async ({ page }) => {
  const percentPayload = {
    ...capturePayload,
    pageUrl: "https://news.example.test/view/percent",
    selectedText: "visible 100% public comment text",
    domSnippet:
      '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">percentHandle</span><p>visible 100% public comment text</p></article>',
  }

  await page.goto(`/?capture=${encodeURIComponent(JSON.stringify(percentPayload))}`)

  await expect(page.getByTestId("status-message")).toContainText("증거를 저장했습니다")
  await expect(page.getByText("visible 100% public comment text")).toBeVisible()
})

test("reviewer can import multiple visible comments from one user-triggered capture", async ({
  page,
}) => {
  const blockedRequests: string[] = []
  await page.route("**/*", (route) => {
    const requestUrl = new URL(route.request().url())
    if (
      /(?:^|\.)nate\.com$/u.test(requestUrl.hostname) ||
      /(?:^|\.)naver\.com$/u.test(requestUrl.hostname)
    ) {
      blockedRequests.push(route.request().url())
      return route.abort()
    }
    return route.continue()
  })

  await page.goto(`/?captures=${encodeURIComponent(JSON.stringify(captureBatchPayload))}`)

  await expect(page.getByTestId("status-message")).toContainText("보이는 댓글 2건을 저장했습니다")
  await expect(page.getByText("samplePublicHandle")).toBeVisible()
  await expect(page.getByText("secondPublicHandle")).toBeVisible()
  await expect(page.getByText("두 번째 보이는 댓글 증거")).toBeVisible()
  await expect(page.getByRole("heading", { name: "증거 기록" }).last()).toBeVisible()
  expect(blockedRequests).toEqual([])
})
