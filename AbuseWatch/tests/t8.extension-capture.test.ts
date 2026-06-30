import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"
import { parseSafeCaptureBatchPayload } from "../src/domain/capture"
import {
  buildExtensionCaptureBatchPayload,
  buildExtensionCapturePayload,
  isExtensionCaptureAllowed,
} from "../src/extension/capture-contract"
import { runContentScript } from "./helpers/content-script-fixture"

const markedDom =
  '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">publicHandle</span><p>visible comment text</p></article>'

describe("T8 extension capture contract", () => {
  it("builds the same safe capture payload shape as the app boundary", () => {
    // Given: the extension sees only an explicitly marked comment container.
    const payload = buildExtensionCapturePayload({
      appUrl: "http://127.0.0.1:4173/",
      candidateUrlId: "candidate-extension",
      pageUrl: "https://news.example.test/view/123",
      pageTitle: "Opened article",
      selectedText: "visible comment text",
      publicHandle: "publicHandle",
      visibleTimestamp: "2026-06-26 09:00",
      domSnippet: markedDom,
      capturedAt: "2026-06-26T00:00:00.000Z",
    })

    // When: the payload is prepared for handoff to the local app.
    // Then: it stays local and preserves the existing capture contract fields.
    expect(payload.redirectUrl).toContain("http://127.0.0.1:4173/?capture=")
    expect(payload.capturePayload).toMatchObject({
      candidateUrlId: "candidate-extension",
      pageUrl: "https://news.example.test/view/123",
      selectedText: "visible comment text",
      publicHandle: "publicHandle",
      domSnippet: markedDom,
    })
  })

  it("rejects unsafe extension captures before app handoff", () => {
    // Given: an extension candidate includes private account chrome.
    const decision = isExtensionCaptureAllowed({
      selectedText: "Contact sample@example.test",
      domSnippet: '<form data-account-chrome="true"><input type="hidden" value="secret"></form>',
      publicHandle: "publicHandle",
    })

    // When: the extension evaluates whether it may hand off the payload.
    // Then: unsafe content is blocked before redirecting to the app.
    expect(decision).toEqual({
      ok: false,
      reason: "캡처 내용에 개인정보 또는 계정 화면 요소가 포함되어 있습니다.",
    })
  })

  it("builds a local batch capture handoff for multiple visible comments", () => {
    // Given: the extension sees multiple explicitly marked public comments.
    const result = buildExtensionCaptureBatchPayload({
      appUrl: "http://127.0.0.1:4173/",
      captures: [
        {
          candidateUrlId: "candidate-extension",
          pageUrl: "https://news.example.test/view/123",
          pageTitle: "Opened article",
          selectedText: "first visible comment",
          publicHandle: "publicHandleA",
          visibleTimestamp: "2026-06-26 09:00",
          domSnippet:
            '<article data-abusewatch-comment="true"><p>first visible comment</p></article>',
          capturedAt: "2026-06-26T00:00:00.000Z",
        },
        {
          candidateUrlId: "candidate-extension",
          pageUrl: "https://news.example.test/view/123",
          pageTitle: "Opened article",
          selectedText: "second visible comment",
          publicHandle: "publicHandleB",
          visibleTimestamp: "2026-06-26 09:01",
          domSnippet:
            '<article data-abusewatch-comment="true"><p>second visible comment</p></article>',
          capturedAt: "2026-06-26T00:00:00.000Z",
        },
      ],
    })

    // When: the handoff URL is prepared.
    const redirectedUrl = new URL(result.redirectUrl)
    const batch = parseSafeCaptureBatchPayload(
      JSON.parse(redirectedUrl.searchParams.get("captures") ?? "{}"),
    )
    if (!batch.ok) {
      throw new Error(batch.reason)
    }

    // Then: it stays local and contains both visible comment payloads.
    expect(redirectedUrl.origin).toBe("http://127.0.0.1:4173")
    expect(result.captureBatchPayload.captures).toHaveLength(2)
    expect(batch.payload.captures.map((capture) => capture.publicHandle)).toEqual([
      "publicHandleA",
      "publicHandleB",
    ])
  })

  it("declares no remote host permissions in the extension manifest", () => {
    // Given: the shipped browser extension prototype manifest.
    const manifest = JSON.parse(readFileSync("extension/manifest.json", "utf8")) as {
      readonly permissions: readonly string[]
      readonly host_permissions: readonly string[]
    }

    // When: permissions are inspected.
    // Then: it cannot crawl platform hosts or broad URL patterns.
    expect(manifest.permissions).toEqual(["activeTab", "scripting"])
    expect(manifest.host_permissions).toEqual([])
  })

  it("executes the shipped content script for safe visible comment batches", () => {
    // Given: marked public comments in the active tab.
    const result = runContentScript({
      selectedText: "visible 100% public comment text",
      comments: [
        {
          domSnippet:
            '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">publicHandleA</span><p>visible 100% public comment text</p></article>',
          textContent: "visible 100% public comment text",
          handle: "publicHandleA",
          time: "visible time A",
          visible: true,
        },
        {
          domSnippet:
            '<article data-abusewatch-comment="true"><span data-abusewatch-handle="true">publicHandleB</span><p>another visible public comment</p></article>',
          textContent: "another visible public comment",
          handle: "publicHandleB",
          time: "visible time B",
          visible: true,
        },
      ],
    })

    // When: the content script runs.
    const redirectedUrl = new URL(result.locationHref)
    const encodedBatch = redirectedUrl.searchParams.get("captures")
    if (encodedBatch === null) {
      throw new Error("content script did not write captures query")
    }
    const parsed = parseSafeCaptureBatchPayload(JSON.parse(encodedBatch))
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }

    // Then: it redirects only to the local app with one payload per visible comment.
    expect(redirectedUrl.origin).toBe("http://127.0.0.1:4173")
    expect(parsed.payload.captures.map((capture) => capture.selectedText)).toEqual([
      "visible 100% public comment text",
      "another visible public comment",
    ])
    expect(parsed.payload.captures[0]?.domSnippet).toContain("data-abusewatch-comment")
    expect(result.alerts).toEqual([])
  })

  it("executes the shipped content script and skips hidden marked comments", () => {
    // Given: one marked comment is hidden and one marked comment is visible.
    const result = runContentScript({
      selectedText: "",
      comments: [
        {
          domSnippet:
            '<article data-abusewatch-comment="true" hidden><p>hidden marked comment</p></article>',
          textContent: "hidden marked comment",
          handle: "hiddenHandle",
          time: "hidden time",
          visible: false,
        },
        {
          domSnippet:
            '<article data-abusewatch-comment="true"><time>2026-06-27 01:20</time><span data-abusewatch-handle="true">visibleHandle</span><p>visible marked comment</p></article>',
          textContent: "visible marked comment",
          handle: "visibleHandle",
          time: "2026-06-27 01:20",
          visible: true,
        },
      ],
    })

    // When: the content script runs.
    const redirectedUrl = new URL(result.locationHref)
    const encodedBatch = redirectedUrl.searchParams.get("captures")
    if (encodedBatch === null) {
      throw new Error("content script did not write captures query")
    }
    const parsed = parseSafeCaptureBatchPayload(JSON.parse(encodedBatch))
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }

    // Then: only the visible marked comment is handed to the app.
    expect(parsed.payload.captures).toHaveLength(1)
    expect(parsed.payload.captures[0]?.publicHandle).toBe("visibleHandle")
    expect(parsed.payload.captures[0]?.domSnippet).toContain("<time>2026-06-27 01:20</time>")
    expect(parsed.payload.captures[0]?.selectedText).not.toContain("hidden marked comment")
  })

  it("executes the shipped content script and omits hidden descendant text", () => {
    // Given: a visible marked comment contains a hidden child node.
    const result = runContentScript({
      selectedText: "",
      comments: [
        {
          domSnippet:
            '<article data-abusewatch-comment="true"><p>visible descendant text</p><span style="display:none">hidden descendant text</span></article>',
          textContent: "visible descendant text",
          hiddenText: "hidden descendant text",
          handle: "visibleHandle",
          time: "visible time",
          visible: true,
        },
      ],
    })

    // When: the content script runs.
    const redirectedUrl = new URL(result.locationHref)
    const encodedBatch = redirectedUrl.searchParams.get("captures")
    if (encodedBatch === null) {
      throw new Error("content script did not write captures query")
    }
    const parsed = parseSafeCaptureBatchPayload(JSON.parse(encodedBatch))
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }

    // Then: selected text includes only visible descendant text.
    expect(parsed.payload.captures[0]?.selectedText).toBe("visible descendant text")
    expect(parsed.payload.captures[0]?.selectedText).not.toContain("hidden descendant text")
  })

  it("executes the shipped content script and omits hidden handle and time descendants", () => {
    // Given: visible handle and time elements contain hidden child text.
    const result = runContentScript({
      selectedText: "",
      comments: [
        {
          domSnippet:
            '<article data-abusewatch-comment="true"><time data-abusewatch-time="true">2026-06-27 01:20<span style="display:none">hidden time</span></time><span data-abusewatch-handle="true">visibleHandle<span style="display:none">hidden handle</span></span><p>visible comment</p></article>',
          textContent: "visible comment",
          handle: "visibleHandle",
          hiddenHandleText: "hidden handle",
          time: "2026-06-27 01:20",
          hiddenTimeText: "hidden time",
          visible: true,
        },
      ],
    })

    // When: the content script runs.
    const redirectedUrl = new URL(result.locationHref)
    const encodedBatch = redirectedUrl.searchParams.get("captures")
    if (encodedBatch === null) {
      throw new Error("content script did not write captures query")
    }
    const parsed = parseSafeCaptureBatchPayload(JSON.parse(encodedBatch))
    if (!parsed.ok) {
      throw new Error(parsed.reason)
    }

    // Then: handle, time, and snippet contain only visible descendant text.
    const capture = parsed.payload.captures[0]
    expect(capture?.publicHandle).toBe("visibleHandle")
    expect(capture?.visibleTimestamp).toBe("2026-06-27 01:20")
    expect(capture?.domSnippet).not.toContain("hidden handle")
    expect(capture?.domSnippet).not.toContain("hidden time")
  })

  it("executes the shipped content script and blocks unsafe captures", () => {
    // Given: unsafe account chrome in the active tab.
    const result = runContentScript({
      selectedText: "Contact sample@example.test",
      comments: [
        {
          domSnippet:
            '<form data-account-chrome="true"><input type="hidden" value="secret"></form>',
          textContent: "Contact sample@example.test",
          handle: "publicHandle",
          time: "visible time",
          visible: true,
        },
      ],
    })

    // When: the content script evaluates the capture.
    // Then: it blocks locally before app handoff.
    expect(result.locationHref).toBe("https://news.example.test/view/123")
    expect(result.alerts).toEqual(["AbuseWatch 캡처 차단: 표시된 공개 댓글 영역만 선택해 주세요."])
  })
})
