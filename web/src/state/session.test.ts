import { describe, expect, it } from "vitest";
import { CodexRpcClient } from "../rpc/client";
import { FakeTransport } from "../test/fakeTransport";
import { createSessionStore } from "./session";

function setup() {
  const transport = new FakeTransport((message) => {
    if (message.method === "initialize") {
      return { id: message.id, result: { userAgent: "fake-codex/0.167.0" } };
    }
    if (message.method === "thread/start") {
      return { id: message.id, result: { thread: { id: "thr_1" } } };
    }
    if (message.method === "turn/start") {
      return { id: message.id, result: { turn: { id: "turn_1" } } };
    }
    return undefined;
  });
  const client = new CodexRpcClient(transport);
  const store = createSessionStore(client);
  return { transport, client, store };
}

describe("session store", () => {
  it("initializes and starts a thread", async () => {
    const { store } = setup();

    await store.getState().connect();

    expect(store.getState().status).toBe("open");
    expect(store.getState().threadId).toBe("thr_1");
  });

  it("sends a turn and accumulates streaming deltas", async () => {
    const { transport, store } = setup();
    await store.getState().connect();

    await store.getState().send("修一下登录");
    expect(store.getState().turnId).toBe("turn_1");
    expect(store.getState().items.at(-1)).toMatchObject({
      type: "userMessage",
      text: "修一下登录",
    });

    transport.emit({
      method: "item/agentMessage/delta",
      params: { threadId: "thr_1", turnId: "turn_1", itemId: "item_1", delta: "Hel" },
    });
    transport.emit({
      method: "item/agentMessage/delta",
      params: { threadId: "thr_1", turnId: "turn_1", itemId: "item_1", delta: "lo" },
    });

    const item = store.getState().items.find((entry) => entry.id === "item_1");
    expect(item?.text).toBe("Hello");
  });

  it("tracks approvals and responds with the chosen decision", async () => {
    const { transport, store } = setup();
    await store.getState().connect();

    transport.emit({
      id: "approval-1",
      method: "item/commandExecution/requestApproval",
      params: { command: "ls", threadId: "thr_1" },
    });
    const request = store.getState().approvals[0];
    expect(request?.id).toBe("approval-1");

    if (request === undefined) {
      throw new Error("未收到审批请求");
    }
    store.getState().decide(request, "acceptForSession");

    expect(JSON.parse(transport.sent.at(-1) ?? "{}")).toEqual({
      id: "approval-1",
      result: { decision: "acceptForSession" },
    });
    expect(store.getState().approvals).toHaveLength(0);
  });

  it("clears the active turn when it completes", async () => {
    const { transport, store } = setup();
    await store.getState().connect();
    await store.getState().send("hi");
    expect(store.getState().turnId).toBe("turn_1");

    transport.emit({
      method: "turn/completed",
      params: { threadId: "thr_1", turn: { id: "turn_1", status: "completed" } },
    });

    expect(store.getState().turnId).toBeNull();
  });
});

describe("session store edge cases", () => {
  it("refuses to send before the thread exists", async () => {
    const { store } = setup();

    await expect(store.getState().send("hi")).rejects.toThrow("会话未就绪");
  });

  it("surfaces protocol error notifications", async () => {
    const { transport, store } = setup();

    transport.emit({ method: "error", params: { message: "sandbox exited" } });

    expect(store.getState().error).toBe("sandbox exited");
  });

  it("updates the thread id from thread/started notifications", async () => {
    const { transport, store } = setup();

    transport.emit({ method: "thread/started", params: { threadId: "thr_2" } });

    expect(store.getState().threadId).toBe("thr_2");
  });

  it("keeps streamed text when item/completed carries an empty payload", async () => {
    const { transport, store } = setup();
    transport.emit({
      method: "item/started",
      params: { item: { id: "item_9", type: "agentMessage", text: "" } },
    });
    transport.emit({
      method: "item/agentMessage/delta",
      params: { itemId: "item_9", delta: "done" },
    });
    transport.emit({
      method: "item/completed",
      params: { item: { id: "item_9", type: "agentMessage", text: "" } },
    });

    const item = store.getState().items.find((entry) => entry.id === "item_9");
    expect(item?.text).toBe("done");
  });
});

describe("session store robustness", () => {
  it("marks the session as failed when initialization fails", async () => {
    const transport = new FakeTransport((message) => ({
      id: message.id,
      error: { code: -32000, message: "初始化失败" },
    }));
    const store = createSessionStore(new CodexRpcClient(transport));

    await store.getState().connect();

    expect(store.getState().status).toBe("error");
    expect(store.getState().error).toBe("初始化失败");
  });

  it("ignores notifications with missing fields", () => {
    const { transport, store } = setup();

    transport.emit({ method: "thread/started", params: {} });
    transport.emit({ method: "item/started", params: {} });
    transport.emit({ method: "item/agentMessage/delta", params: {} });
    transport.emit({ method: "error", params: {} });

    expect(store.getState().threadId).toBeNull();
    expect(store.getState().items).toHaveLength(0);
    expect(store.getState().error).toBe("未知错误");
  });

  it("rejects a second turn while one is running", async () => {
    const { store } = setup();
    await store.getState().connect();
    await store.getState().send("first");

    await expect(store.getState().send("second")).rejects.toThrow("上一轮尚未完成");
  });
});
