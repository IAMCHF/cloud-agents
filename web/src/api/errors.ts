/** 管理面 REST 错误提取：优先取 JSON `detail`，否则退回状态码。 */

export async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}

export function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
