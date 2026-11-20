/** 文件树：execd `/directories/list` + `/files/download` 的只读浏览与文本预览。 */

import { File, Folder, FolderUp } from "lucide-react";
import { useEffect, useState } from "react";

interface FileEntry {
  path: string;
  type?: string;
  size?: number;
  modified_at?: string;
}

export function FilePanel({
  sessionId,
  token,
  httpOrigin,
}: {
  sessionId: string;
  token: string;
  httpOrigin: string;
}) {
  const [path, setPath] = useState("/workspace");
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [preview, setPreview] = useState<{ path: string; content: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionId === "" || token === "" || httpOrigin === "") {
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    const query = new URLSearchParams({ path, token });
    fetch(
      `${httpOrigin.replace(/\/$/, "")}/api/sessions/${encodeURIComponent(sessionId)}/files?${query.toString()}`,
      {
        signal: controller.signal,
      },
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await errorMessage(response));
        }
        return (await response.json()) as { entries?: FileEntry[] };
      })
      .then((body) => {
        setEntries(sortEntries(body.entries ?? []));
      })
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") {
          return;
        }
        setError(toMessage(cause));
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, [sessionId, token, httpOrigin, path]);

  const openEntry = (entry: FileEntry) => {
    if (isDirectory(entry)) {
      setPreview(null);
      setPath(entry.path);
      return;
    }
    void loadFile(entry.path);
  };

  const loadFile = async (filePath: string) => {
    setError(null);
    const query = new URLSearchParams({ path: filePath, token });
    try {
      const response = await fetch(
        `${httpOrigin.replace(/\/$/, "")}/api/sessions/${encodeURIComponent(sessionId)}/file?${query.toString()}`,
      );
      if (!response.ok) {
        throw new Error(await errorMessage(response));
      }
      setPreview({ path: filePath, content: await response.text() });
    } catch (cause) {
      setError(toMessage(cause));
    }
  };

  const parent = parentPath(path);

  return (
    <div className="flex h-full min-h-0 flex-col text-xs">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <button
          type="button"
          aria-label="上级目录"
          className="rounded p-1 text-muted hover:bg-surface-raised hover:text-foreground disabled:opacity-30"
          disabled={parent === path}
          onClick={() => {
            setPreview(null);
            setPath(parent);
          }}
        >
          <FolderUp size={13} aria-hidden="true" />
        </button>
        <span className="truncate font-mono text-[11px] text-muted">{path}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-1">
        {loading ? <p className="p-2 text-muted">加载中…</p> : null}
        {entries.map((entry) => (
          <button
            key={entry.path}
            type="button"
            className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-muted hover:bg-surface-raised hover:text-foreground"
            onClick={() => openEntry(entry)}
          >
            {isDirectory(entry) ? (
              <Folder size={13} className="shrink-0 text-accent" aria-hidden="true" />
            ) : (
              <File size={13} className="shrink-0" aria-hidden="true" />
            )}
            <span className="truncate">{baseName(entry.path)}</span>
            {!isDirectory(entry) && typeof entry.size === "number" ? (
              <span className="ml-auto shrink-0 text-[10px] text-muted">
                {formatSize(entry.size)}
              </span>
            ) : null}
          </button>
        ))}
        {!loading && entries.length === 0 ? <p className="p-2 text-muted">空目录</p> : null}
      </div>
      {error !== null ? <p className="border-t border-border p-2 text-red-400">{error}</p> : null}
      {preview !== null ? (
        <div className="flex min-h-0 flex-[2] flex-col border-t border-border">
          <div className="flex items-center justify-between px-3 py-1.5 text-[11px] text-muted">
            <span className="truncate font-mono">{preview.path}</span>
            <button
              type="button"
              className="hover:text-foreground"
              onClick={() => setPreview(null)}
            >
              关闭
            </button>
          </div>
          <pre className="min-h-0 flex-1 overflow-auto bg-surface px-3 py-2 text-[11px] leading-relaxed text-foreground">
            {preview.content}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

function isDirectory(entry: FileEntry): boolean {
  return entry.type?.toLowerCase().includes("dir") ?? false;
}

function sortEntries(entries: FileEntry[]): FileEntry[] {
  return [...entries].sort((left, right) => {
    const byType = Number(isDirectory(right)) - Number(isDirectory(left));
    return byType !== 0 ? byType : left.path.localeCompare(right.path);
  });
}

function parentPath(path: string): string {
  const trimmed = path.replace(/\/+$/, "");
  const index = trimmed.lastIndexOf("/");
  return index <= 0 ? "/" : trimmed.slice(0, index);
}

function baseName(path: string): string {
  const trimmed = path.replace(/\/+$/, "");
  const index = trimmed.lastIndexOf("/");
  return trimmed.slice(index + 1) || trimmed;
}

function formatSize(size: number): string {
  if (size < 1024) {
    return `${size}B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)}K`;
  }
  return `${(size / 1024 / 1024).toFixed(1)}M`;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `请求失败：${response.status}`;
  } catch {
    return `请求失败：${response.status}`;
  }
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
