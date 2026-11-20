import { useEffect, useMemo, useState } from "react";
import { type AuthConfig, completeLogin, getAccessToken, loadAuthConfig } from "./auth/oidc";
import { WorkspaceEntry } from "./auth/WorkspaceEntry";
import { ChatView } from "./features/chat/ChatView";
import { CodexRpcClient, createWebSocketTransport } from "./rpc/client";
import { createSessionStore, type SessionStore } from "./state/session";
import { rememberSessionToken } from "./state/tokenStore";

interface Runtime {
  client: CodexRpcClient;
  store: SessionStore;
}

type AuthState =
  | { status: "loading" }
  | { status: "ready"; config: AuthConfig }
  | { status: "error"; message: string };

export function App() {
  const link = useMemo(readSessionLink, []);
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    if (link !== null) {
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const config = await loadAuthConfig();
        if (config.mode === "oidc") {
          await completeLogin(config);
        }
        if (!cancelled) {
          setAuth({ status: "ready", config });
        }
      } catch (error) {
        if (!cancelled) {
          setAuth({ status: "error", message: toMessage(error) });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [link]);

  if (link !== null) {
    return <ChatSession link={link} />;
  }
  if (auth.status === "loading") {
    return <p className="p-8 text-sm text-muted">正在检查登录状态…</p>;
  }
  if (auth.status === "error") {
    return (
      <main className="mx-auto max-w-xl space-y-3 p-8 text-sm">
        <h1 className="text-lg font-semibold text-foreground">Cloud Agents</h1>
        <p role="alert" className="text-red-500">
          {auth.message}
        </p>
        <button
          type="button"
          className="rounded bg-accent px-3 py-2 text-sm text-white"
          onClick={() => window.location.reload()}
        >
          重试
        </button>
      </main>
    );
  }
  return <WorkspaceEntry config={auth.config} />;
}

function ChatSession({ link }: { link: { url: string; sessionId: string; token: string } }) {
  const [runtime, setRuntime] = useState<Runtime | null>(null);

  useEffect(() => {
    rememberSessionToken(link.sessionId, link.token);
    const client = new CodexRpcClient(createWebSocketTransport(link.url));
    const store = createSessionStore(client);
    setRuntime({ client, store });
    void store.getState().connect();
    return () => {
      client.dispose();
      setRuntime(null);
    };
  }, [link]);

  if (runtime === null) {
    return <p className="p-8 text-sm text-muted">正在连接云端会话…</p>;
  }
  return <ChatView store={runtime.store} />;
}

function readSessionLink(): { url: string; sessionId: string; token: string } | null {
  const params = new URLSearchParams(window.location.search);
  const session = params.get("session");
  const token = params.get("token");
  if (session === null || session === "" || token === null || token === "") {
    return null;
  }
  const base = params.get("ws") ?? defaultWebSocketBase();
  const query = new URLSearchParams({ token });
  const accessToken = getAccessToken();
  if (accessToken !== null) {
    query.set("access_token", accessToken);
  }
  return {
    url: `${base.replace(/\/$/, "")}/ws/session/${encodeURIComponent(session)}?${query.toString()}`,
    sessionId: session,
    token,
  };
}

function defaultWebSocketBase(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
