# AGENTS.md — 云端 Agent 执行服务

定位：内网多租户云端 coding agent 执行服务（codex app-server + OpenSandbox 临时沙箱 + Web 工作区）。
权威设计：`docs/云端Agent服务方案.md`（决策：目标/约束/架构/安全基线）；执行：`docs/实施计划.md`（技术栈/预算/阶段/实测）。实现偏离先回写对应文档再继续。
冲突裁决：用户当次明确指令 > 本文件 > 模型默认。第 1、2、4、5 节为硬约束，仅用户明说「这次例外」可覆盖。

## 1. 先规划，确认后执行【硬约束】

- 命中任一必须先出方案并停等明确批准（「可以/批准/执行」），沉默不算批准：≥3 文件或跨模块；架构/接口/数据模型/鉴权/依赖决策；破坏性操作。
- 方案必含：做什么/不做什么、受影响文件与接口、可验证的验收标准。含糊需求先提问，不脑补。
- 免确认：只读检查、格式化、单文件且不涉及接口的小改动。

## 2. 项目硬约束（方案 C1–C5 的落地规则）

- 不换引擎：agent 引擎只用原版 codex app-server，二进制版本固定；禁止自研 agent loop、禁止 fork codex。
- 任务执行协议对客户端/Web 只用原生 Codex JSON-RPC，控制面做薄代理；禁止发明新任务协议。管理/辅助面 API（会话台账、休眠/恢复状态、execd 终端/文件、预览 Ingress）另行定义并最小化，不混入执行协议。
- 新依赖必须是 OSI 开源许可（Apache/MIT 优先）；KPSL、Dify 修改条款等 source-available 须先经用户确认。
- 资源模型：沙箱按活跃会话创建/销毁，禁止每用户常驻容器；每沙箱 cgroup 限额与租户配额不得移除。
- 客户端团队改动最小化：任何需要客户端改协议的设计，先标出并征得用户同意。
- 不用 app-server 实验性 WebSocket 传输；桥接走 stdio。

## 3. 目录契约（初始；新增目录先提方案）

```
control-plane/       # Python + FastAPI；认证/租户/调度/LLM 网关/WSS 桥接
  app/bridge/        # stdio↔WSS 桥接（沙箱侧进程 + 控制面端点）
  app/sandbox/       # OpenSandbox 生命周期客户端
  tests/
web/                 # React + TypeScript SPA（Vite）
  src/rpc/           # WSS JSON-RPC 客户端
  src/features/      # 对话流/审批；P3 补 diff/任务列表/终端/文件树
  src/codex/         # 协议绑定：generate-json-schema → TS（入库 + CI 校验漂移）
sandbox/
  images/            # 镜像模板：pin codex + bridge + 工具链，非 root
  opensandbox/       # OpenSandbox 配置
  egress/            # egress 白名单策略
docs/                # 架构决策、实施计划、客户端对接说明
.githooks/           # 提交门禁（pre-commit → pnpm run check）
```

- P1 长 `control-plane/app/llm_gateway`（最小 SSE 转发，无计量）；P2 长 `app/{auth,scheduler}` 与网关计量/配额；依赖与构建文件（pyproject.toml / package.json）随 P1 首个代码任务落地。
- 内网 agent 客户端代码：`D:\ssd-projects\yice-agent`（本机路径；用户是客户端团队成员，本服务属同一团队，前端代码可直接拷贝复用；涉及客户端协议改动仍按 §2 先标出并征得同意）。
- 先搜再写；配置/类型/常量各一个权威文件；密钥走环境变量，禁止硬编码路径/URL。
- 抽象纪律：抽象必须绑定当前消费者；公开选择（默认值/外部概念）要有证据；共享状态必须有属主，不新增全局单例。
- 依赖锁定（uv.lock / pnpm-lock.yaml，均在各自根）；根 `package.json` + `pnpm-workspace.yaml` 仅承载 workspace 与工具链（jscpd/聚合脚本），web 是 workspace 成员；带 install 脚本的依赖默认禁止，确需引入走白名单审批（如 pnpm onlyBuiltDependencies）。
- 测试分层与门禁（覆盖率/jscpd/pre-commit/Playwright 金路径，无手测）见 `docs/实施计划.md` §5–6；模块级契约已落地：`control-plane/AGENTS.md`、`web/AGENTS.md`。
- 构建/测试/检查命令（仓库根，聚合入口 `pnpm run check`）：控制面 `uv run --directory control-plane {ruff,mypy,pytest}`（首次 `uv sync --all-groups`）；web `pnpm -C web run {lint,typecheck,test:cov,build}`；克隆检测 `pnpm run check:dup`；协议绑定 `pnpm codex:schema` 生成、`pnpm check:codex` 校验漂移（含在 `check` 内）。首次克隆后 `pnpm install && pnpm run hooks:install` 启用 pre-commit（`.githooks/pre-commit` 调 `pnpm run check`）。完成前必须全绿，未跑写明原因。

## 4. 职责边界与敏感素材【硬约束】

- AI 直接做：代码、测试、文档、只读检查。
- 用户操作，AI 只给步骤与验收并复查：内网环境/容器/网关部署、OIDC 与密钥配置、模型服务对接、机器申请。遇后者先声明「这项由你操作」。
- 仓库与文档禁止出现：内网地址/域名/IP/账号/密钥/客户名；禁止提交 `.env`、构建输出与一般生成物。例外：协议契约产物（codex schema 及其生成的 TS 绑定）属入库契约，须提交并进 CI 漂移校验。

## 5. Git【硬约束】

- Conventional Commits `<type>(<scope>): 简述`；一任务一提交，任务完成即提交；在 feat/fix 分支工作，合并主干由用户执行。
- 提交前 `git status` + `git diff --stat` 自检，只暂存本任务文件；检查不全绿不提交、不宣称完成。
- 禁止自动执行：reset --hard、rebase、push --force、clean、删分支/文件、改写历史；禁止擅自 push/打 tag/--no-verify。

## 6. 完成定义

- 检查全绿并给出实际结果；接口改动已同步调用点/测试/文档。
- 回复说明：改了什么、怎么验证、剩余风险。