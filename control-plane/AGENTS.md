# control-plane/ — 控制面

Python ≥3.12，uv 管依赖（`uv.lock` 入库）。职责：认证/租户/调度/LLM 网关/WSS 桥接；设计见 `../docs/云端Agent服务方案.md`。

## 边界

- **薄代理**：任务执行协议对客户端/Web 只用原生 Codex JSON-RPC，本层只做信封（认证/路由/审计），不改写消息语义、不发明新方法。管理/辅助面 API（台账、休眠状态、execd 终端/文件、预览）单独定义并最小化。
- **引擎不在本层**：agent loop 由沙箱内原版 codex app-server 承担；禁止自研 loop、禁止 fork codex、不用 app-server 实验性 WebSocket 传输（桥接走 stdio）。
- **密钥只走环境变量**（pydantic-settings 读取），禁止硬编码地址/账号/token；`.env` 不入库。
- **沙箱按活跃会话创建/销毁**，禁止每用户常驻容器假设；cgroup 限额与准入逻辑不得绕过。
- 依赖只引 OSI 许可；新增运行时依赖先看 `docs/实施计划.md` §1 清单，uv.lock 同步提交。

## 结构

- `app/bridge/` stdio↔WSS 桥接（T3）
- `app/sandbox/` OpenSandbox 生命周期客户端（T4）
- `app/llm_gateway/` 最小 SSE 转发（T4）
- `tests/` 与 `app/` 同构；集成用例走 fake codex app-server，不手搭 mock 骗绿。

## 检查命令

```sh
cd control-plane
uv sync --all-groups        # 首次；本机 PyPI 镜像可用 UV_DEFAULT_INDEX 指定（不入库）
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest               # 覆盖率门槛 80%，配置在 pyproject.toml
```

仓库根 `pnpm run check:cp` 等价上述 lint/类型/测试三步。
