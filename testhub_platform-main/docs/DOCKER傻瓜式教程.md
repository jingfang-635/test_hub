# TestHub 傻瓜式 Docker 教程（Windows 版）

> **适合谁**：完全没配过程序环境，只想把 TestHub 跑起来的人。  
> **你要装的软件**：只有 **1 个** —— Docker Desktop。  
> **不用装**：Python、Node.js、MySQL、Redis（全部在 Docker 里自动搞定）。

---

## 最终效果

跟着做完后，浏览器打开 **http://localhost**，用账号 **admin** 登录，就能用 TestHub 了。

---

## 第 0 步：确认电脑配置

| 项目 | 最低要求 |
|------|----------|
| 系统 | Windows 10/11 64 位 |
| 内存 | 8GB（建议 16GB） |
| 硬盘 | 空出至少 **10GB** |
| 网络 | 第一次启动要能上网（下载 Docker 镜像） |

---

## 第 1 步：安装 Docker Desktop

### 1.1 下载

1. 打开浏览器，访问：https://www.docker.com/products/docker-desktop/
2. 点击 **Download for Windows**
3. 下载 `Docker Desktop Installer.exe`

### 1.2 安装

1. 双击安装包，一路 **OK / 安装**
2. 如果问是否用 WSL 2，选 **是**（推荐）
3. 如果提示安装 WSL，按提示装完 **重启电脑**
4. 重启后，桌面会出现 **Docker Desktop** 图标

### 1.3 确认 Docker 已启动

1. 双击打开 **Docker Desktop**
2. 左下角变成 **绿色 / Engine running** 即表示成功
3. 按 `Win + R`，输入 `cmd`，回车，在黑窗口里输入：

```cmd
docker compose version
```

看到类似 `Docker Compose version v2.x.x` 就 OK。

> **如果提示不是内部命令**：说明 Docker 没装好或没启动，回到 1.3 重新打开 Docker Desktop，等 1～2 分钟再试。

---

## 第 2 步：拿到项目代码

任选一种方式：

### 方式 A：Git 克隆（公司用 Git 时）

```cmd
cd D:\
git clone 你的仓库地址
cd testhub_platform-main\testhub_platform-main
```

### 方式 B：解压 ZIP（最简单）

1. 把项目 ZIP 解压到例如：`D:\testhub_platform-main\testhub_platform-main`
2. 确认这个文件夹里能看到这些文件：
   - `docker-compose.yml`
   - `Dockerfile`
   - `docker-start.bat`
   - `.env.docker.example`

---

## 第 3 步：改 3 个密码（必做）

### 3.1 复制配置文件
      
1. 进入项目文件夹（有 `docker-start.bat` 的那一层）
2. 在文件夹空白处 **Shift + 右键** → **在此处打开 PowerShell 窗口**（或 cmd）
3. 输入：

```cmd
copy .env.docker.example .env
``` 

### 3.2 用记事本打开 .env

```cmd
notepad .env
```

### 3.3 只改下面 3 行（别的先别动）

找到并修改（示例，请换成你自己的）：

```env
DB_PASSWORD=MyCompany@2024
SECRET_KEY=abc123xyz-随便写一长串-不要和别人一样
DJANGO_SUPERUSER_PASSWORD=Admin@2024
```

| 这行是什么 | 干什么用 |
|------------|----------|
| `DB_PASSWORD` | 数据库密码（自己定，记住就行） |
| `SECRET_KEY` | 系统密钥（随便一长串英文数字） |
| `DJANGO_SUPERUSER_PASSWORD` | **你登录 TestHub 的密码** |

4. **Ctrl + S** 保存，关闭记事本

> **登录账号固定是**：用户名 `admin`，密码就是你写的 `DJANGO_SUPERUSER_PASSWORD`

---

## 第 4 步：一键启动

### 方法 1：双击启动（推荐）

直接双击文件夹里的 **`docker-start.bat`**

### 方法 2：命令行启动

```cmd
cd /d D:\testhub_platform-main\testhub_platform-main
docker compose up -d --build
```

### 启动过程中你会看到什么

- **第一次**：会跑 **10～30 分钟**（下载镜像 + 安装依赖），这是正常的，去喝杯咖啡
- 窗口里滚动很多行 `Building`、`Downloading` 都正常
- 最后出现 **启动完成** 或命令行不再报错即可

### 怎么确认真的启动了

再开一个 cmd 窗口，输入：

```cmd
cd /d D:\testhub_platform-main\testhub_platform-main
docker compose ps
```

应该看到 6 个容器，状态都是 **Up** 或 **running**：

| 名字 | 干什么的 |
|------|----------|
| testhub-nginx | 网页入口 |
| testhub-backend | 后端 API |
| testhub-mysql | 数据库 |
| testhub-redis | 缓存/队列 |
| testhub-qcluster | 后台任务 |
| testhub-scheduler | 定时任务 |

---
    
## 第 5 步：打开浏览器使用

1. 打开 Chrome / Edge
2. 地址栏输入：**http://localhost**
3. 看到登录页
4. 输入：
   - 用户名：`admin`
   - 密码：第 3 步你在 `.env` 里设的 `DJANGO_SUPERUSER_PASSWORD`
5. 登录成功 🎉

### 其他常用地址

