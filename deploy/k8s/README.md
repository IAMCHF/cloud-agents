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
- 启动对账只结束创建超过 `CREATING_STALE_TIMEOUT_SECONDS` 的 `creating` 会话；`running`
  保留，等桥接/客户端重连重建通道。REST 管理面与 LLM 网关无状态，任意副本可服务。

## 1. 构建并加载镜像

```powershell
docker build --provenance=false --sbom=false -f control-plane/Dockerfile -t cloud-agents/control-plane:p15 .
docker pull postgres:17
kind load docker-image cloud-agents/control-plane:p15 --name cloud-agents-dev
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

## 4. 冒烟

```powershell
curl.exe -s http://cloud-agents.<NODE_IP>.nip.io/healthz
curl.exe -s -X POST http://cloud-agents.<NODE_IP>.nip.io/api/sessions `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>" -H "Content-Type: application/json" -d '{}'
```

拿返回的 `session_id` / `token` 直接使用 `ws_url`（已指向 Ingress）走原生 WS
（可用 `docs/tests/本地测试指南.md` 的客户端）。验收点：

- `kubectl -n opensandbox get pvc` 出现 `ws-<session_id>` 且 Bound；
- 真实 turn 写 `/workspace/hello.txt` 后，`kubectl -n opensandbox exec <pod> -c sandbox -- cat /workspace/hello.txt` 可见；
- `DELETE /api/sessions/<id>` 后 Pod 回收、Postgres 台账 `ended`；
- PVC 默认保留（`deleteOnSandboxTermination=false`），P3 归档前需手动清理：
  `kubectl -n opensandbox delete pvc ws-<session_id>`。

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
- 多副本依赖 Ingress 粘性（`$arg_token`）；若无 Ingress 直连 Service，桥接与客户端可能落在
  不同副本，表现为客户端连上但收不到流式事件。
- 本清单不包含 TLS、NetworkPolicy 基线、Secret 轮换与 PodSecurity；P4 补。
- `postgres-password` 直接拼进 `DATABASE_URL`，生产口令如含 URL 特殊字符需先编码或改用完整
  `database-url` Secret 键。
