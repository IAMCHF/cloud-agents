# 沙箱镜像：pin codex + 控制面桥接 + 最小工具链。
# 构建上下文必须是仓库根：
#   docker build -f sandbox/images/Dockerfile -t cloud-agents/sandbox:0.1.0 .
# 版本必须与 web/src/codex/codex-version.txt 一致（CI 校验会比对）。

ARG NODE_IMAGE=node:22-slim
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
# 内网/受限网络构建时用 --build-arg APT_MIRROR=mirrors.example.com 切换 Debian 源。
ARG APT_MIRROR=deb.debian.org

FROM ${NODE_IMAGE} AS codex
ARG CODEX_VERSION=0.167.0
RUN npm install --global --prefix /opt/codex "@openai/codex@${CODEX_VERSION}"

FROM ${PYTHON_IMAGE} AS runtime
ARG CODEX_VERSION=0.167.0
ARG APT_MIRROR=deb.debian.org

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/opt/codex/bin:/app/.venv/bin:$PATH \
    CODEX_HOME=/home/agent/.codex \
    CODEX_VERSION=${CODEX_VERSION}

RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=3 update \
    && apt-get install -y --no-install-recommends git ca-certificates openssh-client \
    && rm -rf /var/lib/apt/lists/*

# codex npm 包是 node 启动器 + 平台原生二进制；node 从构建阶段拷入。
COPY --from=codex /usr/local/bin/node /usr/local/bin/node
COPY --from=codex /opt/codex /opt/codex

RUN useradd --create-home --uid 1000 --shell /bin/bash agent \
    && mkdir -p /app /workspace /home/agent/.codex \
    && chown -R agent:agent /home/agent /workspace

WORKDIR /app
COPY control-plane/pyproject.toml control-plane/uv.lock ./
RUN pip install --no-cache-dir uv==0.13.8 \
    && uv sync --frozen --no-dev --no-install-project \
    && rm -rf /root/.cache/uv

COPY control-plane/app ./app
RUN chown -R agent:agent /app

# 运行期约束（只读 rootfs、tmpfs、cgroup 限额）由编排层施加，见 sandbox/opensandbox 与 T6 compose。
USER agent
WORKDIR /workspace

ENTRYPOINT ["python", "-m", "app.bridge"]
