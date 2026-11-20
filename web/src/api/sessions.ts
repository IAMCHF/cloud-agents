/** 云端会话管理面：列表、创建、恢复（执行协议仍走原生 WSS JSON-RPC）。 */

export interface CloudSession {
  session_id: string;
  status: string;
  created_at: string;
  ended_at: string | null;
  archived_at: string | null;
}

export interface SessionLink {
  session_id: string;
  session_token: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function listCloudSessions(accessToken: string): Promise<CloudSession[]> {
  const response = await fetch("/api/sessions", {
    headers: { authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw await toApiError(response, "获取会话列表失败");
  }
  return (await response.json()) as CloudSession[];
}

export async function createCloudSession(accessToken: string): Promise<SessionLink> {
  const response = await fetch("/api/sessions", {
    method: "POST",
    headers: { authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw await toApiError(response, "创建会话失败");
  }
  const body = (await response.json()) as SessionLink;
  return { session_id: body.session_id, session_token: body.session_token };
}

export async function resumeCloudSession(
  accessToken: string,
  sessionId: string,
): Promise<SessionLink> {
  const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/resume`, {
    method: "POST",
    headers: { authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw await toApiError(response, "恢复会话失败");
  }
  const body = (await response.json()) as SessionLink;
  return { session_id: body.session_id, session_token: body.session_token };
}

async function toApiError(response: Response, fallback: string): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: string };
    return new ApiError(response.status, body.detail ?? `${fallback}：${response.status}`);
  } catch {
    return new ApiError(response.status, `${fallback}：${response.status}`);
  }
}
