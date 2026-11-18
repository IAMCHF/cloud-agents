# bench/ — L6 简化基准

对应实施计划 §7 L6：活跃率/资源占用、准入、resume 时延的**简化基准**，给 §2 资源预算提供
开发机参考区间（真值上线后观测，预算不据此改数）。零产品代码改动；结果 JSON 落
`.local/bench/`（不入库），验收证据落 `docs/tests/`  dated 报告。

## 跑法

前置：OpenSandbox server + 控制面已起（[本地测试指南](../docs/tests/本地测试指南.md)，
`NO_PROXY="*"` 启动），仓库根 `.env` 就绪（模型 key/镜像/卷根目录）。

```sh
set -a; . ./.env; set +a
uv run --directory control-plane python ../bench/load.py admission
uv run --directory control-plane python ../bench/load.py density --sessions 8 --duration 180 --duty 0.3
uv run --directory control-plane python ../bench/load.py resume --turns 10
```

脚本自带 `NO_PROXY="*"`（开发机代理 bypass 含 `[::1]` 会崩 httpx）。每模式结束打印
`[RESULT] <mode> PASS/FAIL` 并写 `.local/bench/<mode>-<时间戳>.json`；退出前清理全部沙箱与会话。

## 三个模式测什么

| 模式 | 测什么 | 关键参数 |
|---|---|---|
| `admission` | 同用户单活跃：第二创建 429、并发 burst 全拒、删除后释放、churn 创建时延、`/metrics` 拒绝计数与活跃 gauge 对账 | `--churn 3 --burst 5` |
| `density` | N 路并发按占空比跑最小真实 turn；每沙箱 CPU/内存（docker stats，cgroup 口径）、turn 时延 p50/p95、实测忙碌占比、网关 `llm_requests` 增量 | `--sessions 8 --duration 180 --duty 0.3 --sample-interval 5` |
| `resume` | ① 客户端断线重连+`thread/resume`（同沙箱）② OSB pause→resume→`thread/resume` ③ 冷恢复：K 轮历史落卷→销毁→新沙箱挂卷→**全新 codex 进程**磁盘回放+续聊 | `--turns 10` |

## 口径与已知限制（读报告前必看）

- **P1 单属主**：API 固定 `P1_OWNER` + 同用户单活跃准入，经 API 最多 1 个活跃会话。
  全局上限 `max_active_sessions` 无法经 API 触达（单测已覆盖），多属主压测留 P2（OIDC）后。
- **density 的 N 路构成**：1 个 CP 会话（真桥接/WSS 路径，兼网关 token 锚点）+ N−1 个
  OSB 直建沙箱（`sleep infinity` + `docker exec -i` 驱动真 codex，L4 实验已验证此路径）。
  覆盖：真 codex、真模型、cgroup 限额、网关 N 路 SSE 并发转发；**不覆盖**：N 路桥接 WS 扇入、
  多会话准入竞争。锚点 token 属基准专用手法（恢复沙箱 token 签发是 P3 设计项，见 L4 记录）。
- **CPU% 口径**：docker stats 100% = 1 核；沙箱硬限 2 核即上限 200%。内存为 cgroup 口径 MiB。
- **占空比**：每 turn 后按 `dt*(1-duty)/duty` 休眠，实测忙碌占比 = Σturn 时长/墙钟，报告以实测为准。
- **开发机 ≠ 执行节点**：Docker Desktop VM 资源（`docker info` NCPU/MemTotal）随报告记录；
  内网执行机就绪后按目标 N 复跑（改 `--sessions/--duration` 即可，无代码改动）。
- 冷恢复腿在 codex 运行时 `cp -a` 状态库（含 WAL），与 L4 实验同口径；产品化须停写/checkpoint（P3）。
- 模型调用均为最小 prompt（"Reply with exactly: …"），token 成本可忽略；失败退避 5s 重试。