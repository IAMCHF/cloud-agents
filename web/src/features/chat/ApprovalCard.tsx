import { ChevronDown, CornerDownLeft } from "lucide-react";
import { type ComponentType, type ReactNode, type SVGProps, useState } from "react";

export function ApprovalCard({
  icon: Icon,
  label,
  question,
  children,
  constrainHeight = false,
}: {
  icon: ComponentType<{ size?: number; "aria-hidden"?: SVGProps<SVGSVGElement>["aria-hidden"] }>;
  label: string;
  question: string;
  children: ReactNode;
  constrainHeight?: boolean;
}) {
  // 大段工具参数在卡片内部滚动，标题与操作按钮保持可见。
  return (
    <div
      className={`approval-inline relative z-2 col-start-1 mx-auto w-[min(800px,calc(100%_-_48px))] min-w-0 rounded-lg border border-border bg-surface px-4 py-3 ${constrainHeight ? "flex max-h-[min(640px,80dvh)] flex-col overflow-hidden" : ""}`}
      role="alert"
      aria-label={label}
    >
      <div className="flex shrink-0 items-center gap-1.5 text-xs text-muted">
        <Icon size={13} aria-hidden="true" />
        <span>{label}</span>
      </div>
      <p
        className={`mt-1.5 whitespace-pre-wrap text-sm font-medium leading-6 text-foreground [overflow-wrap:anywhere] ${constrainHeight ? "max-h-[12dvh] shrink-0 overflow-y-auto overscroll-contain" : ""}`}
      >
        {question}
      </p>
      {children}
    </div>
  );
}

export function ApprovalActions({
  onDecline,
  onAccept,
  onAcceptForSession,
  onCancel,
  acceptLabel = "允许一次",
  busy = false,
  acceptDisabled = false,
  shortcuts = true,
}: {
  onDecline: () => void;
  onAccept?: () => void;
  onAcceptForSession?: () => void;
  onCancel?: () => void;
  acceptLabel?: string;
  busy?: boolean;
  acceptDisabled?: boolean;
  shortcuts?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const secondaryClass =
    "flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-raised disabled:opacity-50";
  return (
    <div className="relative mt-2.5 flex items-center justify-end gap-2">
      {onCancel && (
        <button className={secondaryClass} type="button" disabled={busy} onClick={onCancel}>
          取消
        </button>
      )}
      <button className={secondaryClass} type="button" disabled={busy} onClick={onDecline}>
        拒绝
        {shortcuts && (
          <kbd className="rounded bg-surface-raised px-1 py-px text-[10px] font-normal text-muted">
            Esc
          </kbd>
        )}
      </button>
      <div className="flex items-stretch overflow-hidden rounded-md bg-accent text-accent-foreground">
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm transition-opacity hover:opacity-90 disabled:opacity-50"
          type={onAccept ? "button" : "submit"}
          disabled={busy || acceptDisabled}
          onClick={onAccept}
        >
          {acceptLabel}
          {shortcuts && <CornerDownLeft size={13} aria-hidden="true" />}
        </button>
        {onAcceptForSession && (
          <button
            aria-label="更多允许选项"
            aria-expanded={menuOpen}
            className="flex items-center border-l border-accent-foreground/25 px-1.5 transition-opacity hover:opacity-90 disabled:opacity-50"
            type="button"
            disabled={busy || acceptDisabled}
            onClick={() => {
              setMenuOpen((open) => !open);
            }}
          >
            <ChevronDown size={13} aria-hidden="true" />
          </button>
        )}
      </div>
      {menuOpen && onAcceptForSession && (
        <div className="absolute bottom-full right-0 z-20 mb-2 overflow-hidden rounded-lg border border-border bg-surface shadow-lg">
          {[
            { label: "允许一次", action: onAccept },
            { label: "本次会话允许", action: onAcceptForSession },
          ].map(({ label, action }) => (
            <button
              className="block w-full whitespace-nowrap border-0 bg-transparent px-4 py-2 text-left text-sm text-foreground transition-colors hover:bg-surface-raised"
              key={label}
              type="button"
              disabled={busy || acceptDisabled}
              onClick={() => {
                setMenuOpen(false);
                action?.();
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
