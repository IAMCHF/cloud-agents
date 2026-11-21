import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeTransport } from "../test/fakeTransport";
import { FakeWebSocket } from "../test/fakeWebSocket";
import type { JsonRpcMessage } from "./client";
import { CodexRpcClient, createWebSocketTransport, RpcError } from "./client";

describe("CodexRpcClient", () => {
  it("resolves responses by id and dispatches server requests", async () => {
    const transport = new FakeTransport((message) =>
      message.method === "initialize" ? { id: message.id, result: { ok: true } } : undefined,
    );
    const client = new CodexRpcClient(transport);
    const seen: JsonRpcMessage[] = [];
    client.subscribe((message) => {
      seen.push(message);
    });

    const result = await client.request<{ ok: boolean }>("initialize", { clientInfo: {} });
    expect(result.ok).toBe(true);

    transport.emit({
      id: 9,
      method: "item/commandExecution/requestApproval",
      params: { command: "ls" },
    });
    expect(seen[0]?.id).toBe(9);
    expect(seen[0]?.method).toBe("item/commandExecution/requestApproval");
  });

  it("rejects with RpcError on error responses", async () => {
    const transport = new FakeTransport((message) => ({
      id: message.id,
      error: { code: -32601, message: "unknown method" },
    }));
    const client = new CodexRpcClient(transport);

    await expect(client.request("nope", {})).rejects.toBeInstanceOf(RpcError);
  });

  it("rejects pending requests when the transport closes", async () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);

    const pending = client.request("initialize", {});
    transport.drop();

    await expect(pending).rejects.toThrow("连接已关闭");
  });

  it("ignores malformed frames without throwing", () => {
    const transport = new FakeTransport();
    new CodexRpcClient(transport);

    expect(() => {
      transport.emitRaw("not json");
    }).not.toThrow();
  });

  it("times out unanswered requests", async () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);

    await expect(client.request("initialize", {}, 20)).rejects.toThrow("请求超时");
  });

  it("sends responses and notifications as JSON-RPC", () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);

    client.respond("a1", { decision: "accept" });
    client.notify("thread/start", {});

    expect(JSON.parse(transport.sent[0] ?? "{}")).toEqual({
      id: "a1",
      result: { decision: "accept" },
    });
    expect(JSON.parse(transport.sent[1] ?? "{}")).toEqual({
      method: "thread/start",
      params: {},
    });
  });
});

describe("createWebSocketTransport", () => {
  beforeEach(() => {
    FakeWebSocket.reset();
    vi.stubGlobal("WebSocket", FakeWebSocket);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("queues frames until open and then relays both directions", () => {
    const transport = createWebSocketTransport("ws://example/ws/session/s?token=t");
    const received: string[] = [];
    let closed = false;
    transport.setHandlers({
      onMessage: (payload) => {
        received.push(payload);
      },
      onClose: () => {
        closed = true;
      },
    });

    transport.send("queued");
    const socket = FakeWebSocket.instances[0];
    expect(socket?.sent).toEqual([]);

    socket?.open();
    expect(socket?.sent).toEqual(["queued"]);

    transport.send("direct");
    expect(socket?.sent).toEqual(["queued", "direct"]);

    socket?.message('{"method":"turn/started"}');
    expect(received).toEqual(['{"method":"turn/started"}']);

    transport.close();
    expect(closed).toBe(true);
  });

  it("retries handshake failures with backoff and flushes queued frames", () => {
    vi.useFakeTimers();
    try {
      const transport = createWebSocketTransport("ws://example/ws/session/s?token=t", {
        retryDelayMs: 100,
      });
      transport.send("hello");
      FakeWebSocket.instances[0]?.close();
      expect(FakeWebSocket.instances).toHaveLength(1);

      vi.advanceTimersByTime(100);
      expect(FakeWebSocket.instances).toHaveLength(2);
      FakeWebSocket.instances[1]?.open();
      expect(FakeWebSocket.instances[1]?.sent).toEqual(["hello"]);

      transport.close();
      vi.advanceTimersByTime(1000);
      expect(FakeWebSocket.instances).toHaveLength(2);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("CodexRpcClient failure modes", () => {
  it("rejects immediately after dispose", async () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);
    client.dispose();

    await expect(client.request("initialize", {})).rejects.toThrow("连接已关闭");
  });

  it("rejects when the transport throws while sending", async () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);
    transport.send = () => {
      throw new Error("socket exploded");
    };

    await expect(client.request("initialize", {})).rejects.toThrow("socket exploded");
  });

  it("forwards responses with unknown ids to subscribers", () => {
    const transport = new FakeTransport();
    const client = new CodexRpcClient(transport);
    const seen: JsonRpcMessage[] = [];
    client.subscribe((message) => {
      seen.push(message);
    });

    transport.emit({ id: "unknown", result: {} });

    expect(seen).toHaveLength(1);
  });
});
