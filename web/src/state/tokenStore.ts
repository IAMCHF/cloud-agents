/** 浏览器侧会话 token 记忆：仅用于打开仍在运行/已恢复的会话；不替代服务端鉴权。 */

const KEY = "cloud-agents.session-tokens";

function readAll(): Record<string, string> {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(KEY) ?? "{}") as unknown;
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

export function rememberSessionToken(sessionId: string, token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const all = readAll();
  all[sessionId] = token;
  window.localStorage.setItem(KEY, JSON.stringify(all));
}

export function recallSessionToken(sessionId: string): string | null {
  return readAll()[sessionId] ?? null;
}
