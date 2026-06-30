import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export const createConfig = () =>
  defineConfig({
    base: process.env.ABUSEWATCH_BASE_PATH ?? "/",
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
    },
    preview: {
      host: "127.0.0.1",
      port: 4173,
      strictPort: true,
    },
  })

export const config = createConfig()

export default config
