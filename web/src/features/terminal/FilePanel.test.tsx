import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FilePanel } from "./FilePanel";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function urlOf(input: RequestInfo | URL): URL {
  const raw =
    typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  return new URL(raw);
}

function stubFetch(handler: (url: URL) => Response): ReturnType<typeof vi.fn> {
  const mock = vi.fn(async (input: RequestInfo | URL) => handler(urlOf(input)));
  vi.stubGlobal("fetch", mock);
  return mock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("FilePanel", () => {
  it("lists folders first, navigates directories and previews text files", async () => {
    const user = userEvent.setup();
    stubFetch((url) => {
      if (url.pathname.endsWith("/files")) {
        if (url.searchParams.get("path") === "/workspace/src") {
          return jsonResponse({
            entries: [{ path: "/workspace/src/main.ts", type: "file", size: 2048 }],
          });
        }
        return jsonResponse({
          entries: [
            { path: "/workspace/b.txt", type: "file", size: 5 },
            { path: "/workspace/src", type: "directory" },
            { path: "/workspace/big.bin", type: "file", size: 2 * 1024 * 1024 },
          ],
        });
      }
      if (url.pathname.endsWith("/file")) {
        return new Response("hello world", { status: 200 });
      }
      return jsonResponse({}, 404);
    });

    render(<FilePanel sessionId="s1" token="t1" httpOrigin="http://cp:8000/" />);

    expect(await screen.findByText("b.txt")).toBeInTheDocument();
    expect(screen.getByText("5B")).toBeInTheDocument();
    expect(screen.getByText("2.0M")).toBeInTheDocument();

    await user.click(screen.getByText("src"));
    expect(await screen.findByText("main.ts")).toBeInTheDocument();
    expect(screen.getByText("2.0K")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "上级目录" }));
    expect(await screen.findByText("b.txt")).toBeInTheDocument();

    await user.click(screen.getByText("b.txt"));
    expect(await screen.findByText("hello world")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "关闭" }));
    expect(screen.queryByText("hello world")).not.toBeInTheDocument();
  });

  it("shows listing and preview failures", async () => {
    const user = userEvent.setup();
    stubFetch((url) => {
      if (url.pathname.endsWith("/files")) {
        if (url.searchParams.get("path") === "/workspace") {
          return jsonResponse({
            entries: [
              { path: "/workspace/a.txt", type: "file", size: 1 },
              { path: "/workspace/locked", type: "directory" },
            ],
          });
        }
        return new Response("nope", { status: 500 });
      }
      return jsonResponse({ detail: "会话未运行，请先恢复会话" }, 409);
    });

    render(<FilePanel sessionId="s1" token="t1" httpOrigin="http://cp:8000" />);

    await user.click(await screen.findByText("locked"));
    expect(await screen.findByText("请求失败：500")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "上级目录" }));
    await user.click(await screen.findByText("a.txt"));
    expect(await screen.findByText("会话未运行，请先恢复会话")).toBeInTheDocument();
  });

  it("reports network errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("网络断开");
      }),
    );

    render(<FilePanel sessionId="s1" token="t1" httpOrigin="http://cp:8000" />);

    expect(await screen.findByText("网络断开")).toBeInTheDocument();
  });
});
