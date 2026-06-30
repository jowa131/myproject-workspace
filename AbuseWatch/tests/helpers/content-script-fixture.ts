import { readFileSync } from "node:fs"
import { Script, createContext } from "node:vm"

export type ContentScriptFixture = {
  readonly selectedText: string
  readonly comments: readonly {
    readonly domSnippet: string
    readonly textContent: string
    readonly hiddenText?: string
    readonly hiddenHandleText?: string
    readonly hiddenTimeText?: string
    readonly handle: string
    readonly time: string
    readonly visible: boolean
  }[]
}

export type ContentScriptResult = {
  readonly locationHref: string
  readonly alerts: readonly string[]
}

export function runContentScript(fixture: ContentScriptFixture): ContentScriptResult {
  const alerts: string[] = []
  const locationState = { href: "https://news.example.test/view/123" }
  const firstComment = fixture.comments[0] ?? null
  const makeCommentNode = (comment: ContentScriptFixture["comments"][number]) => ({
    nodeType: 1,
    outerHTML: comment.domSnippet,
    textContent: comment.textContent,
    childNodes:
      comment.hiddenText === undefined
        ? [makeTextNode(comment.textContent)]
        : [makeTextNode(comment.textContent), makeHiddenNode(comment.hiddenText)],
    hidden: !comment.visible,
    getAttribute: (name: string) => (name === "aria-hidden" && !comment.visible ? "true" : null),
    getClientRects: () => (comment.visible ? [{ width: 120, height: 20 }] : []),
    querySelector: (selector: string) => {
      switch (selector) {
        case "[data-abusewatch-handle]":
          return makeLabeledNode(comment.handle, comment.hiddenHandleText)
        case "[data-abusewatch-time]":
          return makeLabeledNode(comment.time, comment.hiddenTimeText)
        default:
          return null
      }
    },
  })
  const context = createContext({
    window: {
      getSelection: () => fixture.selectedText,
      alert: (message: string) => alerts.push(message),
      getComputedStyle: (element: { readonly getClientRects: () => readonly unknown[] }) => ({
        display: element.getClientRects().length > 0 ? "block" : "none",
        visibility: element.getClientRects().length > 0 ? "visible" : "hidden",
      }),
    },
    Node: {
      TEXT_NODE: 3,
      ELEMENT_NODE: 1,
    },
    document: {
      title: "Opened article",
      querySelector: (selector: string) => {
        switch (selector) {
          case "[data-abusewatch-comment]":
            return firstComment === null ? null : makeCommentNode(firstComment)
          case "[data-abusewatch-handle]":
            return firstComment === null
              ? null
              : makeLabeledNode(firstComment.handle, firstComment.hiddenHandleText)
          case "[data-abusewatch-time]":
            return firstComment === null
              ? null
              : makeLabeledNode(firstComment.time, firstComment.hiddenTimeText)
          default:
            return null
        }
      },
      querySelectorAll: (selector: string) => {
        if (selector !== "[data-abusewatch-comment]") {
          return []
        }
        return fixture.comments.map((comment) => makeCommentNode(comment))
      },
    },
    location: locationState,
  })

  new Script(readFileSync("extension/content-script.js", "utf8")).runInContext(context)

  return {
    locationHref: locationState.href,
    alerts,
  }
}

function makeTextNode(textContent: string) {
  return {
    nodeType: 3,
    textContent,
  }
}

function makeHiddenNode(textContent: string) {
  return {
    nodeType: 1,
    textContent,
    childNodes: [makeTextNode(textContent)],
    hidden: true,
    getAttribute: (name: string) => (name === "aria-hidden" ? "true" : null),
    getClientRects: () => [],
    querySelector: () => null,
  }
}

function makeLabeledNode(textContent: string, hiddenText: string | undefined) {
  return {
    nodeType: 1,
    textContent: hiddenText === undefined ? textContent : `${textContent}${hiddenText}`,
    childNodes:
      hiddenText === undefined
        ? [makeTextNode(textContent)]
        : [makeTextNode(textContent), makeHiddenNode(hiddenText)],
    hidden: false,
    getAttribute: () => null,
    getClientRects: () => [{ width: 80, height: 16 }],
    querySelector: () => null,
  }
}
