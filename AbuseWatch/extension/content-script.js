;(() => {
  const appUrl = "http://127.0.0.1:4173/"
  const unsafePattern =
    /<\s*(form|input|script|style)\b|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:01[016789][\s.-]?\d{3,4}[\s.-]?\d{4}|0\d{1,2}[\s.-]?\d{3,4}[\s.-]?\d{4}|\+\d{1,3}[\s.-]?\d{6,14})\b|\b(device|credential|password|token|cookie|authorization)\b/iu

  const selection = String(window.getSelection ? window.getSelection() : "").trim()
  const isVisible = (container) => {
    const style = window.getComputedStyle ? window.getComputedStyle(container) : null
    return (
      container.hidden !== true &&
      container.getAttribute?.("aria-hidden") !== "true" &&
      container.getClientRects().length > 0 &&
      style?.display !== "none" &&
      style?.visibility !== "hidden"
    )
  }
  const visibleText = (container) =>
    Array.from(container.childNodes)
      .map((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          return node.textContent || ""
        }
        if (node.nodeType !== Node.ELEMENT_NODE) {
          return ""
        }
        return isVisible(node) ? visibleText(node) : ""
      })
      .join(" ")
      .replace(/\s+/gu, " ")
      .trim()
  const visibleSnippet = (capture) =>
    `<article data-abusewatch-comment="visible-subset"><time>${escapeHtml(
      capture.visibleTimestamp,
    )}</time><span data-abusewatch-handle="true">${escapeHtml(
      capture.publicHandle,
    )}</span><p>${escapeHtml(capture.selectedText).slice(0, 1800)}</p></article>`
  const markedComments = Array.from(document.querySelectorAll("[data-abusewatch-comment]"))
    .filter((container) => isVisible(container))
    .slice(0, 30)
  const globalHandleElement = document.querySelector("[data-abusewatch-handle]")
  const globalTimeElement = document.querySelector("[data-abusewatch-time]")
  const globalHandle =
    globalHandleElement && isVisible(globalHandleElement)
      ? visibleText(globalHandleElement) || "공개 핸들 미확인"
      : "공개 핸들 미확인"
  const globalTime =
    globalTimeElement && isVisible(globalTimeElement)
      ? visibleText(globalTimeElement) || "표시 시간 미확인"
      : "표시 시간 미확인"
  const capturedAt = new Date().toISOString()

  const escapeHtml = (value) =>
    value.replace(
      /[&<>"']/g,
      (character) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[character],
    )

  const selectionLines = selection
    .split(/\n{2,}|\r?\n/u)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .slice(0, 30)

  const captures =
    markedComments.length > 0
      ? markedComments.map((container) => {
          const capture = {
            candidateUrlId: "candidate-extension",
            pageUrl: location.href,
            pageTitle: document.title || location.href,
            selectedText: visibleText(container),
            publicHandle: (() => {
              const handleElement = container.querySelector("[data-abusewatch-handle]")
              return handleElement && isVisible(handleElement)
                ? visibleText(handleElement) || globalHandle
                : globalHandle
            })(),
            visibleTimestamp: (() => {
              const timeElement = container.querySelector("[data-abusewatch-time]")
              return timeElement && isVisible(timeElement)
                ? visibleText(timeElement) || globalTime
                : globalTime
            })(),
            capturedAt,
          }
          return {
            ...capture,
            domSnippet: visibleSnippet(capture),
          }
        })
      : selectionLines.map((line) => ({
          candidateUrlId: "candidate-extension",
          pageUrl: location.href,
          pageTitle: document.title || location.href,
          selectedText: line,
          publicHandle: globalHandle,
          visibleTimestamp: globalTime,
          domSnippet: `<article data-abusewatch-comment="selected-region"><p>${escapeHtml(
            line,
          ).slice(0, 1800)}</p></article>`,
          capturedAt,
        }))

  if (
    captures.length === 0 ||
    captures.some(
      (capture) =>
        capture.selectedText.length === 0 ||
        !capture.domSnippet.includes("data-abusewatch-comment") ||
        unsafePattern.test(capture.selectedText) ||
        unsafePattern.test(capture.domSnippet) ||
        unsafePattern.test(capture.publicHandle),
    )
  ) {
    window.alert("AbuseWatch 캡처 차단: 표시된 공개 댓글 영역만 선택해 주세요.")
    return
  }

  location.href = `${appUrl}?captures=${encodeURIComponent(JSON.stringify({ captures }))}`
})()
