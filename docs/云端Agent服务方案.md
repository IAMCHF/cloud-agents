# 云端 Agent 执行服务 — 方案规划

日期：2026-11-17 ｜ 状态：已定稿（2026-11-17 评审修订）；P1 PoC 真机验收通过（2026-11-18，开发机真沙箱 + 真 codex + DeepSeek 公网 API，见 [验收报告](tests/2026-11-18-P1-验收报告.md)）。安全基线 P1 实测状态见 §6，遗留项见实施计划 §7。

## 1. 目标与产品形态

为内网现有 Codex 系 agent 客户端增加"云端执行"选项，并提供 Web 工作区（形态对标 Codex Web / Trae 网页版）：

- 本地客户端与 Web 共用同一套 Agent 界面与任务台账，用户只切换"本地 / 云端执行"。
- 云端按**活跃会话**提供临时隔离工作区，整个 Agent（codex app-server）在沙箱内运行。
- 云端任务在网页与本地客户端两端可见可接管（本地执行的任务不上云台账）；关页任务继续跑，重开 resume。

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
Web 前端（同一协议的渲染层，WSS）──────────┘              │
                                          沙箱生命周期 API（OpenSandbox）
                                                         │
                              每活跃会话一个容器：codex app-server + stdio↔WSS 桥接
                              挂载用户卷（按会话隔离子目录：workspace + 状态）；egress 白名单
