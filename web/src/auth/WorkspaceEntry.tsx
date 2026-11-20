/** 未带会话链接时的入口：token 模式提示手工链接，OIDC 模式登录、建会话与恢复历史会话。 */

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  type CloudSession,
  createCloudSession,
  listCloudSessions,
  resumeCloudSession,
} from "../api/sessions";
import { recallSessionToken, rememberSessionToken } from "../state/tokenStore";
import { type AuthConfig, beginLogin, clearAccessToken, getAccessToken } from "./oidc";

export function SetupHint() {
  return (
    <main className="mx-auto max-w-xl space-y-3 p-8 text-sm text-muted">
      <h1 className="text-lg font-semibold text-foreground">Cloud Agents</h1>
      <p>尚未指定会话。通过会话创建接口拿到链接后打开即可，例如：</p>
      <code className="block overflow-x-auto rounded bg-surface px-3 py-2 text-xs text-foreground">
        /?session=&lt;id&gt;&amp;token=&lt;token&gt;
      </code>
    </main>
  );
}

export function WorkspaceEntry({ config }: { config: AuthConfig }) {
  if (config.mode === "token") {
    return <SetupHint />;
  }
  return <OidcEntry config={config} />;
}

const STATUS_LABEL: Record<string, string> = {
  creating: "创建中",
  running: "运行中",
  idle: "已休眠",
  sleeping: "休眠中",
  ended: "已结束",
};

function OidcEntry({ config }: { config: AuthConfig }) {
  const [accessToken, setAccessToken] = useState<string | null>(() => getAccessToken());
  const [sessions, setSessions] = useState<CloudSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((cause: unknown): void => {
    if (cause instanceof ApiError && cause.status === 401) {
      clearAccessToken();
      setAccessToken(null);
      setError("登录已失效，请重新登录");
      return;
    }
    setError(toMessage(cause));
  }, []);

  const refresh = useCallback(async (): Promise<void> => {
    if (accessToken === null) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setSessions(await listCloudSessions(accessToken));
    } catch (cause) {
      handleError(cause);
    } finally {
      setLoading(false);
    }
  }, [accessToken, handleError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function signIn(): Promise<void> {
    setBusy("login");
    setError(null);
    try {
      await beginLogin(config);
    } catch (cause) {
      handleError(cause);
      setBusy(null);
    }
  }

  async function createSession(): Promise<void> {
    if (accessToken === null) {
      return;
    }
    setBusy("create");
    setError(null);
    try {
      const link = await createCloudSession(accessToken);
      rememberSessionToken(link.session_id, link.session_token);
      navigate(link.session_id, link.session_token);
    } catch (cause) {
      handleError(cause);
      setBusy(null);
    }
  }

  async function openSession(session: CloudSession): Promise<void> {
    if (accessToken === null) {
      return;
    }
    if (session.status === "running") {
      const token = recallSessionToken(session.session_id);
      if (token === null) {
        setError("该会话正在运行；请使用创建时的原会话链接打开。");
        return;
      }
      navigate(session.session_id, token);
      return;
    }
    if (session.status === "idle") {
      setBusy(session.session_id);
      setError(null);
      try {
        const link = await resumeCloudSession(accessToken, session.session_id);
        rememberSessionToken(link.session_id, link.session_token);
        navigate(link.session_id, link.session_token);
      } catch (cause) {
        handleError(cause);
        setBusy(null);
      }
      return;
    }
    setError("会话已结束，无法打开。");
  }

  return (
    <main className="mx-auto max-w-3xl space-y-5 p-8 text-sm text-muted">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-foreground">Cloud Agents</h1>
        {accessToken !== null ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-50"
              disabled={loading}
              onClick={() => void refresh()}
            >
              刷新
            </button>
            <button
              type="button"
              className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
              disabled={busy !== null}
              onClick={() => void createSession()}
            >
              {busy === "create" ? "创建中…" : "新建会话"}
            </button>
          </div>
        ) : null}
      </div>

      {accessToken === null ? (
        <>
          <p>使用企业账号登录后即可创建或恢复云端会话。</p>
          <button
            type="button"
            className="rounded bg-accent px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={busy !== null}
            onClick={() => void signIn()}
          >
            企业账号登录
          </button>
        </>
      ) : (
        <>
          <p>
            云端会话（仅显示当前账号的会话）。运行中的会话需要浏览器记得原
            token；休眠会话可一键恢复。
          </p>
          {loading ? (
            <p>正在加载会话…</p>
          ) : sessions.length === 0 ? (
            <p>暂无会话，点击「新建会话」开始。</p>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
              {sessions.map((session) => {
                const canOpen =
                  session.status === "idle" ||
                  (session.status === "running" && recallSessionToken(session.session_id) !== null);
                return (
                  <li
                    key={session.session_id}
                    className="flex items-center justify-between gap-3 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-mono text-xs text-foreground">
                        {session.session_id}
                      </p>
                      <p className="mt-0.5 text-xs text-muted">
                        {STATUS_LABEL[session.status] ?? session.status} ·{" "}
                        {formatTime(session.created_at)}
                        {session.archived_at !== null ? " · 已归档" : ""}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="shrink-0 rounded border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-40"
                      disabled={!canOpen || busy !== null}
                      onClick={() => void openSession(session)}
                    >
                      {busy === session.session_id
                        ? "恢复中…"
                        : session.status === "idle"
                          ? "恢复并打开"
                          : "打开"}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}

      {error !== null ? (
        <p role="alert" className="text-sm text-red-500">
          {error}
        </p>
      ) : null}
    </main>
  );
}

function navigate(sessionId: string, token: string): void {
  const query = new URLSearchParams({ session: sessionId, token });
  window.location.assign(`/?${query.toString()}`);
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
