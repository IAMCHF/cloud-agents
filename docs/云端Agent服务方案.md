# 云端 Agent 执行服务 — 方案规划

日期：2026-11-17 ｜ 状态：已定稿，待 PoC

## 1. 目标与产品形态

为内网现有 Codex 系 agent 客户端增加"云端执行"选项，并提供 Web 工作区（形态对标 Codex Web / Trae 网页版）：

- 本地客户端与 Web 共用同一套 Agent 界面与任务台账，用户只切换"本地 / 云端执行"。
- 云端按**活跃会话**提供临时隔离工作区，整个 Agent（codex app-server）在沙箱内运行。
- 网页发起的任务本地客户端可见可接管，反之亦然；关页任务继续跑，重开 resume。

## 2. 硬约束（选型否决项）

| # | 约束 | 来源 |
|---|---|---|
| C1 | 真开源（OSI 许可），企业内部多租户可用 | 选型要求 |
| C2 | 不换引擎：保留现有 Codex app-server（已接内网模型） | 领导方向 |
| C3 | 客户端团队零/低改动（我们不拥有该团队） | 跨团队现实 |
| C4 | 内网资源紧张：资源占用随活跃任务数增长，不随用户数增长 | 资源现实 |
| C5 | 数据不出企业；不同用户不共享运行中沙箱 | 安全底线 |

## 3. 总体架构

```
本地客户端（Codex 协议，shim 或端点切换）──┐
                                          ├─→ 控制面 ─→ 执行机池
Web 前端（同一协议的渲染层，SSE/WSS）──────┘              │
                                          沙箱生命周期 API（OpenSandbox）
                                                         │
                              每活跃会话一个容器：codex app-server + stdio↔WSS 桥接
                              挂载用户卷（workspace + ~/.codex）；egress 白名单
```

### 组件与选型依据

