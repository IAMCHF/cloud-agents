import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PreviewPanel } from "./PreviewPanel";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PreviewPanel", () => {
  it("generates a preview link for the chosen port", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        url: "http://s1--5173.preview.test/",
        preview_token: "pt",
        expires_at: 1,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<PreviewPanel sessionId="s1" token="t1" httpOrigin="http://cp:8000/" />);

    const port = screen.getByLabelText("预览端口");
    await userEvent.clear(port);
    await userEvent.type(port, "5173");
    await userEvent.click(screen.getByRole("button", { name: /生成预览链接/ }));

    const link = await screen.findByRole("link", { name: /新窗口打开/ });
    expect(link).toHaveAttribute("href", "http://s1--5173.preview.test/");
    expect(screen.getByTitle("应用预览")).toHaveAttribute("src", "http://s1--5173.preview.test/");

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://cp:8000/api/sessions/s1/preview?token=t1");
    expect(JSON.parse(String(init.body))).toEqual({ port: 5173 });
    expect(init.method).toBe("POST");
  });

  it("validates the port and surfaces server errors", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ detail: "会话未运行，请先恢复会话" }, 409));
    vi.stubGlobal("fetch", fetchMock);

    render(<PreviewPanel sessionId="s1" token="t1" httpOrigin="http://cp:8000" />);
    const port = screen.getByLabelText("预览端口");
    await userEvent.clear(port);
    await userEvent.type(port, "80");
    await userEvent.click(screen.getByRole("button", { name: /生成预览链接/ }));
    expect(screen.getByText("端口需在 1024–65535 之间")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();

    await userEvent.clear(port);
    await userEvent.type(port, "3000");
    await userEvent.click(screen.getByRole("button", { name: /生成预览链接/ }));
    expect(await screen.findByText("会话未运行，请先恢复会话")).toBeInTheDocument();
  });
});
