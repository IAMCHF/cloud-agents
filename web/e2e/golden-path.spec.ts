import { expect, test } from "@playwright/test";

const SESSION_URL = "/?session=e2e-session&token=e2e-token&ws=ws://127.0.0.1:8800";

test("金路径：派任务 → 流式回显 → 审批 → 完成", async ({ page }) => {
  await page.goto(SESSION_URL);
  await expect(page.getByText("已连接")).toBeVisible();

  await page.getByLabel("任务描述").fill("修复登录接口的空指针");
  await page.getByRole("button", { name: /发送/ }).click();

  await expect(page.getByText("修复登录接口的空指针")).toBeVisible();
  await expect(page.getByText("正在执行任务…")).toBeVisible();
  await expect(page.getByTestId("diff-view")).toBeVisible();
  await expect(page.getByText(/\+hello/)).toBeVisible();
  await expect(page.getByText("执行命令")).toBeVisible();

  const approval = page.getByText("/bin/echo hello");
  await expect(approval).toBeVisible();
  await page.getByRole("button", { name: /允许一次/ }).click();

  await expect(page.getByText("命令已批准，任务完成。")).toBeVisible();
  await expect(approval).toHaveCount(0);
});

test("审批前关闭页面再打开，未决审批仍会补发", async ({ page }) => {
  await page.goto(SESSION_URL);
  await expect(page.getByText("已连接")).toBeVisible();
  await page.getByLabel("任务描述").fill("跑个命令");
  await page.getByRole("button", { name: /发送/ }).click();
  await expect(page.getByText("/bin/echo hello")).toBeVisible();

  await page.close();
  const reopened = await page.context().newPage();
  await reopened.goto(SESSION_URL);

  await expect(reopened.getByText("/bin/echo hello")).toBeVisible();
});
