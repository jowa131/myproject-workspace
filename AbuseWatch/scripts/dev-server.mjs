import http from "node:http"
import { createServer as createViteServer } from "vite"

const host = "127.0.0.1"
const port = Number.parseInt(process.env.ABUSE_TRACKER_PORT ?? "4173", 10)

const vite = await createViteServer({
  appType: "spa",
  server: {
    host,
    middlewareMode: true,
  },
})

const server = http.createServer((request, response) => {
  if (request.url === "/api/health") {
    response.writeHead(200, { "content-type": "application/json; charset=utf-8" })
    response.end(
      JSON.stringify({
        ok: true,
        app: "abusewatch",
        mode: "local-first",
        forbiddenAutomation: [
          "comment-crawling",
          "login-automation",
          "captcha-bypass",
          "auto-report",
        ],
      }),
    )
    return
  }

  vite.middlewares(request, response, () => {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" })
    response.end("Not found")
  })
})

server.listen(port, host, () => {
  console.log(`AbuseWatch dev server listening on http://${host}:${port}`)
})

const closeServer = () => {
  server.close(() => {
    void vite.close().then(() => process.exit(0))
  })
}

process.on("SIGINT", closeServer)
process.on("SIGTERM", closeServer)
