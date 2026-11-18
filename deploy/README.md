# deploy/ — P1 单机编排（部署由用户操作）

本文档只给步骤与验收，AI 不代跑内网部署。

## 组成

- `compose.yaml`：Postgres 17 + 控制面（自动跑 Alembic 迁移）+ OpenSandbox（Docker 运行时）。
- 控制面镜像：`control-plane/Dockerfile`（构建上下文 = 仓库根）。
- 沙箱镜像：`sandbox/images/Dockerfile`（单独构建并推送到执行机可拉取的仓库）。

## 步骤

1. 复制**仓库根** `.env.example` 为 `.env`（compose 读取 `../.env`），至少填：`P1_AUTH_TOKEN`、`OPENSANDBOX_API_KEY`、`PUBLIC_BASE_URL`（沙箱可达的控制面地址）、`WORKSPACE_HOST_ROOT`、`POSTGRES_PASSWORD`、`SANDBOX_CONFIG_PATH`、`LLM_UPSTREAM_BASE_URL/LLM_API_KEY`；按需配 `SANDBOX_EGRESS_ALLOW`（内部 git/包镜像域名，控制面/网关自动放行）。
2. 从 `sandbox/opensandbox/config.example.toml` 复制出执行机配置（填 `execd_image`、`eip`、`storage.allowed_host_paths`、`[egress] image`），把绝对路径写进 `SANDBOX_CONFIG_PATH`。`allowed_host_paths` 必须覆盖 `WORKSPACE_HOST_ROOT`，否则创建沙箱会被拒。**`[egress] mode` 必须为 `dns+nft`**——`dns` 模式只拦 DNS，直连 IP 可绕过（2026-11-18 实测）。OpenSandbox 与执行机同机但跑在容器内（compose）时，额外要求 `[server] host = "0.0.0.0"` 且配 `[docker].host_ip`（沙箱 endpoint 用，见示例注释）。
3. 构建并启动：`docker compose -f deploy/compose.yaml --env-file .env up -d --build`。控制面在 compose 网络内固定用 `http://opensandbox:8080` 访问 OpenSandbox，不要依赖 `.env` 里的本机调试值；opensandbox-server 已 pin `1.2.1`（容器启动时从 PyPI 安装，内网需镜像源或预构建镜像）。
4. 构建沙箱镜像并让 OpenSandbox 能拉到（`SANDBOX_IMAGE` 指向它）。

## 验收

- `curl http://<控制面>:8000/healthz` → `{"status":"ok"}`。
- `curl http://<控制面>:8000/metrics` 含 `cloud_agents_active_sessions`。
- 迁移核对：`docker compose ... exec control-plane alembic current` 应为 `0001_initial (head)`，`alembic check` 无漂移。
- 创建会话：`POST /api/sessions`（Bearer `P1_AUTH_TOKEN`）→ 返回 `ws_url`；浏览器打开 `/?session=...&token=...` 走金路径。
- Playwright：`pnpm -C web run e2e`（mock 模式，不需要本文件的服务）。

## 开发机自测

不依赖内网的完整链路验证（OpenSandbox + 真实 codex）见 `docs/tests/本地测试指南.md`；
compose + Postgres 17 的实跑记录见 `docs/tests/2026-11-18-P1-compose与Postgres验证.md`。

## 已知边界（P1）

- Compose 是单机模板，不做 HA；控制面单 worker，进程内准入/通道状态。
- 每沙箱 cgroup 限额已验施加、egress 默认全拒已强制（2026-11-18 开发机实测，见 `docs/tests/2026-11-18-P1-egress与cgroup验证.md`）；read-only rootfs 未实现（OpenSandbox 创建 API 无字段，P4）。egress 白名单实际 IP 级（sidecar v1.1.7 不执行 `ports`）；沙箱加固项见 `sandbox/opensandbox/config.example.toml`。
- `opensandbox-server` 已 pin `1.2.1`；基础镜像 `python:3.12-slim` 建议在执行机再 pin digest。升级 OpenSandbox 版本须按验证记录复跑 egress/cgroup。
