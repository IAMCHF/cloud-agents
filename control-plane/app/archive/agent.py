"""归档/恢复沙箱内的自包含 agent（通过 OpenSandbox 端口代理访问）。

archive 模式：打包 /workspace 与 CODEX_HOME，起 HTTP 文件服务供控制面下载。
restore 模式：接收两个 tar 的 PUT，校验路径后解压到对应 PVC。
"""

from __future__ import annotations

import http.server
import os
import pathlib
import socketserver
import tarfile
import threading
from typing import Any

MODE = os.environ.get("ARCHIVE_MODE", "archive")
PORT = int(os.environ.get("ARCHIVE_PORT", "18081"))
WORKSPACE = pathlib.Path(os.environ.get("ARCHIVE_WORKSPACE", "/workspace"))
STATE = pathlib.Path(os.environ.get("ARCHIVE_STATE", "/home/agent/.codex"))
OUT = pathlib.Path("/tmp/archive")
_restore_lock = threading.Lock()
_restore_started = False


def _tar(name: str, source: pathlib.Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT / name, "w:gz") as archive:
        if source.exists():
            archive.add(source, arcname=".")


def _extract(name: str, destination: pathlib.Path) -> None:
    archive_path = OUT / name
    if not archive_path.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (base / member.name).resolve()
            if target != base and base not in target.parents:
                raise ValueError(f"unsafe tar member: {member.name}")
        archive.extractall(base, filter="data")


def _archive_mode() -> None:  # pragma: no cover - 仅在沙箱内运行
    _tar("workspace.tar.gz", WORKSPACE)
    _tar("state.tar.gz", STATE)
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args, directory=str(OUT), **kwargs
    )
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), handler) as server:
        server.allow_reuse_address = True
        server.serve_forever()


def _restore_if_ready() -> None:
    global _restore_started
    with _restore_lock:
        if _restore_started:
            return
        if not ((OUT / "workspace.tar.gz").exists() and (OUT / "state.tar.gz").exists()):
            return
        _restore_started = True
    try:
        _extract("workspace.tar.gz", WORKSPACE)
        _extract("state.tar.gz", STATE)
        (OUT / "restore.done").write_text("done", encoding="utf-8")
    except Exception as exc:
        (OUT / "restore.error").write_text(str(exc), encoding="utf-8")


def _read_exact(stream: Any, size: int) -> bytes:
    remaining = size
    chunks: list[bytes] = []
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class _RestoreHandler(http.server.BaseHTTPRequestHandler):  # pragma: no cover
    def do_PUT(self) -> None:
        name = self.path.rstrip("/").split("/")[-1]
        if name not in {"workspace.tar.gz", "state.tar.gz"}:
            self.send_error(400)
            return
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / name).open("wb") as handle:
            if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
                while True:
                    line = self.rfile.readline().strip()
                    if not line:
                        break
                    size = int(line.split(b";")[0], 16)
                    if size == 0:
                        self.rfile.readline()
                        break
                    handle.write(_read_exact(self.rfile, size))
                    self.rfile.read(2)
            else:
                remaining = int(self.headers.get("Content-Length", "0"))
                while remaining > 0:
                    chunk = self.rfile.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    handle.write(chunk)
                    remaining -= len(chunk)
        self.send_response(201)
        self.end_headers()
        self.wfile.flush()
        # 解压可能耗时，放到后台线程；先让代理拿到 201，避免连接被判定为超时。
        threading.Thread(target=_restore_if_ready, daemon=True).start()

    def do_GET(self) -> None:
        if self.path.rstrip("/") != "/status":
            self.send_error(404)
            return
        if (OUT / "restore.error").exists():
            body = b"error"
        elif (OUT / "restore.done").exists():
            body = b"done"
        else:
            body = b"waiting"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


def _restore_mode() -> None:  # pragma: no cover - 仅在沙箱内运行
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), _RestoreHandler) as server:
        server.allow_reuse_address = True
        server.serve_forever()


def main() -> None:  # pragma: no cover - 仅在沙箱内运行
    if MODE == "restore":
        _restore_mode()
    else:
        _archive_mode()


if __name__ == "__main__":
    main()
