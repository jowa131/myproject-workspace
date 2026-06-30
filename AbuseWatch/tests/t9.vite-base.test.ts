import { describe, expect, it } from "vitest"

describe("Vite deployment base", () => {
  it("uses the configured subpath for protected yulchive deployment", async () => {
    const previousBasePath = process.env.ABUSEWATCH_BASE_PATH
    process.env.ABUSEWATCH_BASE_PATH = "/abusewatch/"

    try {
      const { createConfig } = await import("../vite.config")
      expect(createConfig().base).toBe("/abusewatch/")
    } finally {
      if (previousBasePath === undefined) {
        process.env.ABUSEWATCH_BASE_PATH = undefined
      } else {
        process.env.ABUSEWATCH_BASE_PATH = previousBasePath
      }
    }
  })
})
