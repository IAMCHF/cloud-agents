# 2026-11-18 P1 compose 与 Postgres 迁移验证（L7 开发机部分）

L7 前半：在开发机用真实容器验证部署路径——Postgres 17 上跑 Alembic 迁移，`deploy/compose.yaml`
全栈启动并走通建会话 → 真实模型对话 → 审批 → 卷落盘 → 销毁。内网执行机部署仍由用户操作，届时复跑。

## 环境

| 项 | 值 |
|---|---|
| 宿主 | Windows + Docker Desktop，Docker 29.9.3，Compose v5.7.0 |
| 数据库 | `postgres:17`（PostgreSQL 17.12，Debian） |
| 控制面 | `control-plane/Dockerfile`（python:3.12-slim + uv 0.13.8） |
| OpenSandbox | 容器内 `opensandbox-server==1.2.1`（仓库已 pin） |
| 沙箱 | 既有 `cloud-agents/sandbox:0.1.0`，codex-cli 0.167.0 |
| 模型 | DeepSeek `deepseek-flash`（公网 API） |

## 1. Postgres 17 + Alembic

独立 `postgres:17` 容器（端口 5433），`DATABASE_URL` 指向 asyncpg：

```powershell
$env:DATABASE_URL='postgresql+asyncpg://postgres:<本地测试口令>@127.0.0.1:5433/cloud_agents'
uv run --directory control-plane alembic upgrade head
```

| 验证项 | 结果 |
|---|---|
| `alembic upgrade head` | 通过：`Running upgrade -> 0001_initial`；`alembic current` = `0001_initial (head)` |
| 表结构 | `sessions`：varchar 主键 + `ix_sessions_owner` / `ix_sessions_status`；`audit_events`：`bigint` 主键默认 `nextval('audit_events_id_seq')`、`json` payload、`ix_audit_events_session_id`；时间列均为 `timestamptz` |
| `alembic check` | 通过：`No new upgrade operations detected.`（模型与迁移无漂移） |
| `alembic downgrade base` | 通过：两张业务表删除（`information_schema` 计数 0） |
| 再 `alembic upgrade head` | 通过：回到 `0001_initial (head)`，迁移可逆且可重放 |
| 控制面连 Postgres 启动 | 通过：`/healthz` = ok；`/metrics` 中 `cloud_agents_active_sessions 0.0` |
| 启动对账 | 通过：预置 `running` 行启动后被置 `ended`，`end_reason=control_plane_restart` |

## 2. compose 全栈实跑

修复 3 处实跑阻断并补 2 项部署加固（见下）后：

```powershell
docker compose -f deploy/compose.yaml --env-file .env config --quiet   # 通过
docker compose -f deploy/compose.yaml --env-file .env up -d --build
```

| 验证项 | 证据 |
|---|---|
| 服务状态 | postgres healthy；control-plane 与 opensandbox Up；control-plane 日志显示 Alembic 已跑、uvicorn 启动 |
| `/healthz` | `{"status":"ok"}` |
| OpenSandbox API | `GET /v1/sandboxes` 返回空列表，鉴权头 `OPEN-SANDBOX-API-KEY` 生效 |
| 建会话 | `POST /api/sessions` 返回 `session_id` / `sandbox_id` / `ws_url`；宿主机 `.local/volumes/<session>/` 自动创建 |
| 容器形态 | `sandbox-<id>` 与 `sandbox-egress-<id>` 均 Up |
| 原生 JSON-RPC | WS `initialize` 返回 `l7-smoke/0.167.0 (Debian 12.0.0; x86_64)`；`thread/start`、`turn/start` 正常 |
| 真实模型 + 审批 | 任务「在 /workspace 写 hello.txt 并 cat」：自动批准命令后 `turn completed: completed`，回复确认内容 `l7-ok` |
| host 卷 | 宿主机 `.local/volumes/<session>/hello.txt` 内容为 `l7-ok` |
| 台账/审计 | Postgres `sessions.status=running` 且有 `sandbox_id`；`audit_events` 有 `session.created` |
| 指标 | `cloud_agents_active_sessions 1.0` |
| cgroup | `NanoCpus=2000000000 Memory=2147483648 PidsLimit=4096`（2 CPU / 2GiB / pids 4096） |
| egress 下发 | sidecar env：`OPENSANDBOX_EGRESS_RULES={"defaultAction":"deny","egress":[{"action":"allow","target":"host.docker.internal"}]}`，`OPENSANDBOX_EGRESS_MODE=dns+nft` |
| egress 沙箱内三层测试 | 网关 `200`；`api.deepseek.com` / `example.com` DNS 均 BLOCKED；`1.1.1.1:443` / `8.8.8.8:443` 均 BLOCKED |
| 销毁 | `DELETE /api/sessions/<id>` → `sandbox-*` 容器消失；台账 `ended`；审计含 `session.exited`/`session.stopped`；指标回 `0.0` |
| 控制面重启 | `docker compose restart control-plane` 后 `/healthz` ok；Alembic 重跑为 no-op，启动对账正常 |
| 数据持久化 | `down`（保留卷）后 `up -d`：台账记录仍在；`cloud-agents_osbdata` 中 `opensandbox.db` 存在 |