| 地址 | 用途 |
|------|------|
| http://localhost | 主界面 |
| http://localhost/api/docs/ | 接口文档 |
| http://localhost/admin/ | 管理后台 |

---

## 第 6 步：以后每天怎么用

### 开机后第一次用

1. 打开 **Docker Desktop**（等它变绿）
2. 双击 **`docker-start.bat`**

或者（如果上次没关过容器，可能已经在跑）：

```cmd
docker compose up -d
```

### 下班 / 不用时关闭（数据不会丢）

在项目文件夹 cmd 里：

```cmd
docker compose down
```

### 第二天再开

```cmd
docker compose up -d
```

不用重新 `build`，秒开。

---

## 给同事的「复制粘贴版」清单

把下面这段直接发给同事：

```
【TestHub 安装 - 5 步搞定】

1. 安装 Docker Desktop，打开后等左下角变绿
2. 解压/克隆项目到本地
3. 进入 testhub_platform-main 文件夹
4. 执行：copy .env.docker.example .env
5. 记事本打开 .env，改 3 行密码，保存
6. 双击 docker-start.bat，等 10~30 分钟
7. 浏览器打开 http://localhost，账号 admin，密码是 .env 里 DJANGO_SUPERUSER_PASSWORD

详细图文：docs/DOCKER傻瓜式教程.md
```

---

## 常见问题（照着做就行）

### ❌ 问题 1：打不开 http://localhost

**检查：**

```cmd
docker compose ps
```

- 如果 `testhub-nginx` 不是 Up → 等 2 分钟再试，或看「问题 4」
- 如果 6 个都是 Up → 试试 http://127.0.0.1

---

### ❌ 问题 2：80 端口被占用

1. 记事本打开 `.env`
2. 把 `FRONTEND_PORT=80` 改成 `FRONTEND_PORT=8080`
3. 保存后执行：

```cmd
docker compose down
docker compose up -d
```

4. 浏览器访问：**http://localhost:8080**

---

### ❌ 问题 3：docker-start.bat 闪退

1. 先打开 Docker Desktop，确认已启动
2. `Win + R` → 输入 `cmd` → 在项目文件夹执行：

```cmd
docker compose up -d --build
```

3. 看最后几行红色报错，对照下面：

| 报错关键词 | 怎么办 |
|------------|--------|
| `connect` / `timeout` / `registry` | 网络问题，见「问题 6」 |
| `port is already allocated` | 端口被占，见「问题 2」 |
| `Access denied` | 用管理员身份打开 cmd 再试 |

---

### ❌ 问题 4：backend 一直重启

```cmd
docker compose logs backend
```

**最常见原因**：改过 `DB_PASSWORD` 但数据库已经用旧密码建过了。

**解决办法（会清空数据库，第一次部署无所谓）：**

```cmd
docker compose down -v
docker compose up -d --build
```

---

### ❌ 问题 5：登录提示用户名或密码错误

1. 确认用户名是 **`admin`**（全小写）
2. 密码是 `.env` 里 **`DJANGO_SUPERUSER_PASSWORD`** 的值，不是 `DB_PASSWORD`
3. 如果还是不行，重置：

```cmd
docker compose down -v
docker compose up -d --build
```

（会重建数据库和管理员账号）

---

### ❌ 问题 6：下载镜像很慢 / 失败

**能连外网时：**

1. 打开 Docker Desktop → **Settings** → **Docker Engine**
2. 在 JSON 里加上（或合并进现有配置）：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
```

3. 点 **Apply & Restart**，重新运行 `docker-start.bat`

**公司完全不能上网：**

把 `docs/DOCKER部署.md` 第七节「离线分发」交给 IT 处理。

---

### ❌ 问题 7：电脑太卡

Docker Desktop → Settings → Resources：

- Memory 调到 **4GB～6GB**
- 不用 TestHub 时执行 `docker compose down`

---

## 更新到新版本代码

```cmd
cd /d D:\testhub_platform-main\testhub_platform-main
git pull
docker compose up -d --build
```

数据库数据会保留（除非用了 `down -v`）。

---

## 功能说明（知道即可）

| 功能 | Docker 里能不能用 |
|------|-------------------|
| 用例管理、API 测试、数据工厂 | ✅ 开箱即用 |
| 用例评审、测试计划 | ✅ 开箱即用 |
| UI 自动化（浏览器测试） | ⚠️ 平台能开，真正跑浏览器建议在 Windows 本机配 Playwright |
| APP 自动化 | ⚠️ 需要连安卓手机/模拟器，Docker 里一般不做 |
| AI 需求分析 | ⚠️ 要在系统里配置 AI 的 API Key |

---

## 一张图看懂全流程

```
安装 Docker Desktop
        ↓
拿到项目文件夹
        ↓
copy .env.docker.example .env
        ↓
记事本改 3 个密码
        ↓
双击 docker-start.bat（等 10~30 分钟）
        ↓
浏览器 http://localhost
        ↓
admin + 你的密码 登录
        ↓
完成 ✅
```

---

## 需要帮助时，收集这些信息

找 IT 或开发同事时，把下面命令的输出截图发过去：

```cmd
docker compose version
docker compose ps
docker compose logs backend --tail 50
```

---

**更完整的运维说明** → 看 [DOCKER部署.md](./DOCKER部署.md)
