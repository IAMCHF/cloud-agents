import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalActions } from "./ApprovalCard";

describe("ApprovalActions", () => {
  it("reports decline, accept-once and accept-for-session", async () => {
    const accept = vi.fn();
    const decline = vi.fn();
    const session = vi.fn();
    render(<ApprovalActions onAccept={accept} onDecline={decline} onAcceptForSession={session} />);

    await userEvent.click(screen.getByRole("button", { name: /拒绝/ }));
    await userEvent.click(screen.getByRole("button", { name: /允许一次/ }));
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "更多允许选项" }));
    });
    await userEvent.click(screen.getByRole("button", { name: "本次会话允许" }));

    expect(decline).toHaveBeenCalledTimes(1);
    expect(accept).toHaveBeenCalledTimes(1);
    expect(session).toHaveBeenCalledTimes(1);
  });

  it("disables actions while busy", () => {
    render(<ApprovalActions onDecline={vi.fn()} onAccept={vi.fn()} busy />);

    expect(screen.getByRole("button", { name: /允许一次/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /拒绝/ })).toBeDisabled();
  });
});
