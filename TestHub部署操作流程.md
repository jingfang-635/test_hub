# TestHub 智能测试管理平台 - 详细部署操作流程

> 部署指南文档  
> 生成日期：2026年7月25日

---

## 目录

- [一、系统要求](#一系统要求)
  - [1.1 必需软件清单](#11-必需软件清单)
  - [1.2 推荐Windows安装顺序](#12-推荐windows安装顺序)
- [二、部署步骤（分阶段）](#二部署步骤分阶段)
  - [阶段一：准备项目文件](#阶段一准备项目文件)
  - [阶段二：Python 后端部署](#阶段二python-后端部署)
  - [阶段三：Vue 前端部署](#阶段三vue-前端部署)
  - [阶段四：启动定时任务（可选）](#阶段四启动定时任务可选)
- [三、验证部署是否成功](#三验证部署是否成功)
- [四、生产环境部署（可选）](#四生产环境部署可选)
- [五、常见问题排查](#五常见问题排查)
- [六、快速启动命令汇总](#六快速启动命令汇总)
- [七、项目核心功能](#七项目核心功能)

---

## 一、系统要求

### 1.1 必需软件清单

| 软件 | 版本要求 | 下载地址 | 说明 |
|------|---------|---------|------|
| **Python** | 3.12.x | https://www.python.org/downloads/ | 后端运行环境 |
| **Node.js** | 18.x 或更高 | https://nodejs.org/ | 前端构建环境 |
| **MySQL** | 8.0+ | https://dev.mysql.com/downloads/mysql/ | 数据库 |
| **Redis** | 6.0+ | https://redis.io/download/ | 可选，用于APP自动化测试 |
| **Java** | 17+ | https://adoptium.net/ | 可选，用于Allure报告生成 |

### 1.2 推荐Windows安装顺序

```
1. 安装 Python 3.12  →  安装时勾选 "Add Python to PATH"
2. 安装 Node.js     →  安装时保持默认选项
3. 安装 MySQL 8.0   →  记住设置的root密码
4. 安装 Redis       →  Windows版本可从GitHub下载
5. 安装 Java 17     →  可选，用于报告生成
```

---

## 二、部署步骤（分阶段）

### 阶段一：准备项目文件

#### 步骤 1：确认项目目录结构

确保您的项目目录结构如下：

```
testhub_platform-main/
├── testhub_platform-main/        # 项目主目录
│   ├── apps/                      # Django应用模块
│   ├── backend/                   # Django配置
│   ├── frontend/                  # Vue3前端
│   ├── allure/                    # Allure报告工具
│   ├── manage.py                  # Django管理脚本
│   ├── requirements.txt           # Python依赖清单
│   └── .env.example               # 环境变量示例
└── AI测试平台介绍和部署手册.pdf
```

#### 步骤 2：打开命令行

Windows：按 `Win + R`，输入 `cmd` 或 `powershell`，回车

切换到项目目录：

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main
```

---

### 阶段二：Python 后端部署

#### 步骤 1：创建 Python 虚拟环境

```cmd
python -m venv venv
```

#### 步骤 2：激活虚拟环境

```cmd
venv\Scripts\activate
```

> 💡 **提示**：激活成功后，命令行前面会出现 `(venv)` 标识

#### 步骤 3：升级 pip 并安装依赖

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ **注意**：这一步可能需要几分钟，请耐心等待

#### 步骤 4：创建配置文件

```cmd
copy .env.example .env
```

使用记事本或VS Code打开 `.env` 文件，**必须修改以下内容**：

```env
# 必填：设置一个安全的密钥（任意字符串即可）
SECRET_KEY=my-secret-key-2024-change-this

# 必填：数据库配置（填写您安装MySQL时设置的密码）
DB_NAME=testhub
DB_USER=root
DB_PASSWORD=您的MySQL密码
DB_HOST=127.0.0.1
DB_PORT=3306

# 可选：Redis配置
REDIS_URL=redis://127.0.0.1:6379/0

# 保持默认
DEBUG=True
ALLOWED_HOSTS=*
LANGUAGE_CODE=zh-hans
TIME_ZONE=Asia/Shanghai
```

#### 步骤 5：创建 MySQL 数据库

打开新的命令行窗口，登录 MySQL：

```cmd
mysql -u root -p
```

输入密码后，执行以下 SQL：

```sql
CREATE DATABASE testhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

#### 步骤 6：执行数据库迁移

回到项目目录的命令行窗口（需保持虚拟环境激活）：

```cmd
python manage.py makemigrations
python manage.py migrate
```

#### 步骤 7：创建管理员账号

```cmd
python manage.py createsuperuser
```

按提示输入用户名、邮箱和密码（密码至少8位）。

#### 步骤 8：初始化系统数据

```cmd
# 初始化UI自动化元素定位策略
python manage.py init_locator_strategies

# 初始化APP自动化组件库
python manage.py load_component_pack
```

#### 步骤 9：启动后端服务

```cmd
python manage.py runserver 0.0.0.0:8000
```

> ✅ **成功标志**：看到 `Starting development server at http://0.0.0.0:8000/` 表示成功

---

### 阶段三：Vue 前端部署

#### 步骤 10：打开新的命令行窗口

**保持后端服务运行**，打开另一个命令行窗口。

#### 步骤 11：进入前端目录

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main\frontend
```

#### 步骤 12：安装前端依赖

```cmd
npm install
```

> ⚠️ **注意**：这一步可能需要几分钟

#### 步骤 13：启动前端开发服务器

```cmd
npm run dev
```

> ✅ **成功标志**：看到 `Local: http://localhost:3000/` 表示成功

---

### 阶段四：启动定时任务（可选）

#### 步骤 14：启动定时任务调度器

打开**第三个**命令行窗口：

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main
venv\Scripts\activate
python manage.py run_all_scheduled_tasks
```

#### 步骤 15：启动 Celery Worker（可选）

用于处理异步任务（如APP自动化测试）：

```cmd
celery -A backend worker -l info
```

---

## 三、验证部署是否成功

### 3.1 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端界面** | http://localhost:3000 | 用户操作界面 |
| **后端 API** | http://localhost:8000 | 后端接口服务 |
| **API 文档** | http://localhost:8000/api/docs/ | Swagger API文档 |
| **管理后台** | http://localhost:8000/admin/ | Django后台管理 |

### 3.2 检查清单

- [x] 前端页面能正常打开并显示登录界面
- [x] 使用创建的管理员账号可以登录系统
- [x] API文档页面可以正常访问
- [x] 管理后台可以正常登录
- [x] 页面切换无报错

---

## 四、生产环境部署（可选）

### 4.1 Linux 服务器部署

```bash
# 创建用户和目录
sudo useradd -m -s /bin/bash testhub
sudo mkdir -p /opt/testhub_platform
sudo chown -R testhub:testhub /opt/testhub_platform

# 上传项目代码到 /opt/testhub_platform

# Python 环境
cd /opt/testhub_platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install daphne channels channels-redis

# 构建前端
cd /opt/testhub_platform/frontend
npm install
npm run build

# 收集静态文件
source /opt/testhub_platform/venv/bin/activate
cd /opt/testhub_platform
python manage.py collectstatic --noinput
python manage.py migrate
```

### 4.2 使用 systemd 管理服务

创建 `/etc/systemd/system/testhub-asgi.service`：

```ini
[Unit]
Description=TestHub ASGI Service
After=network.target

[Service]
User=testhub
WorkingDirectory=/opt/testhub_platform
Environment="DJANGO_SETTINGS_MODULE=backend.settings"
EnvironmentFile=/opt/testhub_platform/.env
ExecStart=/opt/testhub_platform/venv/bin/daphne -b 0.0.0.0 -p 8000 backend.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable testhub-asgi
sudo systemctl start testhub-asgi

# 查看状态
sudo systemctl status testhub-asgi

# 查看日志
journalctl -u testhub-asgi -f
```

### 4.3 配置 Nginx 反向代理

创建 `/etc/nginx/conf.d/testhub.conf`：

```nginx
server {
    listen 80;
    server_name 服务器IP;

    # 静态文件
    location /static/ {
        alias /opt/testhub_platform/static/;
    }

    location /media/ {
        alias /opt/testhub_platform/media/;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 前端部署
    location / {
        root /opt/testhub_platform/frontend/dist;
        try_files $uri /index.html;
    }
}
```

重启 Nginx：

```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 五、常见问题排查

### Q1: pip 安装失败怎么办？

尝试使用国内镜像源：

```cmd
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: npm install 很慢？

设置淘宝镜像源：

```cmd
npm config set registry https://registry.npmmirror.com
npm install
```

### Q3: 数据库连接失败？

- 确认 MySQL 服务正在运行
- 检查 `.env` 文件中的数据库密码是否正确
- 确认数据库 `testhub` 已创建

### Q4: 端口被占用怎么办？

Windows：查找占用端口的进程

```cmd
netstat -ano | findstr :8000
```

然后结束该进程：

```cmd
taskkill /PID 进程号 /F
```

### Q5: 前端无法访问后端API？

- 确认后端服务正在运行
- 检查 `backend/settings.py` 中的 CORS 配置
- 开发模式下默认允许 localhost 访问

---

## 六、快速启动命令汇总（Windows）

### 🔧 后端服务

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

### 🎨 前端服务（新窗口）

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main\frontend
npm run dev
```

### ⏰ 定时任务（新窗口）

```cmd
cd e:\AItest\testhub_platform-main\testhub_platform-main
venv\Scripts\activate
python manage.py run_all_scheduled_tasks
```

---

## 七、项目核心功能

部署成功后，您可以使用以下功能：

| 模块 | 功能说明 |
|------|---------|
| 🤖 AI需求分析 | 上传文档，自动生成测试用例 |
| 📝 用例管理 | 创建、编辑、版本控制测试用例 |
| 🔍 用例评审 | 多人协作评审测试用例 |
| 🌐 API测试 | 接口测试、自动化执行、报告生成 |
| 🖥️ UI自动化 | Web UI自动化测试（支持Selenium/Playwright） |
| 📱 APP自动化 | Android APP自动化测试 |
| 🏭 数据工厂 | 51+测试数据生成工具 |
| 📊 测试报告 | Allure专业测试报告 |

---

## 附录：项目信息

- **项目名称**：TestHub 智能测试管理平台
- **技术栈**：Django 4.2 + Vue 3.3
- **后端框架**：Django REST Framework
- **前端框架**：Vue 3 + Element Plus
- **数据库**：MySQL 8.0+
- **缓存**：Redis 6.0+（可选）
- **Python版本**：3.12.x
- **Node.js版本**：18.x+

---

<p align="center">
  <strong>— 文档结束 —</strong><br>
  如有问题，请参考项目文档或联系技术支持
</p>