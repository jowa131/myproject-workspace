import { spawn } from "node:child_process"

const server = spawn("cmd.exe", ["/d", "/s", "/c", "npm.cmd run dev"], {
  cwd: process.cwd(),
  env: makeWindowsSafeEnv({ ABUSE_TRACKER_PORT: "4173" }),
  stdio: ["ignore", "pipe", "pipe"],
  windowsHide: true,
})

let serverOutput = ""
server.stdout.on("data", (chunk) => {
  serverOutput += String(chunk)
})
server.stderr.on("data", (chunk) => {
  serverOutput += String(chunk)
})

await waitForServer()

const testProcess = spawn(
  "cmd.exe",
  ["/d", "/s", "/c", "node_modules\\.bin\\playwright.cmd test"],
  {
    cwd: process.cwd(),
    env: makeWindowsSafeEnv({}),
    stdio: "inherit",
    windowsHide: true,
  },
)

const exitCode = await new Promise((resolve) => {
  testProcess.on("exit", (code) => resolve(code ?? 1))
})

server.kill()
setTimeout(() => {
  if (!server.killed) {
    server.kill("SIGKILL")
  }
}, 1000)

process.exit(Number(exitCode))

async function waitForServer() {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch("http://127.0.0.1:4173/")
      if (response.ok) {
        return
      }
    } catch {
      await sleep(250)
    }
  }
  server.kill()
  throw new Error(`Timed out waiting for dev server.\n${serverOutput}`)
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function makeWindowsSafeEnv(extra) {
  const env = {}
  for (const [key, value] of Object.entries(process.env)) {
    const existingKey = Object.keys(env).find(
      (candidate) => candidate.toLowerCase() === key.toLowerCase(),
    )
    if (existingKey === undefined && value !== undefined) {
      env[key] = value
    }
  }
  return { ...env, ...extra }
}
