import type { RpcTransport } from "../rpc/client";

/** 测试用内存传输：可脚本化应答，也可主动推送服务端消息。 */
export class FakeTransport implements RpcTransport {
  readonly sent: string[] = [];
  closed = false;
  private handlers: { onMessage: (payload: string) => void; onClose: () => void } = {
    onMessage: () => undefined,
    onClose: () => undefined,
  };
  private readonly responder: (
    message: Record<string, unknown>,
  ) => Record<string, unknown> | undefined;

  constructor(
    responder?: (message: Record<string, unknown>) => Record<string, unknown> | undefined,
  ) {
    this.responder = responder ?? (() => undefined);
  }

  setHandlers(handlers: { onMessage: (payload: string) => void; onClose: () => void }): void {
    this.handlers = handlers;
  }

  send(payload: string): void {
    this.sent.push(payload);
    const message = JSON.parse(payload) as Record<string, unknown>;
    const response = this.responder(message);
    if (response !== undefined) {
      this.emit(response);
    }
  }

  emit(message: Record<string, unknown>): void {
    this.handlers.onMessage(JSON.stringify(message));
  }

  emitRaw(payload: string): void {
    this.handlers.onMessage(payload);
  }

  drop(): void {
    this.handlers.onClose();
  }

  close(): void {
    this.closed = true;
  }
}
