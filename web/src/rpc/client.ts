/** Codex app-server JSON-RPC 客户端：请求/响应关联、服务端请求与通知分发。 */

export type JsonRpcId = string | number;

export interface JsonRpcError {
  code: number;
  message: string;
}

export interface JsonRpcMessage {
  id?: JsonRpcId;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: JsonRpcError;
}

export interface RpcTransport {
  send(payload: string): void;
  close(): void;
  setHandlers(handlers: { onMessage: (payload: string) => void; onClose: () => void }): void;
}

export class RpcError extends Error {
  readonly code: number;

  constructor(error: JsonRpcError) {
    super(error.message);
    this.name = "RpcError";
    this.code = error.code;
  }
}

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export class CodexRpcClient {
  private nextId = 1;
  private readonly pending = new Map<string, PendingRequest>();
  private readonly listeners = new Set<(message: JsonRpcMessage) => void>();
  private closed = false;

  constructor(private readonly transport: RpcTransport) {
    transport.setHandlers({
      onMessage: (payload) => {
        this.handleMessage(payload);
      },
      onClose: () => {
        this.failPending(new Error("连接已关闭"));
      },
    });
  }

  request<T>(method: string, params: unknown, timeoutMs = 60_000): Promise<T> {
    if (this.closed) {
      return Promise.reject(new Error("连接已关闭"));
    }
    const id = this.nextId;
    this.nextId += 1;
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(String(id));
        reject(new Error(`请求超时：${method}`));
      }, timeoutMs);
      this.pending.set(String(id), {
        resolve: (value) => {
          resolve(value as T);
        },
        reject,
        timer,
      });
      try {
        this.transport.send(JSON.stringify({ id, method, params }));
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(String(id));
        reject(error instanceof Error ? error : new Error(String(error)));
      }
    });
  }

  notify(method: string, params: unknown): void {
    this.transport.send(JSON.stringify({ method, params }));
  }

  /** 应答服务端发起的请求（审批、工具调用等）。 */
  respond(id: JsonRpcId, result: unknown): void {
    this.transport.send(JSON.stringify({ id, result }));
  }

  subscribe(listener: (message: JsonRpcMessage) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  handleMessage(payload: string): void {
    let message: JsonRpcMessage;
    try {
      message = JSON.parse(payload) as JsonRpcMessage;
    } catch {
      return;
    }
    if (message.id !== undefined && message.method === undefined) {
      const pending = this.pending.get(String(message.id));
      if (pending !== undefined) {
        clearTimeout(pending.timer);
        this.pending.delete(String(message.id));
        if (message.error !== undefined) {
          pending.reject(new RpcError(message.error));
        } else {
          pending.resolve(message.result);
        }
        return;
      }
    }
    for (const listener of this.listeners) {
      listener(message);
    }
  }

  dispose(): void {
    this.closed = true;
    this.failPending(new Error("客户端已关闭"));
    this.transport.close();
  }

  private failPending(error: Error): void {
    for (const [id, pending] of this.pending) {
      clearTimeout(pending.timer);
      pending.reject(error);
      this.pending.delete(id);
    }
  }
}

/** 浏览器 WebSocket 传输：未 open 前排队，避免初始化请求丢失。 */
export function createWebSocketTransport(url: string): RpcTransport {
  const socket = new WebSocket(url);
  let handlers: { onMessage: (payload: string) => void; onClose: () => void } = {
    onMessage: () => undefined,
    onClose: () => undefined,
  };
  const queue: string[] = [];

  socket.addEventListener("open", () => {
    for (const payload of queue.splice(0)) {
      socket.send(payload);
    }
  });
  socket.addEventListener("message", (event) => {
    handlers.onMessage(String(event.data));
  });
  socket.addEventListener("close", () => {
    handlers.onClose();
  });

  return {
    send(payload: string): void {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(payload);
      } else {
        queue.push(payload);
      }
    },
    close(): void {
      socket.close();
    },
    setHandlers(next): void {
      handlers = next;
    },
  };
}
