import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { FakeWebSocket } from "./test/fakeWebSocket";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function stubApi(config: unknown, sessions: unknown = []): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url =
        typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.includes("/api/auth/config")) {
        return jsonResponse(config);
      }
      if (url.includes("/api/sessions")) {
        return jsonResponse(sessions);
      }
      return jsonResponse({}, 404);
    }),
  );
}

describe("App", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("explains how to open a session when token auth is active and the URL has no token", async () => {
    window.history.replaceState({}, "", "/");
    stubApi({ mode: "token" });

    render(<App />);

    expect(await screen.findByText(/尚未指定会话/)).toBeInTheDocument();
  });

  it("offers OIDC login when no access token is stored", async () => {
    window.history.replaceState({}, "", "/");
    stubApi({ mode: "oidc", issuer: "https://idp.test", client_id: "web" });

    render(<App />);

    expect(await screen.findByRole("button", { name: "企业账号登录" })).toBeInTheDocument();
  });

  it("offers session creation after login", async () => {
    window.history.replaceState({}, "", "/");
    window.sessionStorage.setItem(
      "cloud-agents.oidc.tokens",
      JSON.stringify({ accessToken: "access-1", expiresAt: Date.now() + 60_000 }),
    );
    stubApi({ mode: "oidc", issuer: "https://idp.test", client_id: "web" });

    render(<App />);

    expect(await screen.findByRole("button", { name: "新建会话" })).toBeInTheDocument();
  });

  describe("with session parameters", () => {
    beforeEach(() => {
      FakeWebSocket.reset();
      vi.stubGlobal("WebSocket", FakeWebSocket);
    });

    it("opens the session websocket and renders the chat shell", () => {
      window.history.replaceState({}, "", "/?session=s1&token=t1&ws=ws://cp:8000");

      render(<App />);

      expect(screen.getByText("Cloud Agents")).toBeInTheDocument();
      expect(screen.getByText("连接中")).toBeInTheDocument();
      expect(FakeWebSocket.instances[0]?.url).toBe("ws://cp:8000/ws/session/s1?token=t1");
    });
  });
});
