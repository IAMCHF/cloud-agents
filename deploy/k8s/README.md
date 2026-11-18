# Kubernetes 部署（P1.5 开发机验证）

在 kind 上部署控制面 + Postgres，沙箱走 OpenSandbox K8s 运行时，工作区用 PVC。
这是 P1.5 的双后端验证路径，不是生产清单；生产差异见 `docs/实施计划.md` 的 D1/D2 矩阵。

前置：kind 集群与 OpenSandbox charts 已按 `docs/tests/2026-11-18-P0-K8s与NFS可行性.md`
安装（namespace `opensandbox-system`、API key `dev-key`）。

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

```powershell
kubectl apply -k deploy/k8s
kubectl -n cloud-agents rollout status statefulset/postgres --timeout=300s
kubectl -n cloud-agents rollout status deploy/control-plane --timeout=300s
kubectl -n cloud-agents get pods
```

`control-plane` 启动时执行 `alembic upgrade head`；`PUBLIC_BASE_URL` 指向集群内 Service，
沙箱桥接通过 `control-plane.cloud-agents.svc.cluster.local:8000` 回连。
`WORKSPACE_PVC_STORAGE_CLASS` 留空用集群默认（kind 为 `standard`）；其他集群按实际改。

## 4. 冒烟

```powershell
kubectl -n cloud-agents port-forward svc/control-plane 18000:8000
```

另开终端：

```powershell
curl.exe -s http://127.0.0.1:18000/healthz
curl.exe -s -X POST http://127.0.0.1:18000/api/sessions `
  -H "Authorization: Bearer <P1_AUTH_TOKEN>" -H "Content-Type: application/json" -d '{}'
```

拿返回的 `session_id` / `token`，把 `ws_url` 的主机换成 `127.0.0.1:18000` 后走原生 WS
（可用 `docs/tests/本地测试指南.md` 的客户端）。验收点：

- `kubectl -n opensandbox get pvc` 出现 `ws-<session_id>` 且 Bound；
- 真实 turn 写 `/workspace/hello.txt` 后，`kubectl -n opensandbox exec <pod> -c sandbox -- cat /workspace/hello.txt` 可见；
- `DELETE /api/sessions/<id>` 后 Pod 回收、Postgres 台账 `ended`；
- PVC 默认保留（`deleteOnSandboxTermination=false`），P3 归档前需手动清理：
  `kubectl -n opensandbox delete pvc ws-<session_id>`。

## 已知边界

- **pause/resume**：K8s 默认无 snapshot registry，pause 会 `PauseFailed`；P1.5 只走冷恢复设计，不用 pause。
- 控制面单副本；P2 HA 需要入口粘性/共享 Postgres，见实施计划。
- 本清单不包含 Ingress、TLS、NetworkPolicy 基线、Secret 轮换与 PodSecurity；P4 补。
- `postgres-password` 直接拼进 `DATABASE_URL`，生产口令如含 URL 特殊字符需先编码或改用完整
  `database-url` Secret 键。
