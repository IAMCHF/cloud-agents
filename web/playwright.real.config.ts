import { defineConfig } from "@playwright/test";

/** 真模式：不启动 mock 后端，直接打本机已运行的控制面 + Vite。 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /real-model\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"]],
  use: {
    channel: "msedge",
    headless: true,
    trace: "retain-on-failure",
  },
});
