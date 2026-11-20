import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeWebSocket } from "../../test/fakeWebSocket";
import { TerminalPanel } from "./TerminalPanel";

const terminalState = vi.hoisted(() => ({
  writes: [] as unknown[],
  addons: [] as unknown[],
  focused: 0,
  disposed: 0,
  dataHandler: null as null | ((data: string) => void),
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 80;
    rows = 24;
    loadAddon(addon: unknown) {
      terminalState.addons.push(addon);
    }
    open() {}
    focus() {
      terminalState.focused += 1;
    }
    write(data: unknown) {
      terminalState.writes.push(data);
    }
    onData(handler: (data: string) => void) {
      terminalState.dataHandler = handler;
      return { dispose() {} };
    }
    dispose() {
      terminalState.disposed += 1;
    }
  },
}));

vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit() {}
  },
}));

class FakeResizeObserver {
  static instances: FakeResizeObserver[] = [];
  disconnected = false;

  constructor(_: () => void) {
    FakeResizeObserver.instances.push(this);
  }

  observe() {}

  disconnect() {
    this.disconnected = true;
  }
}

beforeEach(() => {
  FakeWebSocket.reset();
  terminalState.writes.length = 0;
  terminalState.addons.length = 0;
  terminalState.focused = 0;
  terminalState.disposed = 0;
  terminalState.dataHandler = null;
  vi.stubGlobal("WebSocket", FakeWebSocket);
  vi.stubGlobal("ResizeObserver", FakeResizeObserver);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TerminalPanel", () => {
  it("connects to the control-plane terminal and relays xterm IO", () => {
    const { unmount } = render(
      <TerminalPanel sessionId="s1" token="t/1" wsOrigin="ws://cp:8000/" />,
    );

    const socket = FakeWebSocket.instances[0];
    expect(socket?.url).toBe("ws://cp:8000/api/sessions/s1/terminal?token=t%2F1");
    expect(terminalState.addons).toHaveLength(1);

    socket?.open();
    expect(socket?.sent).toEqual([JSON.stringify({ type: "resize", cols: 80, rows: 24 })]);
    expect(terminalState.focused).toBe(1);

    terminalState.dataHandler?.("ls\r");
    expect(socket?.sent.at(-1)).toBe(JSON.stringify({ type: "stdin", data: "ls\r" }));

    socket?.message("ignored-text");
    expect(terminalState.writes).toEqual([]);
    socket?.messageBytes(new Uint8Array([104, 105]).buffer);
    expect(terminalState.writes).toEqual([new Uint8Array([104, 105])]);

    socket?.close();
    expect(terminalState.writes.at(-1)).toBe("\r\n[终端已断开]\r\n");

    unmount();
    expect(terminalState.disposed).toBe(1);
    expect(FakeResizeObserver.instances.at(-1)?.disconnected).toBe(true);
  });

  it("does not send stdin before the socket is open", () => {
    render(<TerminalPanel sessionId="s1" token="t1" wsOrigin="ws://cp:8000" />);

    terminalState.dataHandler?.("pwd\r");

    expect(FakeWebSocket.instances[0]?.sent).toEqual([]);
  });
});
