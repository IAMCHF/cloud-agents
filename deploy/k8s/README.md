# Kubernetes 部署（P1.5 开发机验证 + P2 HA）

在 kind 上部署控制面（P2 起双副本）+ Postgres，沙箱走 OpenSandbox K8s 运行时，工作区用 PVC。
这是开发机验证路径，不是生产清单；生产差异见 `docs/实施计划.md` 的 D1/D2 矩阵。

前置：kind 集群与 OpenSandbox charts 已按 `docs/tests/2026-11-18-P0-K8s与NFS可行性.md`
安装（namespace `opensandbox-system`、API key `dev-key`）。入口粘性需要 ingress-nginx（见 §3）。

## 0. P2 HA 语义（双副本）

- 控制面 `replicas: 2` + `PodDisruptionBudget minAvailable: 1`；通道状态不落盘，WS 落到任意
  副本时按台账（sessions.token_hash）重建，running 会话不再被启动对账误杀。
- **入口必须按会话粘性**：`/ws/bridge/<id>` 与 `/ws/session/<id>` 必须落在同一副本，否则
  桥接帧无法扇出给客户端。Ingress 用 `upstream-hash-by: $arg_token`（同一会话的桥接与
  客户端共用 `?token=`），不能用 `$uri`（两类路径前缀不同）。
- **哈希漂移自愈**：副本增减会改变一致性哈希环，长连接桥接可能停在旧副本。客户端落到
  无桥接副本时，控制面在握手阶段返回 HTTP 403（未 accept），Ingress 凭
  `proxy-next-upstream: "error timeout http_403"` 换副本重试，直到命中持有桥接的副本。
- 启动对账只结束创建超过 `CREATING_STALE_TIMEOUT_SECONDS` 的 `creating` 会话；`running`
  保留，等桥接/客户端重连重建通道。REST 管理面与 LLM 网关无状态，任意副本可服务。
- **P3 T1 冷恢复**：每会话两个 PVC——`ws-<session>`（工作区）与 `state-<session>`
  （`CODEX_HOME`）。`POST /api/sessions/<id>/sleep` 销毁沙箱、两卷保留、台账转 `idle`；
  `POST /api/sessions/<id>/resume` 重新准入、轮换 token、新沙箱挂原卷，客户端仍用原生
  `thread/resume` 回放历史。启动对账把沙箱不存在的 `running` 转 `idle`，可恢复。
- **P3 T2 空闲销毁**：无客户端、无进行中 turn、静默超过 `IDLE_TIMEOUT_SECONDS`（默认 900s）
  的会话由 sweeper 转 idle；`*requestApproval` 超过 `APPROVAL_TIMEOUT_SECONDS`（默认 300s）
  自动 decline。sweeper 只处理本副本持有桥接的通道。预热池不采用（`poolRef` 拒绝卷与
  networkPolicy），用镜像预拉 + `cloud_agents_sandbox_create_seconds` 观测创建时延。

## 1. 构建并加载镜像

```powershell
docker build --provenance=false --sbom=false -f control-plane/Dockerfile -t cloud-agents/control-plane:p3 .
docker pull postgres:17
kind load docker-image cloud-agents/control-plane:p3 --name cloud-agents-dev
kind load docker-image cloud-agents/sandbox:0.1.0 --name cloud-agents-dev
```

`--provenance=false --sbom=false` 是必需的：Docker Desktop 默认给镜像加 attestation manifest，
`kind load` 会因缺少子 digest 失败。`postgres:17` 由 kubelet 直接拉取（多平台 manifest 同样
不适合 `kind load`）；内网环境改为从内部 registry 拉取。

## 2. 创建 Secret（不入库）

`opensandbox-api-key` 必须与 OpenSandbox server 的 key 一致；`llm-api-key` 从 `.env` 读取。

```powershell
$envMap = @{}
Get-Content .env | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
  $k, $v = $_ -split '=', 2
  $envMap[$k] = $v
}
kubectl -n cloud-agents create secret generic cloud-agents-secrets `
  --from-literal=p1-auth-token=$($envMap['P1_AUTH_TOKEN']) `
  --from-literal=opensandbox-api-key=dev-key `
  --from-literal=llm-api-key=$($envMap['LLM_API_KEY']) `
  --from-literal=postgres-password=dev-pg-pass `
  --dry-run=client -o yaml | kubectl apply -f -
```

## 3. 部署

先装 ingress-nginx（kind 清单），再按节点 IP 配置入口基址：

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=300s

# kind 节点 IP（浏览器与沙箱都能到达）；用 nip.io 让同一域名解析到该 IP。
kubectl get node -o wide   # 取 INTERNAL-IP，例如 172.18.0.2
# 编辑 deploy/k8s/configmap.yaml：PUBLIC_BASE_URL: http://cloud-agents.<NODE_IP>.nip.io
```

```powershell
kubectl apply -k deploy/k8s
kubectl -n cloud-agents rollout status statefulset/postgres --timeout=300s
kubectl -n cloud-agents rollout status deploy/control-plane --timeout=300s
kubectl -n cloud-agents get pods
```

`control-plane` 启动时执行 `alembic upgrade head`；双副本同时启动可能有一副本迁移冲突后
重启重试一次，属预期。`PUBLIC_BASE_URL` 必须指向 Ingress（而非 Service），
桥接与浏览器才走同一粘性入口；沙箱 egress 白名单会自动加入该主机名。
`WORKSPACE_PVC_STORAGE_CLASS` 留空用集群默认（kind 为 `standard`）；其他集群按实际改。

