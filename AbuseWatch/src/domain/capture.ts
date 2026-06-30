import type { CaptureBatchPayload, CapturePayload, EvidenceRecord } from "./contracts"
import { parseCaptureBatchPayload, parseCapturePayload, parseEvidenceRecord } from "./contracts"
import { sha256Hex } from "./hash"
import { normalizeEvidenceText } from "./normalize"

export type SafeCaptureResult =
  | { readonly ok: true; readonly payload: CapturePayload }
  | { readonly ok: false; readonly reason: string }

export type SafeCaptureBatchResult =
  | { readonly ok: true; readonly payload: CaptureBatchPayload }
  | { readonly ok: false; readonly reason: string }

const unsafeContentPatterns: readonly RegExp[] = [
  /<\s*(form|input|script|style)\b/iu,
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/iu,
  /\b(?:\d{1,3}\.){3}\d{1,3}\b/u,
  /\b(?:01[016789][\s.-]?\d{3,4}[\s.-]?\d{4}|0\d{1,2}[\s.-]?\d{3,4}[\s.-]?\d{4}|\+\d{1,3}[\s.-]?\d{6,14})\b/u,
  /\b(device|credential|password|token|cookie|authorization)\b/iu,
]

const hiddenDomPatterns: readonly RegExp[] = [
  /<[^>]+\bhidden(?:\s|=|>)/iu,
  /\baria-hidden\s*=\s*["']?true["']?/iu,
  /\bdisplay\s*:\s*none\b/iu,
  /\bvisibility\s*:\s*hidden\b/iu,
]

export function parseSafeCapturePayload(input: unknown): SafeCaptureResult {
  const payload = parseCapturePayload(input)
  const unsafeReason = findUnsafeCaptureReason(payload)
  if (unsafeReason !== null) {
    return { ok: false, reason: unsafeReason }
  }
  return { ok: true, payload }
}

export function parseSafeCaptureBatchPayload(input: unknown): SafeCaptureBatchResult {
  const payload = parseCaptureBatchPayload(input)
  for (const [index, capture] of payload.captures.entries()) {
    const unsafeReason = findUnsafeCaptureReason(capture)
    if (unsafeReason !== null) {
      return { ok: false, reason: `${index + 1}번째 댓글: ${unsafeReason}` }
    }
  }
  return { ok: true, payload }
}

export async function createEvidenceFromCapture(
  payload: CapturePayload,
  evidenceId: string,
): Promise<EvidenceRecord> {
  const normalizedText = normalizeEvidenceText(payload.selectedText)
  const normalizedTextHash = await sha256Hex(normalizedText)
  const captureHash = await sha256Hex(
    JSON.stringify({
      pageUrl: payload.pageUrl,
      selectedText: payload.selectedText,
      publicHandle: payload.publicHandle,
      visibleTimestamp: payload.visibleTimestamp,
      domSnippet: payload.domSnippet,
      capturedAt: payload.capturedAt,
    }),
  )

  return parseEvidenceRecord({
    id: evidenceId,
    candidateUrlId: payload.candidateUrlId,
    kind: "comment_text",
    originalText: payload.selectedText,
    normalizedTextHash,
    sourceUrl: payload.pageUrl,
    capturedAt: payload.capturedAt,
    captureHash,
    immutable: true,
    attachments: [],
  })
}

export async function createEvidenceBatchFromCaptureBatch(
  payload: CaptureBatchPayload,
  evidenceIdPrefix: string,
): Promise<readonly EvidenceRecord[]> {
  const records: EvidenceRecord[] = []
  for (const [index, capture] of payload.captures.entries()) {
    const suffix = String(index + 1).padStart(3, "0")
    records.push(await createEvidenceFromCapture(capture, `${evidenceIdPrefix}-${suffix}`))
  }
  return records
}

export function makeBookmarklet(appUrl: string): string {
  const script = `
(() => {
  const selection = String(window.getSelection ? window.getSelection() : "").trim();
  const escapeHtml = (value) => value.replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const splitSelection = (value) => value.split(/\\n{2,}|\\r?\\n/u).map((line) => line.trim()).filter((line) => line.length > 0).slice(0, 30);
  const isVisible = (container) => {
    const style = window.getComputedStyle ? window.getComputedStyle(container) : null;
    return container.hidden !== true
      && container.getAttribute?.("aria-hidden") !== "true"
      && container.getClientRects().length > 0
      && style?.display !== "none"
      && style?.visibility !== "hidden";
  };
  const visibleText = (container) => Array.from(container.childNodes)
    .map((node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        return node.textContent || "";
      }
      if (node.nodeType !== Node.ELEMENT_NODE) {
        return "";
      }
      return isVisible(node) ? visibleText(node) : "";
    })
    .join(" ")
    .replace(/\\s+/gu, " ")
    .trim();
  const visibleSnippet = (capture) => '<article data-abusewatch-comment="visible-subset"><time>'
    + escapeHtml(capture.visibleTimestamp)
    + '</time><span data-abusewatch-handle="true">'
    + escapeHtml(capture.publicHandle)
    + '</span><p>'
    + escapeHtml(capture.selectedText).slice(0, 1800)
    + '</p></article>';
  const marked = Array.from(document.querySelectorAll("[data-abusewatch-comment]")).filter(isVisible).slice(0, 30);
  const globalHandleElement = document.querySelector("[data-abusewatch-handle]");
  const globalTimeElement = document.querySelector("[data-abusewatch-time]");
  const globalHandle = globalHandleElement && isVisible(globalHandleElement)
    ? visibleText(globalHandleElement) || "공개 핸들 미확인"
    : "공개 핸들 미확인";
  const globalTime = globalTimeElement && isVisible(globalTimeElement)
    ? visibleText(globalTimeElement) || "표시 시간 미확인"
    : "표시 시간 미확인";
  const capturedAt = new Date().toISOString();
  const captures = marked.length > 0
    ? marked.map((container) => {
        const capture = {
          candidateUrlId: "candidate-bookmarklet",
          pageUrl: location.href,
          pageTitle: document.title || location.href,
          selectedText: visibleText(container),
          publicHandle: (() => {
            const handleElement = container.querySelector("[data-abusewatch-handle]");
            return handleElement && isVisible(handleElement) ? visibleText(handleElement) || globalHandle : globalHandle;
          })(),
          visibleTimestamp: (() => {
            const timeElement = container.querySelector("[data-abusewatch-time]");
            return timeElement && isVisible(timeElement) ? visibleText(timeElement) || globalTime : globalTime;
          })(),
          capturedAt
        };
        return {
          ...capture,
          domSnippet: visibleSnippet(capture)
        };
      })
    : splitSelection(selection).map((text) => ({
        candidateUrlId: "candidate-bookmarklet",
        pageUrl: location.href,
        pageTitle: document.title || location.href,
        selectedText: text,
        publicHandle: globalHandle,
        visibleTimestamp: globalTime,
        domSnippet: '<article data-abusewatch-comment="selected-region"><p>' + escapeHtml(text).slice(0, 1800) + '</p></article>',
        capturedAt
      }));
  if (captures.length === 0) {
    window.alert("AbuseWatch 캡처 차단: 보이는 댓글 영역을 선택해 주세요.");
    return;
  }
  location.href = "${appUrl}?captures=" + encodeURIComponent(JSON.stringify({ captures }));
})();`

  return `javascript:${encodeURIComponent(script)}`
}

function findUnsafeCaptureReason(payload: CapturePayload): string | null {
  if (payload.selectedText.trim().length === 0) {
    return "선택했거나 화면에 보이는 댓글 텍스트가 필요합니다."
  }

  for (const field of [payload.selectedText, payload.domSnippet, payload.publicHandle]) {
    if (unsafeContentPatterns.some((pattern) => pattern.test(field))) {
      return "캡처 내용에 개인정보 또는 계정 화면 요소가 포함되어 있습니다."
    }
  }

  if (hiddenDomPatterns.some((pattern) => pattern.test(payload.domSnippet))) {
    return "화면에 보이지 않는 댓글 DOM은 캡처할 수 없습니다."
  }

  if (!payload.domSnippet.includes("data-abusewatch-comment")) {
    return "캡처 DOM은 명시적으로 표시된 댓글 영역에서만 가져올 수 있습니다."
  }

  return null
}
