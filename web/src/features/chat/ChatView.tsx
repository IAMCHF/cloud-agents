import { FileText, MessageSquare, Plus, SendHorizontal, Terminal } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { useStore } from "zustand";
import type {
  ApprovalDecision,
  ApprovalRequest,
  ChatItem,
  PlanStep,
  SessionStore,
  ThreadSummary,
} from "../../state/session";
import { DiffView } from "../diff/DiffView";
import { PreviewPanel } from "../preview/PreviewPanel";
import { FilePanel } from "../terminal/FilePanel";
import { TerminalPanel } from "../terminal/TerminalPanel";
import { ApprovalActions, ApprovalCard } from "./ApprovalCard";
import { MarkdownText } from "./MarkdownText";

type RightPanel = "diff" | "terminal" | "files" | "preview";

export function ChatView({
  store,
  sessionId,
  token,
  wsOrigin,
  httpOrigin,
}: {
  store: SessionStore;
  sessionId?: string;
  token?: string;
  wsOrigin?: string;
  httpOrigin?: string;
}) {
  const status = useStore(store, (state) => state.status);
  const items = useStore(store, (state) => state.items);
  const approvals = useStore(store, (state) => state.approvals);
  const error = useStore(store, (state) => state.error);
  const turnId = useStore(store, (state) => state.turnId);
  const threads = useStore(store, (state) => state.threads);
  const threadId = useStore(store, (state) => state.threadId);
  const plan = useStore(store, (state) => state.plan);
  const diff = useStore(store, (state) => state.diff);
  const [draft, setDraft] = useState("");
  const [panel, setPanel] = useState<RightPanel>("diff");

  const submit = () => {
    const text = draft.trim();
    if (text === "") {
      return;
    }
    setDraft("");
    void store
      .getState()
      .send(text)
      .catch(() => undefined);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex h-dvh flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3 text-sm">
        <div className="flex items-center gap-3">
          <span className="font-semibold">Cloud Agents</span>
          <span className="text-xs text-muted">{STATUS_LABEL[status]}</span>
          {threadId !== null ? (
            <span className="hidden font-mono text-[11px] text-muted xl:inline">
              {threadId.slice(0, 8)}
            </span>
          ) : null}
        </div>
        <span className="text-xs text-muted">{turnId === null ? "空闲" : "执行中"}</span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface/40 lg:flex">
          <div className="flex items-center justify-between px-3 py-3 text-xs font-semibold text-muted">
            <span>任务线程</span>
            <button
              type="button"
              aria-label="新建线程"
              className="rounded p-1 text-muted hover:bg-surface-raised hover:text-foreground"
              onClick={() => {
                void store
                  .getState()
                  .newThread(true)
                  .catch(() => undefined);
              }}
            >
              <Plus size={14} aria-hidden="true" />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
            {threads.length === 0 ? (
              <p className="px-2 text-xs text-muted">暂无历史线程</p>
            ) : (
              threads.map((thread) => (
                <ThreadRow
                  key={thread.id}
                  thread={thread}
                  active={thread.id === threadId}
                  onSelect={() => {
                    void store
                      .getState()
                      .resumeThread(thread.id, true)
                      .catch(() => undefined);
                  }}
                />
              ))
            )}
          </div>
          <div className="border-t border-border px-3 py-3">
            <p className="mb-2 text-xs font-semibold text-muted">本轮计划</p>
            {plan.length === 0 ? (
              <p className="text-xs text-muted">暂无计划</p>
            ) : (
              <ul className="space-y-1.5">
                {plan.map((step) => (
                  <PlanRow key={`${step.status}-${step.step}`} step={step} />
                ))}
              </ul>
            )}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <main className="flex-1 space-y-5 overflow-y-auto px-6 py-8">
            <div className="mx-auto w-full max-w-3xl space-y-5">
              {items.length === 0 && (
                <p className="text-sm text-muted">
                  描述一个编码任务，云端沙箱会执行它；需要命令或写文件时会先请求你的审批。
                </p>
              )}
              {items.map((item) => (
                <MessageRow key={item.id} item={item} />
              ))}
              {approvals.map((request) => (
                <ApprovalRow
                  key={String(request.id)}
                  request={request}
                  onDecide={(decision) => {
                    store.getState().decide(request, decision);
                  }}
                />
              ))}
              {error !== null && (
                <p className="text-sm text-red-400" role="alert">
                  {error}
                </p>
              )}
            </div>
          </main>

          <footer className="border-t border-border">
            <div className="mx-auto flex w-full max-w-3xl items-end gap-3 px-6 py-4">
              <textarea
                aria-label="任务描述"
                className="min-h-[52px] flex-1 resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent"
                placeholder="例如：修复登录接口的空指针，并补一个回归测试"
                value={draft}
                onChange={(event) => {
                  setDraft(event.target.value);
                }}
                onKeyDown={onKeyDown}
              />
              <button
                className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-50"
                type="button"
                disabled={status !== "open" || turnId !== null || draft.trim() === ""}
                onClick={submit}
              >
                <SendHorizontal size={14} aria-hidden="true" />
                发送
              </button>
            </div>
          </footer>
        </div>

        <aside className="hidden w-[42%] shrink-0 flex-col border-l border-border lg:flex">
          <div className="flex items-center gap-1 border-b border-border px-3 py-2 text-xs">
            {(["diff", "terminal", "files", "preview"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className={`rounded px-2 py-1 ${
                  panel === item
                    ? "bg-surface-raised text-foreground"
                    : "text-muted hover:text-foreground"
                }`}
                onClick={() => {
                  setPanel(item);
                }}
              >
                {TAB_LABEL[item]}
              </button>
            ))}
            <span className="ml-auto text-[11px] text-muted">
              {turnId === null ? "上一轮" : "本轮"}
            </span>
          </div>
          <div className="min-h-0 flex-1">
            {panel === "diff" ? (
              <DiffView diff={diff} />
            ) : panel === "terminal" ? (
              sessionId !== undefined && token !== undefined && wsOrigin !== undefined ? (
                <TerminalPanel sessionId={sessionId} token={token} wsOrigin={wsOrigin} />
              ) : (
                <p className="p-4 text-xs text-muted">会话未连接，终端不可用。</p>
              )
            ) : panel === "files" ? (
              sessionId !== undefined && token !== undefined && httpOrigin !== undefined ? (
                <FilePanel sessionId={sessionId} token={token} httpOrigin={httpOrigin} />
              ) : (
                <p className="p-4 text-xs text-muted">会话未连接，文件树不可用。</p>
              )
            ) : sessionId !== undefined && token !== undefined && httpOrigin !== undefined ? (
              <PreviewPanel sessionId={sessionId} token={token} httpOrigin={httpOrigin} />
            ) : (
              <p className="p-4 text-xs text-muted">会话未连接，预览不可用。</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function ThreadRow({
  thread,
  active,
  onSelect,
}: {
  thread: ThreadSummary;
  active: boolean;
  onSelect: () => void;
}) {
  const label = thread.name ?? thread.preview ?? thread.id;
  return (
    <button
      type="button"
      className={`mb-1 block w-full rounded px-2 py-2 text-left text-xs ${
        active ? "bg-surface-raised text-foreground" : "text-muted hover:bg-surface-raised"
      }`}
      onClick={onSelect}
    >
      <span className="line-clamp-2">{label}</span>
      <span className="mt-0.5 block text-[10px] text-muted">{formatSeconds(thread.updatedAt)}</span>
    </button>
  );
}

function PlanRow({ step }: { step: PlanStep }) {
  const marker = step.status === "completed" ? "✓" : step.status === "inProgress" ? "…" : "○";
  const color =
    step.status === "completed"
      ? "text-green-400"
      : step.status === "inProgress"
        ? "text-accent"
        : "text-muted";
  return (
    <li className="flex gap-1.5 text-xs">
      <span className={`${color} w-3 shrink-0`}>{marker}</span>
      <span className="text-muted">{step.step}</span>
    </li>
  );
}

function MessageRow({ item }: { item: ChatItem }) {
  if (item.type === "userMessage") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-lg bg-surface-raised px-3 py-2 text-sm">
          {item.text}
        </p>
      </div>
    );
  }
  return (
    <article className="rounded-lg border border-border bg-surface px-4 py-3 text-sm">
      <MarkdownText text={item.text} />
    </article>
  );
}

function ApprovalRow({
  request,
  onDecide,
}: {
  request: ApprovalRequest;
  onDecide: (decision: ApprovalDecision) => void;
}) {
  const { icon, label, question } = describeApproval(request);
  return (
    <ApprovalCard icon={icon} label={label} question={question}>
      <ApprovalActions
        onAccept={() => {
          onDecide("accept");
        }}
        onAcceptForSession={() => {
          onDecide("acceptForSession");
        }}
        onDecline={() => {
          onDecide("decline");
        }}
      />
    </ApprovalCard>
  );
}

const TAB_LABEL: Record<RightPanel, string> = {
  diff: "Diff",
  terminal: "终端",
  files: "文件",
  preview: "预览",
};

const STATUS_LABEL: Record<string, string> = {
  connecting: "连接中",
  open: "已连接",
  error: "连接失败",
  closed: "已断开",
};

function formatSeconds(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "";
  }
  return new Date(value * 1000).toLocaleString();
}

function describeApproval(request: ApprovalRequest): {
  icon: typeof Terminal;
  label: string;
  question: string;
} {
  const { method, params } = request;
  if (method === "item/commandExecution/requestApproval") {
    const command = typeof params.command === "string" ? params.command : "（未提供命令）";
    return { icon: Terminal, label: "命令执行审批", question: command };
  }
  if (method === "item/fileChange/requestApproval") {
    const root = typeof params.grantRoot === "string" ? params.grantRoot : "工作区";
    return { icon: FileText, label: "文件写入审批", question: `允许在 ${root} 下写入文件？` };
  }
  const reason = typeof params.reason === "string" ? params.reason : method;
  return { icon: MessageSquare, label: "需要确认", question: reason };
}
