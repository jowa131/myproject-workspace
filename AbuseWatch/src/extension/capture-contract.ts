import { parseSafeCaptureBatchPayload, parseSafeCapturePayload } from "../domain/capture"
import type { CaptureBatchPayload, CapturePayload } from "../domain/contracts"

export type ExtensionCaptureInput = {
  readonly appUrl: string
  readonly candidateUrlId: string
  readonly pageUrl: string
  readonly pageTitle: string
  readonly selectedText: string
  readonly publicHandle: string
  readonly visibleTimestamp: string
  readonly domSnippet: string
  readonly capturedAt: string
}

export type ExtensionCaptureItemInput = Omit<ExtensionCaptureInput, "appUrl">

export type ExtensionCaptureResult = {
  readonly capturePayload: CapturePayload
  readonly redirectUrl: string
}

export type ExtensionCaptureBatchInput = {
  readonly appUrl: string
  readonly captures: readonly ExtensionCaptureItemInput[]
}

export type ExtensionCaptureBatchResult = {
  readonly captureBatchPayload: CaptureBatchPayload
  readonly redirectUrl: string
}

export type ExtensionCaptureDecision =
  | { readonly ok: true }
  | { readonly ok: false; readonly reason: string }

export const extensionManifest = {
  manifest_version: 3,
  name: "AbuseWatch 증거 캡처",
  version: "0.1.0",
  action: {
    default_title: "보이는 증거 저장",
  },
  permissions: ["activeTab", "scripting"],
  host_permissions: [],
  background: {
    service_worker: "background.js",
  },
} as const

export function isExtensionCaptureAllowed(input: {
  readonly selectedText: string
  readonly domSnippet: string
  readonly publicHandle: string
}): ExtensionCaptureDecision {
  const parsed = parseSafeCapturePayload({
    candidateUrlId: "candidate-extension",
    pageUrl: "https://example.test/",
    pageTitle: "Extension safety check",
    selectedText: input.selectedText,
    publicHandle: input.publicHandle,
    visibleTimestamp: "visible time not found",
    domSnippet: input.domSnippet,
    capturedAt: "2026-06-26T00:00:00.000Z",
  })

  if (!parsed.ok) {
    return { ok: false, reason: parsed.reason }
  }

  return { ok: true }
}

export function buildExtensionCapturePayload(input: ExtensionCaptureInput): ExtensionCaptureResult {
  const parsed = parseSafeCapturePayload({
    candidateUrlId: input.candidateUrlId,
    pageUrl: input.pageUrl,
    pageTitle: input.pageTitle,
    selectedText: input.selectedText,
    publicHandle: input.publicHandle,
    visibleTimestamp: input.visibleTimestamp,
    domSnippet: input.domSnippet,
    capturedAt: input.capturedAt,
  })

  if (!parsed.ok) {
    throw new ExtensionCaptureBlockedError(parsed.reason)
  }

  const url = new URL(input.appUrl)
  url.searchParams.set("capture", JSON.stringify(parsed.payload))

  return {
    capturePayload: parsed.payload,
    redirectUrl: url.toString(),
  }
}

export function buildExtensionCaptureBatchPayload(
  input: ExtensionCaptureBatchInput,
): ExtensionCaptureBatchResult {
  const parsed = parseSafeCaptureBatchPayload({
    captures: input.captures.map((capture) => ({
      candidateUrlId: capture.candidateUrlId,
      pageUrl: capture.pageUrl,
      pageTitle: capture.pageTitle,
      selectedText: capture.selectedText,
      publicHandle: capture.publicHandle,
      visibleTimestamp: capture.visibleTimestamp,
      domSnippet: capture.domSnippet,
      capturedAt: capture.capturedAt,
    })),
  })

  if (!parsed.ok) {
    throw new ExtensionCaptureBlockedError(parsed.reason)
  }

  const url = new URL(input.appUrl)
  url.searchParams.set("captures", JSON.stringify(parsed.payload))

  return {
    captureBatchPayload: parsed.payload,
    redirectUrl: url.toString(),
  }
}

export class ExtensionCaptureBlockedError extends Error {
  public readonly reason: string

  public constructor(reason: string) {
    super(reason)
    this.name = "ExtensionCaptureBlockedError"
    this.reason = reason
  }
}
