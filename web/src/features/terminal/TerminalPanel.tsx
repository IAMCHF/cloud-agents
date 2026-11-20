/** Web 终端：浏览器 xterm ↔ 控制面 WS ↔ execd PTY。 */

import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useEffect, useRef } from "react";

export function TerminalPanel({
  sessionId,
  token,
  wsOrigin,
}: {
  sessionId: string;
  token: string;
  wsOrigin: string;
}) {
  const host = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (host.current === null) {
      return;
    }
    const terminal = new Terminal({
      convertEol: true,
      cursorBlink: true,
      fontSize: 12,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      theme: {
        background: "#0d1117",
        foreground: "#e6edf3",
        cursor: "#58a6ff",
      },
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(host.current);
    fit.fit();

    const socketUrl = `${wsOrigin.replace(/\/$/, "")}/api/sessions/${encodeURIComponent(
      sessionId,
    )}/terminal?token=${encodeURIComponent(token)}`;
    const socket = new WebSocket(socketUrl);
    socket.binaryType = "arraybuffer";
    let disposed = false;

    const sendResize = () => {
      fit.fit();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "resize", cols: terminal.cols, rows: terminal.rows }));
      }
    };

    socket.addEventListener("open", () => {
      sendResize();
      terminal.focus();
    });
    socket.addEventListener("message", (event) => {
      if (typeof event.data === "string") {
        return;
      }
      terminal.write(new Uint8Array(event.data as ArrayBuffer));
    });
    socket.addEventListener("close", () => {
      if (!disposed) {
        terminal.write("\r\n[终端已断开]\r\n");
      }
    });
    socket.addEventListener("error", () => {
      if (!disposed) {
        terminal.write("\r\n[终端连接失败]\r\n");
      }
    });

    const dataSubscription = terminal.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "stdin", data }));
      }
    });
    const observer = new ResizeObserver(sendResize);
    observer.observe(host.current);

    return () => {
      disposed = true;
      observer.disconnect();
      dataSubscription.dispose();
      socket.close();
      terminal.dispose();
    };
  }, [sessionId, token, wsOrigin]);

  return (
    <div ref={host} className="h-full min-h-0 bg-[#0d1117] p-2" data-testid="terminal-panel" />
  );
}
