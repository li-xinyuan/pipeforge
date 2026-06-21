# ConfigForge 生产环境部署指南

## 目录

- [部署前置检查清单](#部署前置检查清单)
- [Nginx HTTPS 反向代理配置](#nginx-https-反向代理配置)
- [Docker Compose SSL 部署](#docker-compose-ssl-部署)
- [Let's Encrypt 证书申请](#lets-encrypt-证书申请)
- [证书续期](#证书续期)
- [回滚方案](#回滚方案)

---

## 部署前置检查清单

在生产环境部署前，请确认以下配置项已正确设置：

| 检查项 | 环境变量 | 要求 | 说明 |
|--------|----------|------|------|
| 运行环境 | `CONFIGFORGE_ENV` | 必须为 `production` | 禁用调试模式，启用生产级日志 |
| JWT 密钥 | `CONFIGFORGE_JWT_SECRET` | 长度 ≥ 32 字符 | 用于签发和验证 JWT Token，必须为强随机字符串 |
| 加密密钥 | `CONFIGFORGE_ENCRYPTION_KEY` | Fernet 合法密钥 | 用于敏感数据加密，通过 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成 |
| SSL/TLS 证书 | — | 有效且未过期 | 域名匹配的证书文件（`.pem` / `.crt` + `.key`） |

### 快速生成密钥

```bash
# 生成 JWT_SECRET（≥32字符）
openssl rand -hex 32

# 生成 ENCRYPTION_KEY（Fernet 密钥）
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 环境变量验证脚本

```bash
#!/bin/bash
# 部署前环境检查

errors=0

# 检查 CONFIGFORGE_ENV
if [ "${CONFIGFORGE_ENV}" != "production" ]; then
  echo "[FAIL] CONFIGFORGE_ENV 未设置为 production"
  errors=$((errors + 1))
else
  echo "[PASS] CONFIGFORGE_ENV=production"
fi

# 检查 JWT_SECRET 长度
if [ ${#CONFIGFORGE_JWT_SECRET} -lt 32 ]; then
  echo "[FAIL] CONFIGFORGE_JWT_SECRET 长度不足 32 字符（当前: ${#CONFIGFORGE_JWT_SECRET}）"
  errors=$((errors + 1))
else
  echo "[PASS] CONFIGFORGE_JWT_SECRET 长度合规"
fi

# 检查 ENCRYPTION_KEY
if [ -z "$CONFIGFORGE_ENCRYPTION_KEY" ]; then
  echo "[FAIL] CONFIGFORGE_ENCRYPTION_KEY 未设置"
  errors=$((errors + 1))
else
  echo "[PASS] CONFIGFORGE_ENCRYPTION_KEY 已设置"
fi

# 检查 SSL 证书文件
if [ ! -f "/etc/nginx/ssl/fullchain.pem" ] || [ ! -f "/etc/nginx/ssl/privkey.pem" ]; then
  echo "[FAIL] SSL 证书文件不存在（/etc/nginx/ssl/fullchain.pem 或 privkey.pem）"
  errors=$((errors + 1))
else
  echo "[PASS] SSL 证书文件就绪"
fi

if [ $errors -gt 0 ]; then
  echo ""
  echo "共有 $errors 项检查未通过，请修复后再部署！"
  exit 1
else
  echo ""
  echo "所有检查通过，可以继续部署。"
fi
```

---

## Nginx HTTPS 反向代理配置

完整的 Nginx 配置示例文件位于 `deploy/nginx.conf.example`，以下为配置要点说明。

### 核心配置要点

1. **HTTP → HTTPS 跳转**：80 端口所有请求 301 跳转至 HTTPS
2. **TLS 协议版本**：仅启用 TLSv1.2 和 TLSv1.3
3. **HSTS**：`Strict-Transport-Security max-age=31536000; includeSubDomains`
4. **安全响应头**：X-Frame-Options、X-Content-Type-Options、CSP 等
5. **反向代理**：`/api/` 代理至后端 8000 端口，`/` 服务 SPA 静态文件
6. **上传限制**：`client_max_body_size 100M`

### 配置示例

```nginx
# HTTP → HTTPS 跳转
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;

    # HSTS（首次部署建议先使用短时长测试，确认无误后再改为 31536000）
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 安全头
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'" always;

    client_max_body_size 100m;

    # API 反向代理
    location /api/ {
        proxy_pass http://configforge_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # 静态资源缓存
    location /assets/ {
        proxy_pass http://configforge_backend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # SPA 前端
    location / {
        proxy_pass http://configforge_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Docker Compose SSL 部署

### SSL 卷挂载示例

在 `docker-compose.yml` 中为 nginx 服务添加 SSL 证书卷挂载：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"    # 开放 HTTPS 端口
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      # === SSL 证书挂载 ===
      - ./ssl/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
      - ./ssl/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
      # === Let's Encrypt webroot 验证（如使用 certbot） ===
      # - ./certbot-webroot:/var/www/certbot:ro
    restart: unless-stopped
```

### 完整部署步骤

```bash
# 1. 准备 SSL 证书目录
mkdir -p ssl

# 2. 将证书文件放入 ssl/ 目录
# cp /path/to/fullchain.pem ssl/
# cp /path/to/privkey.pem ssl/

# 3. 复制 nginx 配置示例
cp deploy/nginx.conf.example nginx/nginx.conf

# 4. 编辑 nginx.conf，替换 your-domain.com 为实际域名

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env，设置生产环境变量

# 6. 启动服务
docker compose up -d

# 7. 验证 HTTPS 可访问
curl -I https://your-domain.com/api/health
```

---

## Let's Encrypt 证书申请

### 方式一：Certbot Standalone 模式（推荐首次申请）

```bash
# 1. 安装 certbot
# macOS
brew install certbot

# Ubuntu/Debian
sudo apt update && sudo apt install -y certbot

# CentOS/RHEL
sudo yum install -y certbot

# 2. 停止占用 80 端口的服务
docker compose stop nginx

# 3. 申请证书（替换 your-domain.com）
sudo certbot certonly --standalone \
  -d your-domain.com \
  --email admin@your-domain.com \
  --agree-tos \
  --no-eff-email

# 4. 复制证书到项目目录
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
chmod 644 ./ssl/fullchain.pem
chmod 600 ./ssl/privkey.pem

# 5. 重启服务
docker compose up -d
```

### 方式二：Certbot Webroot 模式（无需停机）

```bash
# 1. 在 nginx 配置中添加 .well-known 路径（已包含在 nginx.conf.example 中）
#    location /.well-known/acme-challenge/ {
#        root /var/www/certbot;
#    }

# 2. 创建 webroot 目录
mkdir -p certbot-webroot

# 3. 启动 nginx
docker compose up -d nginx

# 4. 申请证书
sudo certbot certonly --webroot \
  -w ./certbot-webroot \
  -d your-domain.com \
  --email admin@your-domain.com \
  --agree-tos \
  --no-eff-email

# 5. 复制证书并重启
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
docker compose restart nginx
```

### 方式三：Docker Certbot（容器化方式）

```yaml
# 在 docker-compose.yml 中添加 certbot 服务
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./ssl:/etc/letsencrypt
      - ./certbot-webroot:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h; done'"
```

---

## 证书续期

### 自动续期（Cron）

Let's Encrypt 证书有效期为 90 天，建议在到期前 30 天自动续期。

```bash
# 添加 cron 任务
sudo crontab -e

# 每天凌晨 2:00 检查并续期
0 2 * * * certbot renew --quiet --deploy-hook "cp /etc/letsencrypt/live/your-domain.com/*.pem /path/to/CCTEST/ssl/ && docker compose -f /path/to/CCTEST/docker-compose.yml restart nginx"
```

### 手动续期

```bash
# 1. 续期证书
sudo certbot renew

# 2. 复制新证书
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/

# 3. 重载 nginx（无需重启，使用 reload 实现零停机）
docker compose exec nginx nginx -s reload
```

### 续期验证

```bash
# 检查证书有效期
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# 测试续期流程（不实际续期）
sudo certbot renew --dry-run
```

---

## 回滚方案

### 场景一：配置变更导致故障

```bash
# 1. 回滚 nginx 配置到上一个已知正常版本
cd /path/to/CCTEST
git log --oneline -5 -- nginx/nginx.conf
git checkout <commit-hash> -- nginx/nginx.conf

# 2. 重载 nginx
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# 3. 验证服务恢复
curl -I https://your-domain.com/api/health
```

### 场景二：SSL 证书问题

```bash
# 1. 临时回退到 HTTP（仅用于紧急恢复）
#    修改 nginx.conf，注释 HTTPS server 块，恢复 HTTP server 块
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload

# 2. 修复证书后重新启用 HTTPS
#    替换正确的证书文件
cp /path/to/correct/fullchain.pem ./ssl/
cp /path/to/correct/privkey.pem ./ssl/
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload
```

### 场景三：应用版本回滚

```bash
# 1. 查看当前运行的镜像版本
docker compose images

# 2. 回滚到上一个版本
git log --oneline -5
git checkout <stable-commit-hash>

# 3. 重新构建并启动
docker compose down
docker compose build --no-cache
docker compose up -d

# 4. 验证服务
curl -I https://your-domain.com/api/health
```

### 场景四：完全回滚（全量恢复）

```bash
# 1. 停止所有服务
docker compose down

# 2. 恢复代码到稳定版本
git checkout <stable-tag>

# 3. 恢复数据（如有备份）
# cp -r /backup/data ./data

# 4. 恢复环境变量
# cp /backup/.env .env

# 5. 重新启动
docker compose up -d

# 6. 全面验证
curl -I https://your-domain.com/api/health
curl -I https://your-domain.com/
```

### 回滚检查清单

- [ ] 确认回滚目标版本/配置
- [ ] 通知相关人员即将进行回滚
- [ ] 备份当前状态（数据、配置、日志）
- [ ] 执行回滚操作
- [ ] 验证服务功能正常
- [ ] 确认 HTTPS 证书有效
- [ ] 检查日志无异常错误
- [ ] 通知相关人员回滚完成
- [ ] 记录回滚原因和过程
