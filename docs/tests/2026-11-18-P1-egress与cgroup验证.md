# 2026-11-18 P1 egress 强制与 cgroup 限额验证

一次性记录。补 [P1 验收报告](2026-11-18-P1-验收报告.md)「未覆盖项」中的网络出口策略与 cgroup 施加验证；
对应实施计划 §7 L1/L2。结论：**egress 默认全拒在 `dns+nft` 模式下成立并已强制**；
`dns` 模式存在直连 IP 绕过，不可用；`ports` 字段当前不被 sidecar 执行（IP 级白名单）。

## 环境与版本

- 开发机 Windows + Docker Desktop 29.9.3（非内网执行机）。
- OpenSandbox server：`uvx opensandbox-server`，Docker 运行时；execd `v1.1.0`、egress sidecar `v1.1.7`（镜像站拉取）。
- 控制面：`feat/p1-poc` 工作区（networkPolicy 改动，含本次提交）；SQLite 台账 `.local/ledger.db`。
- 沙箱镜像 `cloud-agents/sandbox:0.1.0`（codex-cli 0.167.0，Debian 12）；模型 DeepSeek `deepseek-flash`（公网 Responses API）。
- OpenSandbox 配置：`network_mode="bridge"`、`[egress] mode` 分别按 `dns` / `dns+nft` 各测一轮；
  `drop_capabilities` 9 项、`no_new_privileges=true`、`pids_limit=4096`。

## 验证项与证据

### 1. networkPolicy 随创建请求下发（L1）

控制面 `SANDBOX_EGRESS_ALLOW` 为空时，sidecar 容器 env 收到：

```
OPENSANDBOX_EGRESS_RULES={"defaultAction": "deny", "egress": [{"action": "allow", "target": "host.docker.internal"}]}
```

配置 `SANDBOX_EGRESS_ALLOW="api.deepseek.com,1.1.1.1:443"` 后：

```
OPENSANDBOX_EGRESS_RULES={"defaultAction": "deny", "egress": [{"action": "allow", "target": "host.docker.internal"},
  {"action": "allow", "target": "api.deepseek.com"}, {"action": "allow", "target": "1.1.1.1", "ports": [443]}]}
```

控制面/网关地址自动放行、域名不带端口、IP:port 正确解析，与单测口径一致。
沙箱容器 `NetworkMode=container:<egress sidecar>`——共享 sidecar 网络命名空间，全部流量必经 sidecar。

### 2. `dns` 模式不满足全拒（本次发现）

沙箱内 `docker exec sandbox-<id> timeout 40 python -c "<socket/urllib 测试>"`：

| 测试 | dns 模式结果 |
|---|---|
| HTTP `http://host.docker.internal:8000/healthz` | 200（放行生效） |
| DNS `api.deepseek.com` / `example.com` | gaierror -2（拒绝） |
| **TCP 直连 `1.1.1.1:443`（绕过 DNS）** | **CONNECTED（绕过成功）** |

`dns` 模式只拦 DNS 解析，硬编码 IP 即可出网。**「默认全拒」必须用 `dns+nft`。**

### 3. `dns+nft` 模式默认全拒成立

| 测试 | dns+nft 结果 |
|---|---|
| 网关 HTTP | 200 |
| DNS `api.deepseek.com` / `example.com`（未放行时） | gaierror -2 |
| TCP `1.1.1.1:443` / `8.8.8.8:443` | TimeoutError（丢弃） |
| 硬编码 `8.8.8.8:53` 发 DNS 查 `example.com` | rcode=3（NXDOMAIN，被透明拦截过滤） |
| 硬编码 `8.8.8.8:53` 发 DNS 查 `host.docker.internal` | rcode=0 answers=1（白名单域名可解析） |

sidecar 内 `nft list ruleset` 关键规则（证据）：

```
chain egress { type filter hook output priority filter; policy drop;
  ct state established,related accept
  udp dport 53 redirect to :15353        # DNS 透明重定向到 sidecar 过滤
  tcp dport 853 drop / udp dport 853 drop # DoT 绕过被封
  ip daddr @dyn_allow_v4 accept           # 白名单域名动态解析 IP，timeout 6m
  ip daddr @allow_v4 accept               # 静态 IP/CIDR 白名单
  drop }
```

`dyn_allow_v4` 实测含 `api.deepseek.com` 解析出的两个 IP 与 `host.docker.internal` 网关 IP（6m TTL）。

