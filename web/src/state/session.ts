/** 会话状态：把 Codex JSON-RPC 通知归约成对话项、线程/计划与审批请求。 */

import { createStore, type StoreApi } from "zustand/vanilla";
import type { CodexRpcClient, JsonRpcId, JsonRpcMessage } from "../rpc/client";

export type ApprovalDecision = "accept" | "acceptForSession" | "decline" | "cancel";

export interface ChatItem {
  id: string;
  type: string;
  text: string;
}

export interface ThreadSummary {
  id: string;
  name: string | null;
  preview: string;
  updatedAt: number;
}

export interface PlanStep {
  status: "pending" | "inProgress" | "completed";
  step: string;
}

export interface ApprovalRequest {
  id: JsonRpcId;
  method: string;
  params: Record<string, unknown>;
}

export type SessionStatus = "connecting" | "open" | "error" | "closed";

export interface SessionState {
  status: SessionStatus;
  threadId: string | null;
  turnId: string | null;
  items: ChatItem[];
  threads: ThreadSummary[];
  plan: PlanStep[];
  diff: string;
  approvals: ApprovalRequest[];
  error: string | null;
  connect: () => Promise<void>;
  send: (text: string) => Promise<void>;
  decide: (request: ApprovalRequest, decision: ApprovalDecision) => void;
  resumeThread: (threadId: string, clearApprovals?: boolean) => Promise<void>;
  newThread: (clearApprovals?: boolean) => Promise<void>;
  handleMessage: (message: JsonRpcMessage) => void;
}

export type SessionStore = StoreApi<SessionState>;

interface ThreadPayload {
  id?: string;
  turns?: Array<{ items?: Array<Record<string, unknown>> }>;
}

export function createSessionStore(client: CodexRpcClient): SessionStore {
  const store = createStore<SessionState>()((set, get) => ({
    status: "connecting",
    threadId: null,
    turnId: null,
    items: [],
    threads: [],
    plan: [],
    diff: "",
    approvals: [],
    error: null,

    async connect(): Promise<void> {
      set({ status: "connecting", error: null });
      try {
        await client.request("initialize", {
          clientInfo: { name: "cloud-agents-web", version: "0.1.0" },
        });
        const listed = await client.request<{ data?: ThreadSummary[] }>("thread/list", {
          limit: 50,
        });
        const threads = listed.data ?? [];
        set({ threads });
        const latest = threads[0];
        if (latest === undefined) {
          await get().newThread();
        } else {
          await get().resumeThread(latest.id);
        }
      } catch (error) {
        set({ status: "error", error: toMessage(error) });
      }
    },

    async send(text: string): Promise<void> {
      const { threadId, turnId, items } = get();
      if (threadId === null) {
        throw new Error("会话未就绪");
      }
      if (turnId !== null) {
        throw new Error("上一轮尚未完成");
      }
      const localItem: ChatItem = {
        id: `local-${Date.now()}`,
        type: "userMessage",
        text,
      };
      set({ items: [...items, localItem], error: null, diff: "", plan: [] });
      try {
        const started = await client.request<{ turn?: { id?: string } }>("turn/start", {
          threadId,
          input: [{ type: "text", text }],
        });
        set({ turnId: started.turn?.id ?? null });
      } catch (error) {
        set({ error: toMessage(error) });
        throw error;
      }
    },

    decide(request: ApprovalRequest, decision: ApprovalDecision): void {
      client.respond(request.id, { decision });
      set({ approvals: get().approvals.filter((item) => item.id !== request.id) });
    },

    async resumeThread(threadId: string, clearApprovals = false): Promise<void> {
      set({ status: "connecting", error: null });
      try {
        const result = await client.request<{ thread?: ThreadPayload }>("thread/resume", {
          threadId,
        });
        const thread = result.thread ?? {};
        const items = (thread.turns ?? []).flatMap((turn) =>
          (turn.items ?? []).map(toChatItem).filter((item): item is ChatItem => item !== null),
        );
        set({
          status: "open",
          threadId: thread.id ?? threadId,
          turnId: null,
          items,
          approvals: clearApprovals ? [] : get().approvals,
          diff: "",
          plan: [],
          threads: touchThread(get().threads, thread.id ?? threadId),
        });
      } catch (error) {
        set({ status: "error", error: toMessage(error) });
        throw error;
      }
    },

    async newThread(clearApprovals = false): Promise<void> {
      const result = await client.request<{ thread?: { id?: string } }>("thread/start", {});
      const id = result.thread?.id;
      set({
        status: "open",
        threadId: id ?? null,
        turnId: null,
        items: [],
        approvals: clearApprovals ? [] : get().approvals,
        diff: "",
        plan: [],
        threads:
          id === undefined
            ? get().threads
            : upsertThread(get().threads, {
                id,
                name: null,
                preview: "新线程",
                updatedAt: nowSeconds(),
              }),
      });
    },

    handleMessage(message: JsonRpcMessage): void {
      const method = message.method;
      if (method === undefined) {
        return;
      }
      const params = asRecord(message.params);
      if (message.id !== undefined) {
        // 服务端发起的请求：审批 / 工具调用 / 追问。
        set({ approvals: [...get().approvals, { id: message.id, method, params }] });
        return;
      }
      switch (method) {
        case "thread/started": {
          const threadId = asString(params.threadId);
          if (threadId !== null) {
            set({
              threadId,
              threads: upsertThread(get().threads, {
                id: threadId,
                name: null,
                preview: "新线程",
                updatedAt: nowSeconds(),
              }),
            });
          }
          break;
        }
        case "turn/started": {
          const turn = asRecord(params.turn);
          set({ turnId: asString(turn.id), status: "open", diff: "", plan: [] });
          break;
        }
        case "turn/diff/updated": {
          set({ diff: asString(params.diff) ?? "" });
          break;
        }
        case "turn/plan/updated": {
          set({ plan: toPlan(params.plan) });
          break;
        }
        case "turn/completed": {
          set({ turnId: null });
          break;
        }
        case "item/started":
        case "item/completed": {
          const item = toChatItem(asRecord(params.item));
          if (item !== null) {
            set({ items: upsertItem(get().items, item) });
          }
          break;
        }
        case "item/agentMessage/delta": {
          const itemId = asString(params.itemId);
          const delta = asString(params.delta);
          if (itemId !== null && delta !== null) {
            set({ items: appendDelta(get().items, itemId, delta) });
          }
          break;
        }
        case "error": {
          set({ error: asString(params.message) ?? "未知错误" });
          break;
        }
        default:
          break;
      }
    },
  }));

  client.subscribe((message) => {
    store.getState().handleMessage(message);
  });
  return store;
}

