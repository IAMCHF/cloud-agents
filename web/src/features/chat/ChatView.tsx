import { FileText, MessageSquare, SendHorizontal, Terminal } from "lucide-react";
import { type KeyboardEvent, useState } from "react";
import { useStore } from "zustand";
import type {
  ApprovalDecision,
  ApprovalRequest,
  ChatItem,
  SessionStore,
} from "../../state/session";
import { ApprovalActions, ApprovalCard } from "./ApprovalCard";
import { MarkdownText } from "./MarkdownText";

export function ChatView({ store }: { store: SessionStore }) {
  const status = useStore(store, (state) => state.status);
  const items = useStore(store, (state) => state.items);
  const approvals = useStore(store, (state) => state.approvals);
  const error = useStore(store, (state) => state.error);
  const turnId = useStore(store, (state) => state.turnId);
  const [draft, setDraft] = useState("");

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
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <header className="flex items-center justify-between border-b border-border px-6 py-3 text-sm">
        <div>
          <span className="font-semibold">Cloud Agents</span>
          <span className="ml-3 text-xs text-muted">{STATUS_LABEL[status]}</span>
        </div>
        <span className="text-xs text-muted">{turnId === null ? "空闲" : "执行中"}</span>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 space-y-5 px-6 py-8">
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

const STATUS_LABEL: Record<string, string> = {
  connecting: "连接中",
  open: "已连接",
  error: "连接失败",
  closed: "已断开",
};

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