### 4. 白名单扩展生效（四类放行的机制验证）

`SANDBOX_EGRESS_ALLOW="api.deepseek.com,1.1.1.1:443"` 一轮，沙箱内：

| 测试 | 结果 |
|---|---|
| DNS `api.deepseek.com` | RESOLVED（120.240.157.195） |
| TCP `api.deepseek.com:443` | CONNECTED |
| TCP `1.1.1.1:443` | CONNECTED |
| TCP `8.8.8.8:443`（未放行） | TimeoutError |
| DNS `example.com`（未放行） | gaierror -2 |

### 5. `ports` 字段不被执行（本次发现，上游限制）

规则 `{"target":"1.1.1.1","ports":[443]}` 下，沙箱内 TCP `1.1.1.1:80` 仍 **CONNECTED**。
nft 链只有 `ip daddr @allow_v4 accept`，无任何端口匹配——egress sidecar v1.1.7 接受 `ports` 但不执行，
**白名单实际粒度是 IP 级**。控制面继续按 API 契约下发 `ports`（前向兼容），文档口径按 IP 级表述。

### 6. 强制出口下真实模型 turn 通过

`dns+nft`、白名单仅控制面/网关一轮：WS 连 `ws://127.0.0.1:8000/ws/session/<id>`，
`initialize`（userAgent 含 codex-cli 0.167.0）→ `thread/start` → `turn/start`（提示词要求回复 `egress-ok`）：

```
turn completed in 1.5s; deltas=4; text='egress-ok'; errors=[]
```

模型流量由控制面网关从宿主转发（真 key 只在网关），沙箱只需回连控制面——与全拒策略自洽。
浏览器↔控制面腿不在沙箱出口策略范围内，P1 验收已覆盖，本轮不重复。

### 7. cgroup 限额与容器安全项施加（L2）

`docker inspect sandbox-<id>`：

```
NanoCpus=2000000000  Memory=2147483648  PidsLimit=4096
NoNewPrivileges=[no-new-privileges=true]
CapDrop=[NET_RAW NET_ADMIN SYS_MODULE SYS_TIME MKNOD SYS_TTY_CONFIG SYS_ADMIN SYS_PTRACE AUDIT_WRITE]
ReadonlyRootfs=false
```

cpu=2 / memory=2Gi 由 `resourceLimits` 真实施加；只读 rootfs 仍为 false（OpenSandbox 创建 API 无该字段，P4 遗留，见实施计划 §7 L2）。

### 8. 清理与台账

三轮会话 `DELETE /api/sessions/<id>` 均 204；`docker ps` 无 `sandbox-*` 容器；
台账 `sessions.status=ended`；`/metrics` `cloud_agents_active_sessions 0.0`。

## 缺陷与修复

本轮未改代码逻辑（networkPolicy 实现按预期工作）；三个发现均已回写文档/配置：

1. **`dns` 模式直连 IP 绕过** → 示例配置与指南改为强制 `mode="dns+nft"`；方案 §6 口径同步。
2. **`ports` 不被 sidecar v1.1.7 执行** → 文档按 IP 级白名单表述；`manager.py` 注释同步；sidecar 升级后需复测。
3. **开发机代理 bypass 含 `[::1]` 致 `uvx opensandbox-server` 启动崩溃**（httpx InvalidURL，与 pytest 同根因，实施计划 §8 已记）→
   服务进程以 `NO_PROXY="*"` 启动规避；指南补记。仅开发机现象，部署机按方案 §6 无代理约束执行。

## 未覆盖风险

- 只读 rootfs 未实现（P4，L2 遗留）。
- 域名白名单靠 DNS 动态解析（6m TTL）；超过 TTL 的长连接行为未显式验证（`ct established,related accept` 理论上放行，未实测）。
- IPv6 出口路径未测（nft 有 `allow_v6/dyn_allow_v6` 规则，本轮测试均 IPv4）。
- egress sidecar / execd 版本升级后行为可能变化（尤其 `ports`），升级须复测本清单。
- 本验证在开发机 Docker Desktop；内网执行机部署后需按 L7 复跑。

## 复现入口

- 环境搭建与 egress 验证步骤：[本地测试指南](本地测试指南.md)「egress 强制验证」节。
- 真实 turn：指南 §4 WS 冒烟或 `web/e2e/real-model.spec.ts`（真模式 Playwright）。
- 本轮 WS 脚本 `.local/verify_turn.py`（本机一次性，不入库）；关键命令已列于上文各节。