function upsertItem(items: ChatItem[], item: ChatItem): ChatItem[] {
  const index = items.findIndex((existing) => existing.id === item.id);
  if (index === -1) {
    return [...items, item];
  }
  const next = [...items];
  const previous = next[index];
  next[index] = { ...item, text: item.text === "" ? (previous?.text ?? "") : item.text };
  return next;
}

function appendDelta(items: ChatItem[], itemId: string, delta: string): ChatItem[] {
  const index = items.findIndex((item) => item.id === itemId);
  if (index === -1) {
    return [...items, { id: itemId, type: "agentMessage", text: delta }];
  }
  const next = [...items];
  const current = next[index];
  if (current === undefined) {
    return next;
  }
  next[index] = { ...current, text: current.text + delta };
  return next;
}

function upsertThread(threads: ThreadSummary[], thread: ThreadSummary): ThreadSummary[] {
  const index = threads.findIndex((item) => item.id === thread.id);
  if (index === -1) {
    return [thread, ...threads];
  }
  const next = [...threads];
  next[index] = { ...next[index], ...thread };
  return next;
}

function touchThread(threads: ThreadSummary[], threadId: string): ThreadSummary[] {
  return threads.map((thread) =>
    thread.id === threadId ? { ...thread, updatedAt: nowSeconds() } : thread,
  );
}

function toChatItem(value: Record<string, unknown>): ChatItem | null {
  const id = asString(value.id);
  const type = asString(value.type);
  if (id === null || type === null) {
    return null;
  }
  return { id, type, text: itemText(value) };
}

function itemText(value: Record<string, unknown>): string {
  const text = asString(value.text);
  if (text !== null) {
    return text;
  }
  const content = value.content;
  if (!Array.isArray(content)) {
    return "";
  }
  return content
    .map((part) => {
      const record = asRecord(part);
      return asString(record.text) ?? "";
    })
    .join("");
}

function toPlan(value: unknown): PlanStep[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((step) => {
      const record = asRecord(step);
      const label = asString(record.step);
      if (label === null) {
        return null;
      }
      const rawStatus = asString(record.status);
      const status: PlanStep["status"] =
        rawStatus === "completed"
          ? "completed"
          : rawStatus === "inProgress"
            ? "inProgress"
            : "pending";
      return { status, step: label };
    })
    .filter((step): step is PlanStep => step !== null);
}

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function toMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
