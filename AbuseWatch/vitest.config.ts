import { defineConfig } from "vitest/config"

export const config = defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
})

export default config
