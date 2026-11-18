import { expect, test } from "@playwright/test";

const REAL_URL = process.env.E2E_REAL_SESSION_URL ?? "";

/**
 * 真模式金路径：需要本机已启动 OpenSandbox、控制面、Vite，并通过
 * `E2E_REAL_SESSION_URL="http://127.0.0.1:5173/?session=..&token=..&ws=ws://127.0.0.1:8000"` 指定会话。
 * 未设置时自动跳过，不阻塞 CI。
 */
test.skip(REAL_URL === "", "未设置 E2E_REAL_SESSION_URL，跳过真模式");

test("真实模型：发送任务并看到流式回复", async ({ page }) => {
  await page.goto(REAL_URL);
  await expect(page.getByText("已连接")).toBeVisible({ timeout: 30_000 });

  await page.getByLabel("任务描述").fill("只回复：pong。不要调用任何工具。");
  await page.getByRole("button", { name: /发送/ }).click();

  await expect(page.getByText("pong", { exact: true })).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText("执行中")).toHaveCount(0);

  // 刷新页面会重新握手：真 codex 只允许 initialize 一次，桥接需缓存并本地应答。
  await page.reload();
  await expect(page.getByText("已连接")).toBeVisible({ timeout: 30_000 });
});
