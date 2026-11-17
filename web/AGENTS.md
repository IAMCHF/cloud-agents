# web/ — Web 工作区 SPA

React 19 + TypeScript + Vite + Tailwind CSS 4 + @assistant-ui/react + Zustand。pnpm workspace 成员，锁文件在仓库根 `pnpm-lock.yaml`。

## 边界

- **协议类型唯一来源 `src/codex/`**：T2 用 pin 版本 codex 的 `generate-json-schema` 产物 + json-schema-to-typescript 生成，禁止手写协议类型或另造事件模型。
- **协议只用原生 Codex JSON-RPC**；不新增自定义事件、不在前端做服务端语义（重连/重放由桥接与控制面负责）。
- 组件可从 yice-agent 直接拷贝（同团队），**测试一并拷**；重复拷贝同一实现前先看能否复用，jscpd 会拦跨文件克隆。
- 状态只用 Zustand（REST 增多再评 TanStack Query），不引第二套全局状态库；样式只用 Tailwind，不引 UI 组件库（shadcn 已弃）。
- 不把任何密钥/内网地址写进前端代码或构建产物。

## 结构

- `src/rpc/` WSS JSON-RPC 客户端（T5）
- `src/features/` 对话流/审批/resume（T5）；diff/终端/文件树 P3
- `src/codex/` 协议绑定产物（T2）：`schema/` 为 pin 版本 codex 的原始 JSON，`generated/` 为 json-schema-to-typescript 输出，两者**均由 `pnpm codex:schema` 生成、禁止手改**；漂移由 `pnpm check:codex` 拦截。
- `src/App.tsx` 当前为 P1 脚手架占位壳，T5 整体替换

## 检查命令

```sh
pnpm install                # 仓库根执行，安装 workspace 全部依赖
pnpm -C web run lint        # Biome
pnpm -C web run typecheck   # tsc --noEmit
pnpm -C web run test:cov    # Vitest + 覆盖率门槛 80%
pnpm -C web run build       # tsc + vite build
pnpm -C web run e2e         # Playwright 金路径（msedge channel，自带 mock 后端：控制面+桥接+fake codex）
```

仓库根 `pnpm run check:web` 等价 lint/类型/测试三步。