## 3. 缺陷与修复

| # | 问题 | 修复 |
|---|---|---|
| 1 | compose 要求 `OPEN_SANDBOX_API_KEY`，但 `.env.example` 只有 `OPENSANDBOX_API_KEY`；opensandbox-server 实际读 `OPENSANDBOX_SERVER_API_KEY`，且 toml 已配 `api_key` | 删掉该必填 env，api_key 统一由挂载的 `sandbox.toml` 提供 |
| 2 | 控制面容器从 `.env` 继承 `OPENSANDBOX_BASE_URL=http://127.0.0.1:8080`，容器内回环不是 OpenSandbox | compose 固定 `OPENSANDBOX_BASE_URL=http://opensandbox:8080` |
| 3 | opensandbox 服务把 `${WORKSPACE_HOST_ROOT}` 同路径挂进容器，Windows 下容器目标 `D:/...` 非法；该挂载对 host 卷后端并非必需（`allowed_host_paths` 只做字符串前缀校验） | 删除该挂载，注释说明 host 卷由宿主机 Docker 直接挂到沙箱 |
| 4 | `pip install opensandbox-server` 未 pin，每次启动可能换版本 | pin `opensandbox-server==1.2.1` |
| 5 | OpenSandbox 自身 sqlite 台账在容器内，容器重建后与残留沙箱失联 | 增加命名卷 `osbdata:/root/.opensandbox` |

修复文件：[deploy/compose.yaml](../../deploy/compose.yaml)、[deploy/README.md](../../deploy/README.md)。

## 4. 未覆盖与风险

- **开发机 vs 内网执行机**：本机用 Docker Desktop，`PUBLIC_BASE_URL=http://host.docker.internal:8000` 可被沙箱解析；内网 Linux 执行机必须换成沙箱可达的宿主地址。控制面容器内的 OpenSandbox 地址已固定为服务名，不随执行机变化。
- **OpenSandbox 包安装**：容器启动时从 PyPI 安装 `opensandbox-server==1.2.1`（本机约 48s）；内网需镜像源或预构建镜像，升级版本须复跑本记录。基础镜像 `python:3.12-slim` 建议再 pin digest。
- **endpoint 字段**：P1 控制面只用生命周期 API，不调用沙箱 endpoint；若启用 execd/预览（P3），容器内模式需配 `[docker].host_ip`（或 `[server].eip`），本记录未验证该路径。
- **浏览器金路径**：本次用原生 WS 完成真实 turn，未在 compose 下重跑 Playwright 真模式；浏览器路径已在主机模式验收通过，compose 差异仅在控制面地址。
- **pause/resume**：compose 下未复跑（主机模式已验证），不影响 L7 的迁移与部署路径结论。
- **DELETE 竞态**：删除时桥接先断开会把 `end_reason` 记为 `sandbox_exited`（状态正确、审计完整）；主动删除与异常退出的原因区分留 P2。
