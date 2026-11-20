/** 应用预览：生成短期预览链接，内嵌 iframe 或新窗口打开沙箱子域。 */

import { ExternalLink, Play } from "lucide-react";
import { useState } from "react";
import { errorMessage, toMessage } from "../../api/errors";

export function PreviewPanel({
  sessionId,
  token,
  httpOrigin,
}: {
  sessionId: string;
  token: string;
  httpOrigin: string;
}) {
  const [port, setPort] = useState("3000");
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setError(null);
    const value = Number(port);
    if (!Number.isInteger(value) || value < 1024 || value > 65535) {
      setError("端口需在 1024–65535 之间");
      return;
    }
    setLoading(true);
    try {
      const query = new URLSearchParams({ token });
      const response = await fetch(
        `${httpOrigin.replace(/\/$/, "")}/api/sessions/${encodeURIComponent(sessionId)}/preview?${query.toString()}`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ port: value }),
        },
      );
      if (!response.ok) {
        throw new Error(await errorMessage(response));
      }
      const body = (await response.json()) as { url?: string };
      if (typeof body.url !== "string") {
        throw new Error("预览响应缺少 url");
      }
      setUrl(body.url);
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col text-xs">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <label className="text-muted" htmlFor="preview-port">
          端口
        </label>
        <input
          id="preview-port"
          aria-label="预览端口"
          className="w-20 rounded border border-border bg-surface px-2 py-1 font-mono text-[11px] outline-none focus:border-accent"
          value={port}
          onChange={(event) => {
            setPort(event.target.value);
          }}
        />
        <button
          type="button"
          className="flex items-center gap-1 rounded bg-accent px-2 py-1 text-[11px] font-medium text-accent-foreground disabled:opacity-50"
          disabled={loading}
          onClick={() => {
            void generate();
          }}
        >
          <Play size={12} aria-hidden="true" />
          {loading ? "生成中…" : "生成预览链接"}
        </button>
        {url !== null ? (
          <a
            className="ml-auto flex items-center gap-1 text-accent hover:underline"
            href={url}
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={12} aria-hidden="true" />
            新窗口打开
          </a>
        ) : null}
      </div>
      {error !== null ? <p className="p-3 text-red-400">{error}</p> : null}
      {url === null ? (
        <div className="flex flex-1 items-center justify-center p-6 text-center text-muted">
          <p>
            在终端里启动应用（如 <span className="font-mono">pnpm dev --port 3000</span>
            ），再生成预览链接。预览地址带短期票据，仅本次会话可用。
          </p>
        </div>
      ) : (
        <div className="min-h-0 flex-1 bg-white">
          <iframe title="应用预览" src={url} className="h-full w-full border-0" />
        </div>
      )}
    </div>
  );
}
