import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CodexRpcClient } from "../../rpc/client";
import { createSessionStore } from "../../state/session";
import { FakeTransport } from "../../test/fakeTransport";
import { ChatView } from "./ChatView";

function setup() {
  const transport = new FakeTransport();
  const client = new CodexRpcClient(transport);
  const store = createSessionStore(client);
  return { transport, store };
}

describe("ChatView", () => {
  it("renders streamed agent messages and sends approval decisions", async () => {
    const { transport, store } = setup();
    act(() => {
      transport.emit({
        method: "item/started",
        params: { item: { id: "item_1", type: "agentMessage", text: "" } },
      });
      transport.emit({
        method: "item/agentMessage/delta",
        params: { itemId: "item_1", delta: "已定位到空指针，准备修复。" },
      });
      transport.emit({
        id: "approval-1",
        method: "item/commandExecution/requestApproval",
        params: { command: "pnpm test", cwd: "/workspace" },
      });
    });

    render(<ChatView store={store} />);
    expect(screen.getByText("已定位到空指针，准备修复。")).toBeInTheDocument();
    expect(screen.getByText("pnpm test")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /允许一次/ }));

    expect(JSON.parse(transport.sent.at(-1) ?? "{}")).toEqual({
      id: "approval-1",
      result: { decision: "accept" },
    });
    expect(screen.queryByText("pnpm test")).not.toBeInTheDocument();
  });

  it("shows an empty-state hint before the first task", () => {
    const { store } = setup();

    render(<ChatView store={store} />);

    expect(screen.getByText(/描述一个编码任务/)).toBeInTheDocument();
  });
});

describe("ChatView interactions", () => {
  it("submits the composer text as a turn", async () => {
    const { transport, store } = setup();
    act(() => {
      store.setState({ status: "open", threadId: "thr_1" });
    });
    render(<ChatView store={store} />);

    await userEvent.type(screen.getByLabelText("任务描述"), "补一个回归测试");
    await userEvent.click(screen.getByRole("button", { name: /发送/ }));

    const sent = transport.sent.map((payload) => JSON.parse(payload) as Record<string, unknown>);
    const turn = sent.find((message) => message.method === "turn/start");
    expect(turn?.params).toMatchObject({ threadId: "thr_1" });
  });

  it("shows protocol errors and file approval prompts", () => {
    const { transport, store } = setup();
    act(() => {
      transport.emit({
        id: "file-1",
        method: "item/fileChange/requestApproval",
        params: { grantRoot: "/workspace/src" },
      });
      transport.emit({ method: "error", params: { message: "上游超时" } });
    });

    render(<ChatView store={store} />);

    expect(screen.getByText(/允许在 \/workspace\/src 下写入文件/)).toBeInTheDocument();
    expect(screen.getByText("上游超时")).toBeInTheDocument();
  });
});

describe("ChatView states", () => {
  it("disables sending while a turn is running", () => {
    const { store } = setup();
    act(() => {
      store.setState({ status: "open", threadId: "thr_1", turnId: "turn_1" });
    });

    render(<ChatView store={store} />);

    expect(screen.getByRole("button", { name: /发送/ })).toBeDisabled();
    expect(screen.getByText("执行中")).toBeInTheDocument();
  });

  it("renders unknown server requests with their reason", () => {
    const { transport, store } = setup();
    act(() => {
      transport.emit({
        id: "ask-1",
        method: "item/tool/requestUserInput",
        params: { reason: "选择目标分支" },
      });
    });

    render(<ChatView store={store} />);

    expect(screen.getByText("选择目标分支")).toBeInTheDocument();
    expect(screen.getByText("需要确认")).toBeInTheDocument();
  });
});

describe("ChatView side panels", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("explains that terminal and files need a connected session", async () => {
    const { store } = setup();

    render(<ChatView store={store} />);

    await userEvent.click(screen.getByRole("button", { name: "终端" }));
    expect(screen.getByText("会话未连接，终端不可用。")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "文件" }));
    expect(screen.getByText("会话未连接，文件树不可用。")).toBeInTheDocument();
  });

  it("mounts the file panel when session credentials are available", async () => {
    const { store } = setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ entries: [] }), { status: 200 })),
    );

    render(
      <ChatView
        store={store}
        sessionId="s1"
        token="t1"
        wsOrigin="ws://cp:8000"
        httpOrigin="http://cp:8000"
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "文件" }));
    expect(await screen.findByText("空目录")).toBeInTheDocument();
  });
});
