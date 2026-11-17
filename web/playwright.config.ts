import { defineConfig } from "@playwright/test";

/** 金路径 mock 模式：Web ↔ 控制面 ↔ 桥接 ↔ fake codex（无沙箱、无真实 LLM）。 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: "http://127.0.0.1:5174",
    channel: "msedge",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "node ../scripts/e2e-stack.mjs",
      url: "http://127.0.0.1:8800/healthz",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