| 组件 | 选型 | 许可证 | 证据 / 理由 |
|---|---|---|---|
| Agent 引擎 | codex app-server（原版二进制，版本固定） | Apache-2.0 | 2026-08 官方定位为平台层，协议文档化；thread/turn/item、审批回调、resume/fork、自定义 model_providers 均已核实（[app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)） |
| 沙箱基础设施 | OpenSandbox（Docker 运行时起步，K8s 演进） | Apache-2.0 | 阿里内部生产日均百万级沙箱；2026-10 被 AAIF 收录（[报道](https://m.toutiao.com/article/7700873824409092623/)）；暂停/恢复、egress 白名单、Ingress 预览、execd 终端/文件 API 原生自带；**Docker 模式无 KVM 依赖** |
| 控制面 | 自建（Python + FastAPI）：Web 服务 + WSS/SSE 网关 + 会话调度器 + LLM 网关 + Postgres | — | 认证(OIDC)/租户/RBAC/配额/审计；网关薄代理 JSON-RPC，不发明新协议 |
| Web 前端 | React SPA（TypeScript），消费 `codex app-server generate-ts` 生成的类型绑定 | — | 对话流/diff/审批/任务列表；终端(xterm.js+execd)、文件树、应用预览分期上 |
| 模型 | 内网现有模型服务，经 LLM 网关按租户计量转发 | — | 沙箱内 codex 的 model_providers 指向网关；真 key 只在网关 |

明确不选：Daytona（2026-06 闭源归档）、LobeChat 云沙箱（不开源）、Open WebUI 去品牌部署（许可越线）、仿冒 Codex Cloud 私有后端（闭源协议，随时失效）、E2B（自托管栈重且 Firecracker 需 KVM/裸金属；若日后有裸金属+强运维可重评）。

### 技术栈明细（2026-11-17 拍板）

原则：全部 OSI 许可（Apache/MIT/BSD 优先），成熟生产验证；P1 只引最小集，按阶段引入。控制面 Python + FastAPI，Web React + TypeScript；UI 定 shadcn/ui + Tailwind，Python 包管理定 uv。

**控制面（Python ≥3.12）**

| 用途 | 选型 | 许可 | 阶段 |
|---|---|---|---|
| HTTP/WSS 入口 | FastAPI + uvicorn（WebSocket 用 Starlette 原生） | MIT / BSD-3 | P1 |
| 配置/信封校验 | Pydantic v2 + pydantic-settings（密钥走环境变量） | MIT | P1 |
| 异步 HTTP | httpx（LLM 网关流式转发 + OpenSandbox API） | BSD-3 | P1 |
| 沙箱侧桥接 | websockets + asyncio subprocess（stdio↔WSS） | BSD-3 | P1 |
| 台账/审计 | SQLAlchemy 2.0 async + asyncpg + Alembic | MIT / Apache-2.0 / MIT | P1 |
| 租户/RBAC/配额 + OIDC | 同上库表 + Authlib | BSD-3 | P2 |
| 埋点/日志 | prometheus-client + structlog（活跃率实测；审计落 Postgres） | Apache-2.0 / MIT·Apache | P1 |
| 调度 | 进程内 asyncio + Postgres 台账，不引 Celery/Redis | — | P1；P2 HA 再评 |
| 工程化 | uv + Ruff + mypy + pytest / pytest-asyncio | MIT·Apache / MIT / MIT / MIT·Apache | P1 |

LLM 网关对沙箱暴露 OpenAI 兼容接口（codex `model_providers` 原生支持），真 key 只在网关；内网模型服务适配按实际协议定（对接由用户操作）。

**Web（React 19 + TypeScript）**

| 用途 | 选型 | 许可 | 阶段 |
|---|---|---|---|
| 构建/包管理 | Vite + pnpm | MIT | P1 |
| 协议类型 | codex `generate-ts` 绑定入库 + CI 漂移校验 | Apache-2.0 | P1 |
| 状态 | Zustand（WSS 事件驱动）；REST 增多再评 TanStack Query | MIT | P1 |
| UI | Tailwind CSS + shadcn/ui（Radix） | MIT | P1 |
| 消息渲染 | react-markdown + remark-gfm + Shiki | MIT | P1 |
| 测试 | Vitest + Testing Library；Playwright 金路径 E2E | MIT / Apache-2.0 | P1 |
| Lint/format | Biome | MIT | P1 |
| diff 视图 | Monaco / CodeMirror 6（届时拍板） | MIT | P3 |
| 终端/文件树 | xterm.js + execd；文件树自绘 | MIT | P3 |

**沙箱 / 镜像 / 数据 / 部署**

| 层 | 选型 | 许可 | 阶段 |
|---|---|---|---|
| 沙箱 | OpenSandbox Docker 模式（生命周期 API 保持可替换边界） | Apache-2.0 | P1 |
| 镜像 | Debian slim 多阶段 + pin digest；Python + Node LTS + git；codex 二进制 pin；非 root / 只读 rootfs / cgroup 限额 | DFSG | P1 |
| 编排 | Docker Engine + Compose（P1 单机） | Apache-2.0 | P1 |
| 数据库 | Postgres 17；用户卷 NAS/NFS | PostgreSQL License | P1 |
| 加固 | gVisor（可选） | Apache-2.0 | P4 |

**不引 / 缓议**：Redis/Celery（P2 HA 再评）；客户端 shim 打包语言（P4，倾向 Go/Rust 单二进制，P1 不引第二语言）；K8s（P4）；OpenTelemetry（P2 可选）。禁止项见 §2：不自研 agent loop、不 fork codex、不发明新协议、不用实验性 WS 传输。

## 4. 关键设计决策

1. **隔离单位 = 活跃会话，不是用户。** 计算与存储分离：用户卷持久化，容器只是临时计算壳。
2. **逻辑冻结优先于物理休眠。** codex 全部状态在磁盘（rollout + workspace）：空闲 → 销毁容器保留卷；回来 → 预热池取新沙箱挂卷 + `thread/resume`，秒级恢复。仅"需保活 dev server 预览"的会话用 OpenSandbox 物理暂停/恢复。
3. **预热池** 3–5 个预装工具链的空白沙箱，抵消冷启动；分配后挂卷 + 起 codex 进程。
4. **凭据不进沙箱。** 沙箱内只有受限网关 token；审计/配额/断供在 LLM 网关一处实现。
5. **协议即接口。** 对客户端和 Web 暴露原生 Codex JSON-RPC；控制面只做信封（认证/路由/审计）。传输用 stdio + 自建桥接，不用 app-server 实验性 WebSocket。
6. **版本固定 + CI 协议校验。** pin codex 二进制版本，TS 绑定生成入 CI（VS Code 扩展同款做法）。
7. **审批流。** `requestApproval` 转发前端/客户端弹窗；断线重连走协议原生审批重放；无人在线时按策略挂起或超时拒绝（可配）。

## 5. 客户端接入（给客户端团队的一页纸）

云端执行对客户端 = **换一个 codex 连接端点，协议一个字不变**。二选一：

- **档位 A（零代码改动）**：提供 drop-in `codex` shim 二进制，stdio JSON-RPC 原样透传至云端 WSS。客户端只改二进制路径/配置。
- **档位 B（小改动，体验更好）**：加"本地/云端"开关，云端时改连 WSS 端点，复用现有事件解析与渲染代码；可显示云端任务列表与休眠/恢复状态。

OpenSandbox 及一切服务端组件对客户端不可见。联动：同一控制面会话台账 + 同一沙箱会话允许多客户端接入（app-server 原生支持）。

## 6. 资源预算（500 在线用户）

**前提：资源 = 峰值并发活跃会话 × 单沙箱开销。活跃率规划值 30%（150 并发），PoC 后实测回调。**

单活跃沙箱：内存均值 0.5GB / cgroup 硬限 2GB；CPU 均值 0.3 vCPU / 硬限 2 vCPU；用户卷 2–5GB。

| 角色 | 规格 | 数量 | 说明 |
|---|---|---|---|
| 执行节点 | 16 vCPU / 64GB / 200GB SSD | 3 | 48 vCPU / 192GB，承载 150 活跃（均值 45 vCPU / 75GB）+ 突发余量；单台故障可降级承接 |
| 控制面 | 4 vCPU / 8GB | 2 | HA；500 WS 长连接为轻负载 |
| 共享存储 | NAS/NFS 1–2TB | — | 500 用户工作区卷 |

合计约 **56 vCPU / 208GB / 2TB**。极限（500 全活跃）需执行节点扩至 6–8 台，横向加机即可。

边界：
- **LLM 推理另核**（通常是最大成本项）：向模型服务方确认 150 路并发流的容量余量。
- 密度模型成立前提：每沙箱 cgroup 硬限 + 租户并发配额，超卖排队不打爆。

## 7. 安全基线

- 容器：非 root、只读根文件系统、drop capabilities、cgroup 限额。
- 网络：每沙箱 egress 默认全拒，白名单仅 LLM 网关 / 内部 git / 包镜像；预览 Ingress 带会话级鉴权（仅属主可访问）。
- 数据：每用户独立卷，挂载校验属主；沙箱销毁不删卷。
- 隔离强度：内网认证员工威胁模型下容器级起步，需加强上 gVisor（无 KVM 依赖）；不上 Kata/microVM（内网 VM 无嵌套虚拟化）。
- 审计：控制面落盘全部会话事件与审批记录。

## 8. 实施阶段

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| P1 PoC（1–2 周） | 单机 Docker + OpenSandbox；沙箱内 codex app-server ↔ stdio 桥接 ↔ WSS ↔ 最小网页；LLM 走内网网关 | 金路径：网页派真实 coding 任务 → 流式回显 → 审批弹窗 → 关页重开 resume 成功；**埋点测活跃率** |
| P2 控制面 | OIDC、会话台账、调度器（剩余内存最多者得）、LLM 网关计量、配额 | 多租户并行任务互不干扰；配额/审计生效 |
| P3 密度与体验 | 预热池、空闲销毁策略、卷归档；Web 补齐 diff 审查/任务列表/终端/文件树/预览 | 150 并发压测通过；空闲会话零计算占用 |
| P4 加固与接入 | egress 策略全量、客户端档位 A/B 接入、（可选）gVisor、K8s 运行时迁移 | 客户端零/低改动接入验收；安全评审通过 |

工作量估计：控制面+桥接 2–3 人月；Web 前端 1–2 人月；执行层用现成组件不自研。

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| app-server 协议迭代快、experimental 字段多 | 版本固定 + generate-ts 绑定 + CI 校验；只用稳定方法 |
| 活跃率假设失真 | P1 埋点实测，机器按实测回调；执行池无状态横向扩 |
| OpenSandbox 开源版年轻（server 0.x） | 生命周期 API 是边界，可整体替换为裸 Docker/K8s，不影响客户端与前端 |
| 内网模型并发容量不足 | 立项前先与模型服务方对容量；网关侧排队/限流兜底 |
| 审批无人响应阻塞任务 | 策略可配：挂起等待 / 超时拒绝；IM 通知（企业微信/钉钉） |

## 10. 备选路线备忘

- **集中 Agent Loop + 薄执行沙箱**（其他 AI 方案 1）：通用 agent 的标准模式，但需自研 loop 或 fork codex（app-server 无原生远程执行后端），且客户端要改协议，违反 C2/C3。仅当未来自研非 Codex agent 时重评。
- **E2B 替代 OpenSandbox**：生态更老牌，但自托管需 Nomad/Consul/KVM；有裸金属+专职运维时可重评。
- **Octop（MIT，腾讯）**：若需求转向"通用助手+编码委派"而非纯 coding 云端执行，可作快速落地备选。

## 附：关键事实来源

- [Codex app-server 协议 README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md) ｜ [Codex 开源边界](https://m.toutiao.com/a7676391925070479935/) ｜ [VS Code 集成模式](https://m.blog.csdn.net/gitblog_00887/article/details/156599082)
- [OpenSandbox 阿里日均百万沙箱 / AAIF 收录](https://m.toutiao.com/article/7700873824409092623/) ｜ [OpenSandbox 架构详解](https://johng.cn/ai/opensandbox-alibaba-ai-sandbox-platform)
- [Daytona 闭源归档公告](https://mygit.top/repository/753490180) ｜ [Codex Cloud 官方机制（闭源后端）](https://help.openai.com/zh-hans-cn/articles/11369540-using-codex-with-your-chatgpt-plan)