import { useEffect, useMemo, useState } from "react";
import { ChatView } from "./features/chat/ChatView";
import { CodexRpcClient, createWebSocketTransport } from "./rpc/client";
import { createSessionStore, type SessionStore } from "./state/session";

interface Runtime {
  client: CodexRpcClient;
  store: SessionStore;
}

export function App() {
  const config = useMemo(readConfig, []);
  const [runtime, setRuntime] = useState<Runtime | null>(null);

  useEffect(() => {
    if (config === null) {
      return;
    }
    const client = new CodexRpcClient(createWebSocketTransport(config.url));
    const store = createSessionStore(client);
    setRuntime({ client, store });
    void store.getState().connect();
    return () => {
      client.dispose();
      setRuntime(null);
    };
  }, [config]);

  if (config === null) {
    return <SetupHint />;
  }
  if (runtime === null) {
    return <p className="p-8 text-sm text-muted">正在连接云端会话…</p>;
  }
  return <ChatView store={runtime.store} />;
}

function SetupHint() {
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

function readConfig(): { url: string } | null {
  const params = new URLSearchParams(window.location.search);
  const session = params.get("session");
  const token = params.get("token");
  if (session === null || session === "" || token === null || token === "") {
    return null;
  }
  const base = params.get("ws") ?? defaultWebSocketBase();
  const url = `${base.replace(/\/$/, "")}/ws/session/${encodeURIComponent(session)}?token=${encodeURIComponent(token)}`;
  return { url };
}

function defaultWebSocketBase(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}