### 3.1 kind 宿主可达（无 80/443 端口映射时）

kind 集群若创建时没配 `extraPortMappings`，宿主访问不到节点 80 端口，而沙箱 Pod 与
浏览器又必须使用同一个 URL。开发机用「socat 代理 + CoreDNS hosts 覆盖」打通：

```powershell
# 1) 宿主 127.0.0.1:80 -> 控制面节点 80（socat 容器加入 kind 网络）
docker run -d --name ca-ingress --network kind -p 80:80 alpine/socat `
  tcp-listen:80,fork,reuseaddr tcp-connect:cloud-agents-dev-control-plane:80
# 拿到代理在 kind 网络里的 IP（下面假设 172.19.0.5）
docker inspect ca-ingress --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 2) 集群内把 nip.io 域名覆盖到代理 IP（Corefile 的 .:53 块加 hosts 段后重启 CoreDNS）
#    hosts { <代理IP> cloud-agents.127.0.0.1.nip.io  fallthrough }
kubectl -n kube-system edit configmap coredns
kubectl -n kube-system rollout restart deploy/coredns
```

宿主解析 `cloud-agents.127.0.0.1.nip.io` 得到 127.0.0.1（nip.io 公共 DNS），走代理进
Ingress；沙箱 Pod 解析同一域名得到代理 IP。生产环境直接用真实负载均衡域名即可，
不需要这层代理。

## 4. 冒烟

```powershell
curl.exe -s http://cloud-agents.<NODE_IP>.nip.io/healthz
curl.exe -s -X POST http://cloud-agents.<NODE_IP>.nip.io/api/sessions `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>" -H "Content-Type: application/json" -d '{}'
```

拿返回的 `session_id` / `token` 直接使用 `ws_url`（已指向 Ingress）走原生 WS
（可用 `docs/tests/本地测试指南.md` 的客户端）。验收点：

- `kubectl -n opensandbox get pvc` 出现 `ws-<session_id>` 与 `state-<session_id>` 且 Bound；
- 真实 turn 写 `/workspace/hello.txt` 后，`kubectl -n opensandbox exec <pod> -c sandbox -- cat /workspace/hello.txt` 可见；
- `DELETE /api/sessions/<id>` 后 Pod 回收、Postgres 台账 `ended`；
- PVC 默认保留（`deleteOnSandboxTermination=false`），P3 T3 归档前需手动清理：
  `kubectl -n opensandbox delete pvc ws-<session_id> state-<session_id>`。

### 4.0 冷恢复冒烟

```powershell
# 休眠：销毁沙箱，保留两卷
curl.exe -s -X POST http://cloud-agents.<NODE_IP>.nip.io/api/sessions/<id>/sleep `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>" -o NUL -w "%{http_code}`n"   # 204

# 状态应为 idle，sandbox_id 为 null
curl.exe -s http://cloud-agents.<NODE_IP>.nip.io/api/sessions/<id> `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>"

# 恢复：返回新 token；用新 ws_url 连上后发原生 thread/resume
curl.exe -s -X POST http://cloud-agents.<NODE_IP>.nip.io/api/sessions/<id>/resume `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>"
```

验收点：休眠后沙箱 Pod 消失、两 PVC Bound；恢复后新沙箱 `/home/agent/.codex` 可见
`config.toml`/`state_5.sqlite`/`sessions/`；`thread/resume` 返回休眠前的历史轮次并可续聊。

### 4.1 P2 HA 验证（双副本 + 粘性 + 重建）

1. 建会话并连上 WS，发一轮 turn 确认流式与审批正常。
2. `kubectl -n cloud-agents delete pod <持有该会话的 control-plane pod>`；
   观察桥接与客户端各自重连（桥接指数退避、客户端 1013 重试），然后 `thread/resume` 续聊。
3. 台账中的会话应保持 `running`（或重连后仍可用），不因重启被标记 `ended`；
   `kubectl -n cloud-agents logs deploy/control-plane` 可见「通道已按台账重建」。
4. 两个副本分别 `kubectl -n cloud-agents exec ... -- curl localhost:8000/metrics`，
   均能出数；`/api/sessions/<id>` 从任意副本查询一致。

## 已知边界

- **pause/resume**：K8s 默认无 snapshot registry，pause 会 `PauseFailed`；P1.5 只走冷恢复设计，不用 pause。
- 多副本依赖 Ingress 粘性（`$arg_token`）；裸连 Service 时桥接与客户端可能落在不同副本，
  表现为握手被拒绝或连上后收不到流式事件。副本增减导致的哈希漂移由
  `proxy-next-upstream` 重试自愈；但滚动更新时旧 Pod 仍在 endpoints 内，客户端可能收到
  连接重置（而非稳定 403），客户端需 1s 退避重试（Web 自动重试列 P3 T7）。
- `state-<session>` 与 `ws-<session>` 两个 PVC 都由 OpenSandbox 创建；kind local-path 权限正常。
  真实 NFS 上非 root（uid 1000）写 `CODEX_HOME` 需要 `fsGroup` 或目录属主策略，D2 复核。
- 本清单不包含 TLS、NetworkPolicy 基线、Secret 轮换与 PodSecurity；P4 补。
- `postgres-password` 直接拼进 `DATABASE_URL`，生产口令如含 URL 特殊字符需先编码或改用完整
  `database-url` Secret 键。
