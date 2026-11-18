/** 未带会话链接时的入口：token 模式提示手工链接，OIDC 模式登录并新建会话。 */

import { useState } from "react";
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

function OidcEntry({ config }: { config: AuthConfig }) {
  const [accessToken, setAccessToken] = useState<string | null>(() => getAccessToken());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await beginLogin(config);
    } catch (cause) {
      setError(toMessage(cause));
      setBusy(false);
    }
  }

  async function createSession(): Promise<void> {
    if (accessToken === null) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/sessions", {
        method: "POST",
        headers: { authorization: `Bearer ${accessToken}` },
      });
      if (response.status === 401) {
        clearAccessToken();
        setAccessToken(null);
        throw new Error("登录已失效，请重新登录");
      }
      if (!response.ok) {
        throw new Error(`创建会话失败：${response.status} ${await readDetail(response)}`);
      }
      const body = (await response.json()) as { session_id: string; session_token: string };
      const query = new URLSearchParams({
        session: body.session_id,
        token: body.session_token,
      });
      window.location.assign(`/?${query.toString()}`);
    } catch (cause) {
      setError(toMessage(cause));
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl space-y-4 p-8 text-sm text-muted">
      <h1 className="text-lg font-semibold text-foreground">Cloud Agents</h1>
      {accessToken === null ? (
        <>
          <p>使用企业账号登录后即可创建云端会话。</p>
          <button
            type="button"
            className="rounded bg-accent px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={busy}
            onClick={() => void signIn()}
          >
            企业账号登录
          </button>
        </>
      ) : (
        <>
          <p>已登录。创建一个新的云端会话开始工作。</p>
          <button
            type="button"
            className="rounded bg-accent px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={busy}
            onClick={() => void createSession()}
          >
            新建会话
          </button>
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

async function readDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? "";
  } catch {
    return "";
  }
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
