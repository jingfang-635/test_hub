# TestHub Docker 本机构建部署指南

> 适用：公司内网 Windows / Linux / macOS，**无需**逐步安装 Python、Node、MySQL、Redis。  
> 只需安装 **Docker Desktop**（或 Docker Engine + Compose）。

---

## 一、前置条件

| 项目 | 要求 |
|------|------|
| Docker | Docker Desktop 4.x+（Windows/Mac）或 Docker 24+ + Compose v2 |
| 内存 | 建议 8GB+ |
| 磁盘 | 建议预留 10GB+（含镜像与数据卷） |
| 网络 | 首次构建需拉取 `mysql:8.0`、`redis:7-alpine`、`node:20`、`python:3.12` 等基础镜像 |

---

## 二、快速启动（3 步）

### Windows

```cmd
cd testhub_platform-main
copy .env.docker.example .env
notepad .env
docker-start.bat
```

### Linux / macOS

```bash
cd testhub_platform-main
cp .env.docker.example .env
vim .env
chmod +x docker-start.sh
./docker-start.sh
```

或手动：

```bash
docker compose up -d --build
```

### 必改项（`.env`）

| 变量 | 说明 |
|------|------|
| `DB_PASSWORD` | MySQL root 密码 |
| `SECRET_KEY` | Django 密钥（随机长字符串） |
| `DJANGO_SUPERUSER_PASSWORD` | 首次登录管理员密码 |

---

## 三、访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost （端口由 `FRONTEND_PORT` 控制，默认 80） |
| API 文档 | http://localhost/api/docs/ |
| 管理后台 | http://localhost/admin/ |

默认管理员（若 `.env` 中已配置）：

- 用户名：`admin`（`DJANGO_SUPERUSER_USERNAME`）
- 密码：`DJANGO_SUPERUSER_PASSWORD` 的值

---

## 四、容器说明

| 容器 | 作用 |
|------|------|
| `testhub-mysql` | MySQL 8 数据库 |
| `testhub-redis` | Redis（任务队列 / WebSocket） |
| `testhub-backend` | Django + Uvicorn（API / SSE / WebSocket） |
| `testhub-qcluster` | Django-Q2 异步任务 |
| `testhub-scheduler` | 定时任务调度 |
| `testhub-nginx` | 前端静态资源 + 反向代理 |

数据持久化卷：`mysql_data`、`redis_data`、`media_data`、`logs_data`

---

## 五、常用命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f backend

# 停止（保留数据）
docker compose down

# 停止并删除数据卷（⚠️ 清空数据库）
docker compose down -v

# 重新构建后启动
docker compose up -d --build

# 仅执行数据库迁移
docker compose exec backend /entrypoint.sh migrate

# 进入后端 shell
docker compose exec backend python backend/manage.py shell
```

---

## 六、可选：安装完整功能依赖

默认镜像仅安装**核心依赖**（用例管理、API 测试、数据工厂等）。

若需要 UI 自动化 / APP 自动化 / AI 等可选模块的 Python 包，在 `.env` 中设置：

```env
INSTALL_OPTIONAL=true
```

然后重新构建：

```bash
docker compose build --no-cache
docker compose up -d
```

> **说明**：UI 自动化在容器内运行 Playwright/Selenium 还需额外安装浏览器，建议在宿主机或专用执行机跑 UI 用例；Docker 更适合部署平台本身。

---

## 七、公司内网分发方式

### 方式 A：Git 仓库 + 本机构建（推荐）

1. 将代码 push 到公司 Git / GitHub
2. 同事 `git clone` 后执行第二节步骤
3. 镜像在各自机器本地 build，**不需要私有镜像仓库**

### 方式 B：离线分发基础镜像

若内网无法访问 Docker Hub，由 IT 在一台能联网的机器上：

```bash
docker pull mysql:8.0 redis:7-alpine node:20-alpine python:3.12-slim-bookworm nginx:1.27-alpine
docker save mysql:8.0 redis:7-alpine node:20-alpine python:3.12-slim-bookworm nginx:1.27-alpine -o base-images.tar
```

内网机器：

```bash
docker load -i base-images.tar
docker compose up -d --build
```

---

## 八、升级

```bash
git pull
docker compose up -d --build
```

后端 entrypoint 会自动执行 `migrate` 和初始化命令。

---

## 九、常见问题

### 1. 80 端口被占用

修改 `.env`：`FRONTEND_PORT=8080`，访问 http://localhost:8080

### 2. 构建 npm/pip 很慢

已配置国内镜像（npmmirror / 清华源）。若仍慢，配置 Docker Desktop 代理或公司内网镜像加速。

### 3. backend 一直 restarting

```bash
docker compose logs backend
```

常见原因：MySQL 密码与 `.env` 不一致（若曾换过密码需 `docker compose down -v` 重建数据卷）。

### 4. 飞书 / AI 等第三方配置

在 `.env` 中追加对应变量（参考 `config.yaml.example`），重启 backend：

```bash
docker compose restart backend qcluster scheduler
```

---

## 十、与本地开发模式对比

| | Docker 部署 | 本地 venv + npm |
|--|-------------|-----------------|
| 环境安装 | 仅 Docker | Python/Node/MySQL/Redis 逐个装 |
| 启动 | `docker compose up -d` | `start.bat` 多窗口 |
| 适用 | 公司统一交付、演示、内网服务器 | 日常开发调试 |

本地开发仍可使用 `start.bat`；Docker 用于「拿来即用」交付。
