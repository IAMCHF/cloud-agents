import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { FakeWebSocket } from "./test/fakeWebSocket";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("explains how to open a session when the URL has no token", () => {
    window.history.replaceState({}, "", "/");

    render(<App />);

    expect(screen.getByText(/尚未指定会话/)).toBeInTheDocument();
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