```

### 组件与选型依据

| 组件 | 选型 | 许可证 | 证据 / 理由 |
|---|---|---|---|
| Agent 引擎 | codex app-server（原版二进制，版本固定） | Apache-2.0 | 2026-08 官方定位为平台层，协议文档化；thread/turn/item、审批回调、resume/fork、自定义 model_providers 均已核实（[app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)） |
| 沙箱基础设施 | OpenSandbox（Docker 运行时起步，K8s 演进） | Apache-2.0 | 阿里内部生产日均百万级沙箱；2026-10 被 AAIF 收录（[报道](https://m.toutiao.com/article/7700873824409092623/)）；暂停/恢复、egress 白名单、Ingress 预览、execd 终端/文件 API 原生自带；**Docker 模式无 KVM 依赖** |
| 控制面 | 自建（Python + FastAPI）：Web 服务 + WSS/SSE 网关 + 会话调度器 + LLM 网关 + Postgres | — | 认证(OIDC)/租户/RBAC/配额/审计；网关薄代理 JSON-RPC，不发明新协议 |
| Web 前端 | React SPA（TypeScript），消费 `codex app-server generate-json-schema` → json-schema-to-typescript 生成的类型绑定（与客户端同流程） | — | 对话流/diff/审批/任务列表；终端(xterm.js+execd)、文件树、应用预览分期上 |
| 模型 | 内网现有模型服务，经 LLM 网关按租户计量转发 | — | 沙箱内 codex 的 model_providers 指向网关；真 key 只在网关。**codex 0.167 起只支持 Responses API**（chat wire_api 已移除，2026-11-18 实测）：内网模型须提供 Responses 兼容端点，chat-only 上游需网关转换层（P2 决策，见 §7） |

明确不选：Daytona（2026-06 闭源归档）、LobeChat 云沙箱（不开源）、Open WebUI 去品牌部署（许可越线）、仿冒 Codex Cloud 私有后端（闭源协议，随时失效）、E2B（自托管栈重且 Firecracker 需 KVM/裸金属；若日后有裸金属+强运维可重评）。

库级技术栈、资源预算与实施阶段见 [实施计划.md](实施计划.md)。

## 4. 关键设计决策

1. **隔离单位 = 活跃会话，不是用户。** 计算与存储分离：用户卷持久化，容器只是临时计算壳。**活跃会话**指容器存活的会话（含跑 turn 与短暂空闲，空闲超时窗口 P3 定），密度模型按此口径埋点。**同用户多活跃会话**：卷内按会话隔离 workspace 与状态子目录，resume 挂对应会话目录，避免并发写同一 SQLite/工作区；P1 先以「同用户单活跃」准入兜底。
2. **逻辑冻结优先于物理休眠。** codex 全部状态在磁盘（rollout + workspace）：空闲 → 销毁容器保留卷；回来 → 预热池取新沙箱挂卷 + `thread/resume` 恢复（「秒级」为假设；销毁→新沙箱挂卷→resume 冷恢复实验与 NFS 上 SQLite 锁兼容性 P1 未兑现，移入实施计划 §7 L4/L5——实验 P1 补做、产品化 P3）。仅「需保活 dev server 预览」的会话用 OpenSandbox 物理暂停/恢复；Docker 模式 pause→resume→`thread/resume` 续聊已实测可用（2026-11-18），**pause 语义仍未定论**（freezer 保内存 vs checkpoint 落盘），若保内存则保活会话须计入容量预算。
3. **预热池** 3–5 个预装工具链的空白沙箱，抵消冷启动；分配后挂卷 + 起 codex 进程（P3 落地）。**依赖运行中热挂卷**，若 OpenSandbox 仅支持创建时挂载则池设计需调整，P1/P3 核实。
4. **凭据不进沙箱。** 沙箱内只有受限网关 token；审计/配额/断供在 LLM 网关一处实现。网关 token/URL 经环境变量或 tmpfs 临时配置注入，**不写持久化用户卷**（避免落 NAS 且跨会话残留）；网关即便 P1 无计量也须校验会话 token。
5. **协议即接口。** 任务执行协议对客户端和 Web 只用原生 Codex JSON-RPC；控制面只做信封（认证/路由/审计）。管理/辅助面 API（台账、休眠状态、execd 终端/文件、预览）另行定义并最小化。传输用 stdio + 自建桥接，不用 app-server 实验性 WebSocket。
6. **版本固定 + CI 协议校验。** pin codex 二进制版本；`app-server generate-json-schema` 产物入库，经 json-schema-to-typescript 生成 TS 绑定入 CI 漂移校验（2026-11-17 修正：generate-ts 在 codex 主仓查无实据，改用客户端已验证的 schema 流程）。
7. **审批流。** `requestApproval` 转发前端/客户端弹窗；断线重连的审批重放由桥接缓存 pending 请求实现（同沙箱重连时 bridge↔codex stdio 不断，pending 审批握在桥接手里；**该路线已实测生效**：T3 集成测试 + 真机浏览器刷新重连补发，2026-11-18，不再依赖「app-server 原生重放」核实）。真 codex 每进程只允许一次 initialize，重连时由桥接缓存首次结果本地应答（真机实测修复）。无人在线时按策略挂起或超时拒绝（可配）。

## 5. 客户端接入（给客户端团队的一页纸）

云端执行对客户端 = **换一个 codex 连接端点，协议一个字不变**。二选一：

- **档位 A（零代码改动）**：提供 drop-in `codex` shim 二进制，stdio JSON-RPC 原样透传至云端 WSS。客户端只改二进制路径/配置。
- **档位 B（小改动，体验更好）**：加"本地/云端"开关，云端时改连 WSS 端点，复用现有事件解析与渲染代码；可显示云端任务列表与休眠/恢复状态。

OpenSandbox 及一切服务端组件对客户端不可见。联动：同一控制面会话台账；**先后接管**靠 `thread/resume`（原生），P1 即此形态、单客户端在线。**多客户端同时在线**需桥接做事件扇出 + 请求仲裁 + 审批路由（stdio 单管道，非 app-server 原生），列 P2+ 设计项并先核实。

## 6. 安全基线

基线为目标态；各条附 P1 真机实测状态（2026-11-18），未兑现项统一跟踪于实施计划 §7。

- 容器：非 root、只读根文件系统、drop capabilities、cgroup 限额。**P1 状态**：非 root 已落镜像；cgroup 限额经 OpenSandbox API `resourceLimits`（cpu=2/memory=2Gi）传入，是否真施加未验证；只读根文件系统未实现。两项是密度模型前提（L2）。
- codex 自身沙箱：容器内无 user namespace 权限，bwrap 嵌套沙箱不可用（真机实测）；默认 `sandbox_mode=danger-full-access` + `approval_policy=on-request`（env 可覆盖），**容器即唯一隔离边界**。据此 gVisor（P4）优先级上调：容器内全权限意味着逃逸直达用户卷。
- 网络：每沙箱 egress 默认全拒，白名单仅**控制面 WSS 端点（桥接回连）**/ LLM 网关 / 内部 git / 包镜像四类；预览 Ingress 带会话级鉴权（仅属主可访问）。**P1 未强制**：仅交付策略示例（`sandbox/egress/policy.example.yaml`），创建请求未接 networkPolicy，真机验收实际走公网模型 API 即出口未受限。单租户开发机阶段接受该缺口；**P2 多租户/内网部署前必须强制**（L1），OpenSandbox Docker 模式 egress 能力待核实。codex 自身外联（auth/telemetry/更新检查）显式关闭亦未落配置，当前无全拒兜底，随 egress 一并补。
- 数据：每用户独立卷，挂载校验属主；沙箱销毁不删卷。P1 已验：host 卷白名单 + 会话级子目录，文件写入宿主卷可见、销毁不删卷。
- 隔离强度：内网认证员工威胁模型下容器级起步，需加强上 gVisor（无 KVM 依赖）；不上 Kata/microVM（内网 VM 无嵌套虚拟化）。
- 审计：控制面落盘全部会话事件与审批记录（批量/异步写入，吞吐见实施计划）；审计库集中全量提示词/代码，须最小权限访问 + 静态加密。P1 已落审计队列批量写（可丢弃并计数）；静态加密/最小权限进安全评审。

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| app-server 协议迭代快、experimental 字段多 | 版本固定 + generate-json-schema → json-schema-to-typescript 绑定 + CI 校验；只用稳定方法 |
| 活跃率假设失真 | P1 交付埋点能力 + 模拟基准，真值上线后观测回调；执行池无状态横向扩 |
| OpenSandbox 开源版年轻（server 0.x） | 生命周期 API 是边界，可整体替换为裸 Docker/K8s，不影响客户端与前端 |
| 内网模型并发容量不足 | 立项前先与模型服务方对容量；网关侧排队/限流兜底 |
| 内网模型 chat-only 不兼容（codex 0.167 只支持 Responses API；智谱 `/responses` 404 实测） | 对接前确认内网模型协议（用户操作）；chat-only 上游需网关 chat→responses 转换层（P2 决策，P1 不做）；验收暂用 DeepSeek Responses 端点 |
| 控制面单点重启丢会话（P1 对账仅标 ended，沙箱会话不可恢复） | P1 接受（重启对账已实测）；P2 HA 须设计会话路由 + 重启恢复，或明确降级策略（实施计划 §7 L8） |
| 审批无人响应阻塞任务 | 策略可配：挂起等待 / 超时拒绝；IM 通知须私有化部署或仅发不含任务内容的提醒（公网企业微信/钉钉与 C5 冲突） |
| codex 状态库（SQLite）在 NFS 用户卷上的锁兼容性 | **未实测**（本机 bind mount 通过，NFS 未测，实施计划 §7 L5）；不可行则状态盘本地化 + 卷归档（P3）或换卷方案 |
| P1 无租户配额时并发打爆内存 | 全局 max_active_sessions 准入兜底（P1，按总量预算取值，见实施计划 §2；默认 24 已落地，压测回调未做）；租户配额 P2。cgroup 硬限只限单沙箱、防不了总量超卖；OOM 被杀 ≈ 逻辑冻结，靠 resume 恢复（代价：打断进行中 turn） |
| 同用户多活跃会话并发写同一卷 | 卷内会话级子目录隔离（目标态）；P1 同用户单活跃准入兜底 |
| OpenSandbox Docker 模式能力不全（pause/egress/Ingress/execd 部分或仅 K8s） | 部分已实测：pause/resume、execd 可用；egress/Ingress/热挂卷未验，cgroup/read-only 施加未验（实施计划 §7 L1/L2/L10）；生命周期 API 为可替换边界，回退裸 Docker 时相应能力需自实现 |

## 8. 备选路线备忘

- **集中 Agent Loop + 薄执行沙箱**（其他 AI 方案 1）：通用 agent 的标准模式，但需自研 loop 或 fork codex（app-server 无原生远程执行后端），且客户端要改协议，违反 C2/C3。仅当未来自研非 Codex agent 时重评。
- **E2B 替代 OpenSandbox**：生态更老牌，但自托管需 Nomad/Consul/KVM；有裸金属+专职运维时可重评。
- **Octop（MIT，腾讯）**：若需求转向"通用助手+编码委派"而非纯 coding 云端执行，可作快速落地备选。

## 附：关键事实来源

- [Codex app-server 协议 README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md) ｜ [Codex 开源边界](https://m.toutiao.com/a7676391925070479935/) ｜ [VS Code 集成模式](https://m.blog.csdn.net/gitblog_00887/article/details/156599082)
- [OpenSandbox 阿里日均百万沙箱 / AAIF 收录](https://m.toutiao.com/article/7700873824409092623/) ｜ [OpenSandbox 架构详解](https://johng.cn/ai/opensandbox-alibaba-ai-sandbox-platform)（生产规模为二手报道，评审前宜补官方 repo/会议材料佐证；许可 Apache-2.0 以 repo 为准）
- [Daytona 闭源归档公告](https://mygit.top/repository/753490180) ｜ [Codex Cloud 官方机制（闭源后端）](https://help.openai.com/zh-hans-cn/articles/11369540-using-codex-with-your-chatgpt-plan)