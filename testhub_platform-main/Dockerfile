# TestHub Docker 镜像（本机构建）
# 阶段：frontend-build → backend → nginx

# ---------- 1. 前端构建 ----------
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY frontend/ ./
RUN npm run build


# ---------- 2. Python 后端 ----------
FROM python:3.12-slim-bookworm AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
COPY requirements_optional.txt /tmp/requirements_optional.txt

ARG INSTALL_OPTIONAL=false
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && if [ "$INSTALL_OPTIONAL" = "true" ]; then \
         pip install --no-cache-dir -r /tmp/requirements_optional.txt \
           -i https://pypi.tuna.tsinghua.edu.cn/simple; \
       fi

COPY backend/ ./backend/
COPY start_backend.py ./
COPY media/ ./media/
COPY --from=frontend-build /app/frontend/dist ./frontend_dist/

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

RUN mkdir -p logs static_files \
    && find logs -mindepth 1 ! -name '.gitkeep' -delete 2>/dev/null || true

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["web"]


# ---------- 3. Nginx 网关（对外统一入口） ----------
FROM nginx:1.27-alpine AS nginx

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
