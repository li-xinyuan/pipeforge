# ConfigForge 优化提升详细实施计划

> 编制日期：2026-06-20
> 修订日期：2026-06-21（根据 [PLAN_REVIEW_AUDIT.md](PLAN_REVIEW_AUDIT.md) 审核报告修订）
> 版本范围：v0.8.1 → v1.2.0
> 前置文档：[PROJECT_OPTIMIZATION_RECOMMENDATIONS.md](PROJECT_OPTIMIZATION_RECOMMENDATIONS.md)
> 审核报告：[PLAN_REVIEW_AUDIT.md](PLAN_REVIEW_AUDIT.md)
> 总任务数：44 项

---

## 总览

| Phase | 版本 | 核心目标 | 子任务数 | 优先级 |
|-------|------|----------|----------|--------|
| 5A | v0.8.1 | 安全加固 | 10 | P0 — 阻塞生产部署 |
| 5B | v0.9.0 | 性能与体验 | 10 | P1 — 影响用户体验 |
| 5C | v0.9.5 | 代码质量 | 11 | P2 — 影响可维护性 |
| 5D | v1.0.0 | 功能增强 | 7 | P3 — 补齐功能短板 |
| 5E | v1.2.0 | 架构演进 | 6 | P4 — 长期规划 |

---

## Phase 5A：安全加固（v0.8.1）

> **目标**：修复所有安全缺陷，确保系统可在生产环境安全运行。
> **验收标准**：通过安全扫描，无 P0 级安全缺陷，默认配置即安全。

---

### T-5A-01 首次登录强制修改默认密码

**关联缺陷**：D-02
**优先级**：P0

**问题**：`user_store.py` 的 `ensure_default_admin()` 创建 `admin/admin123`，无强制修改提示，部署后若未修改密码，攻击者可直接登录。

**方案**：
1. `User` 模型添加 `must_change_password: bool = False` 字段
2. `ensure_default_admin()` 创建用户时设置 `must_change_password=True`
3. 登录 API 返回 `must_change_password` 字段
4. 前端 Auth Store 存储 `mustChangePassword` 状态
5. 路由守卫：`mustChangePassword=true` 时强制跳转修改密码页面
6. 新增 `POST /api/auth/change-password` 端点，修改成功后清除标志
7. 前端新增 `ChangePasswordView.vue` 页面

**涉及文件**：
- 后端：`configforge/models/user.py`、`configforge/services/user_store.py`、`configforge/api/auth.py`
- 前端：`configforge-web/src/stores/auth.ts`、`configforge-web/src/router/index.ts`、`configforge-web/src/views/ChangePasswordView.vue`（新建）

**验证标准**：
- [ ] 全新部署后首次登录 admin/admin123，强制跳转修改密码页面
- [ ] 修改密码后正常使用，不再提示
- [ ] 已有用户登录不受影响

---

### T-5A-02 Fernet 密钥丢失检测

**关联缺陷**：D-03
**优先级**：P0
**前置依赖**：T-5A-06（需先引入 `CONFIGFORGE_ENV` 环境变量）

**问题**：未设置 `CONFIGFORGE_ENCRYPTION_KEY` 时自动生成 `.fernet_key` 文件，Docker 容器重启后文件丢失，所有加密凭证不可恢复。

**方案**：
1. `configforge/utils/crypto.py` 启动时检测：
   - 若 `CONFIGFORGE_ENCRYPTION_KEY` 未设置 且 `.fernet_key` 不存在 → 打印 WARNING 并创建
   - 若 `CONFIGFORGE_ENCRYPTION_KEY` 未设置 且 `.fernet_key` 存在 → 正常加载
   - 若 `CONFIGFORGE_ENCRYPTION_KEY` 已设置 → 始终使用环境变量（忽略文件）
2. `server.py` 启动时检查生产模式（`CONFIGFORGE_ENV=production`，由 T-5A-06 引入）：
   - 若 `CONFIGFORGE_ENCRYPTION_KEY` 未设置 → 拒绝启动，提示设置环境变量
3. `.fernet_key` 文件创建时设置 `chmod 600` 权限
4. Dockerfile 添加 `CONFIGFORGE_ENV=production` 默认值

**涉及文件**：
- `configforge/utils/crypto.py`、`configforge/server.py`、`Dockerfile`、`.env.example`

**验证标准**：
- [ ] 生产模式下未设置 `CONFIGFORGE_ENCRYPTION_KEY` 时拒绝启动
- [ ] 开发模式下自动生成 `.fernet_key`，文件权限 600
- [ ] 设置环境变量后正常启动

---

### T-5A-03 PyJWT 声明为必需依赖

**关联缺陷**：D-06
**优先级**：P0

**问题**：`jwt.py` 在无 PyJWT 时手写 HMAC-SHA256 JWT 实现，且 `pyproject.toml` 未声明 PyJWT 依赖。

**方案**：
1. `pyproject.toml` 的 `dependencies` 添加 `PyJWT>=2.8.0`
2. `configforge/middleware/jwt.py` 移除手写回退实现，仅保留 PyJWT 实现
3. 移除 `try/except ImportError` 分支

**涉及文件**：
- `pyproject.toml`、`configforge/middleware/jwt.py`

**验证标准**：
- [ ] `uv pip install` 后 PyJWT 已安装
- [ ] JWT 签发和验证功能正常
- [ ] 无手写 JWT 代码

---

### T-5A-04 细粒度 RBAC — 后端

**关联缺陷**：D-04
**关联优化**：O-04
**优先级**：P0
**架构评审检查点**：是 — 涉及认证依赖注入体系变更

**问题**：JWT 认证有 admin/editor/viewer 三种角色，但大部分端点未实现角色权限检查。

**当前认证机制**（代码库事实）：
- `configforge/middleware/auth.py` 的 `AuthMiddleware`（`BaseHTTPMiddleware` 子类）仅做令牌验证，验证通过后直接 `return await call_next(request)`，**不将用户信息写入 `request.state`**
- `configforge/api/auth.py` 的 `get_current_user` 是 `@router.get("/me")` 路由处理器，**不是** `Depends()` 依赖函数
- 需要用户信息的路由通过 `_get_current_user_from_request(request)` 从 `Authorization` 头重新解析令牌

**方案**：
1. `configforge/middleware/auth.py` 新增 FastAPI 依赖注入函数：
   ```python
   from fastapi import Request, HTTPException, Depends

   async def get_current_user_dep(request: Request) -> User:
       """FastAPI 依赖：从请求中提取已认证用户"""
       user = _get_current_user_from_request(request)
       if user is None:
           raise HTTPException(401, detail="未认证")
       return user

   def require_role(*roles: str):
       """角色权限依赖工厂"""
       async def dependency(user: User = Depends(get_current_user_dep)):
           if user.role not in roles:
               raise HTTPException(403, detail="权限不足")
               return user
       return dependency
   ```
   > 注：`_get_current_user_from_request` 已存在于 `auth.py:35`，需提取到 `middleware/auth.py` 或公共模块供依赖函数调用

2. 按端点配置角色要求（在路由参数中添加 `Depends(require_role(...))`）：

| API 模块 | 端点 | 所需角色 |
|----------|------|----------|
| configs | POST/PUT/DELETE | editor, admin |
| configs | GET | viewer, editor, admin |
| wizard | dry-run/execute | editor, admin |
| templates | POST/PUT/DELETE | admin |
| templates | GET | viewer, editor, admin |
| connections | POST/PUT/DELETE | admin |
| connections | GET | viewer, editor, admin |
| schedules | POST/PUT/DELETE | editor, admin |
| schedules | GET | viewer, editor, admin |
| notifications | POST/PUT/DELETE | editor, admin |
| notifications | GET | viewer, editor, admin |
| ai | settings GET/PUT | admin |
| ai | suggest/orchestrate | editor, admin |
| auth | register | admin |
| audit-log | GET | admin |

3. JWT 未启用时跳过角色检查（开发模式）：`get_current_user_dep` 在无 JWT_SECRET 时返回默认 admin 用户

**涉及文件**：
- `configforge/middleware/auth.py`（新增依赖函数）、`configforge/api/auth.py`（提取 `_get_current_user_from_request`）、所有 `configforge/api/*.py`（添加 `Depends`）

**验证标准**：
- [ ] viewer 用户调用 POST /api/configs 返回 403
- [ ] editor 用户调用 DELETE /api/templates/{id} 返回 403
- [ ] admin 用户所有操作正常
- [ ] JWT 未启用时所有操作不受限

---

### T-5A-05 细粒度 RBAC — 前端

**关联缺陷**：D-04
**关联优化**：O-04
**优先级**：P0

**问题**：前端未根据用户角色隐藏/禁用无权限的操作按钮。

**方案**：
1. Auth Store 添加 `canEdit` 和 `canAdmin` computed：
   ```typescript
   const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'editor')
   const canAdmin = computed(() => user.value?.role === 'admin')
   ```
2. 按页面隐藏无权限的 UI 元素：

| 页面 | 元素 | 显示条件 |
|------|------|----------|
| HomeView | "新建配置"按钮 | canEdit |
| HomeView | "执行"按钮 | canEdit |
| HomeView | "更多操作"→删除 | canEdit |
| TemplateMarketView | "删除"按钮 | canAdmin（已实现） |
| SchedulesPage | "新建定时任务"按钮 | canEdit |
| SettingsPage | AI 设置标签页 | canAdmin |
| SettingsPage | 数据库连接管理 | canAdmin |
| AppNavBar | "注册新用户" | canAdmin（已实现） |

3. API 拦截器处理 403 错误，显示"权限不足"提示

**涉及文件**：
- `configforge-web/src/stores/auth.ts`、`configforge-web/src/views/HomeView.vue`、`configforge-web/src/views/SchedulesPage.vue`、`configforge-web/src/views/SettingsPage.vue`、`configforge-web/src/composables/useApi.ts`

**验证标准**：
- [ ] viewer 用户看不到"新建配置"按钮
- [ ] editor 用户看不到 AI 设置标签页
- [ ] 403 错误显示"权限不足"提示

---

### T-5A-06 安全默认值与环境区分

**关联缺陷**：D-02, D-03
**关联优化**：O-05
**优先级**：P0
**前置说明**：当前代码库中不存在 `CONFIGFORGE_ENV` 环境变量，`server.py` 中没有任何环境区分逻辑。本任务需首先引入该机制。

**问题**：多项安全配置默认值不安全，且无环境区分机制。

**方案**：
1. **引入 `CONFIGFORGE_ENV` 环境变量（前置步骤）**：
   - 新建 `configforge/utils/env.py`，提供 `is_production()` / `is_development()` 辅助函数
   - `CONFIGFORGE_ENV` 默认值为 `development`，可选值：`development` / `production`
   - 统一文档术语为 `CONFIGFORGE_ENV`（修正 Recommendations 文档 O-05 中的 `NODE_ENV` 引用）
2. `server.py` 启动时检查：
   - `CONFIGFORGE_ENV=production` 时，`CONFIGFORGE_JWT_SECRET` 必须设置且长度 ≥ 32
   - `CONFIGFORGE_ENV=production` 时，`CONFIGFORGE_ENCRYPTION_KEY` 必须设置（供 T-5A-02 使用）
   - `CONFIGFORGE_ENV=production` 时，`CORS_ORIGINS` 不允许包含 `*`
3. `.env.example` 更新，添加 `CONFIGFORGE_ENV` 说明
4. Dockerfile 设置 `ENV CONFIGFORGE_ENV=production`
5. `docker-compose.yml` 添加 `CONFIGFORGE_ENV` 环境变量示例

**涉及文件**：
- `configforge/utils/env.py`（新建）、`configforge/server.py`、`.env.example`、`Dockerfile`、`docker-compose.yml`

**验证标准**：
- [ ] `CONFIGFORGE_ENV` 环境变量可读取，默认 `development`
- [ ] 生产模式下未设置 JWT_SECRET 拒绝启动
- [ ] 生产模式下未设置 `CONFIGFORGE_ENCRYPTION_KEY` 拒绝启动
- [ ] 生产模式下 CORS 不允许 `*`
- [ ] 开发模式行为不变

---

### T-5A-07 版本号统一

**关联缺陷**：D-09
**优先级**：P0

**问题**：`pyproject.toml`（v0.8.0）、`package.json`（v0.7.0）、README（v0.5.0）三处版本号不同步。

**方案**：
1. 统一版本号为 `v0.8.1`
2. 更新 `pyproject.toml`、`configforge-web/package.json`、`README.md`
3. CI 添加版本号一致性检查 job：
   ```yaml
   - name: Check version consistency
     run: |
       BACKEND=$(grep '^version' pyproject.toml | awk -F'"' '{print $2}')
       FRONTEND=$(grep '"version"' configforge-web/package.json | awk -F'"' '{print $4}')
       if [ "$BACKEND" != "$FRONTEND" ]; then
         echo "Version mismatch: backend=$BACKEND frontend=$FRONTEND"
         exit 1
       fi
   ```

**涉及文件**：
- `pyproject.toml`、`configforge-web/package.json`、`README.md`、`.github/workflows/ci.yml`

**验证标准**：
- [ ] 三处版本号一致
- [ ] CI 版本号检查通过

---

### T-5A-08 SSRF 防护完善

**关联缺陷**：D-05
**优先级**：P1

**问题**：`validate_url()` 阻止内网 IP，但对域名解析后的内网 IP 无法拦截（TOCTOU）。

**方案**：
1. `configforge/utils/security.py` 的 `validate_url()` 改为解析后验证：
   ```python
   import socket

   def validate_url(url: str) -> bool:
       # ... 现有检查 ...
       hostname = parsed.hostname
       try:
           # 获取所有解析 IP
           ips = socket.getaddrinfo(hostname, None)
           for ip in ips:
               ip_addr = ip[4][0]
               if is_private_ip(ip_addr):
                   raise ValueError(f"域名 {hostname} 解析到内网 IP {ip_addr}")
       except socket.gaierror:
           raise ValueError(f"无法解析域名 {hostname}")
       return True
   ```
2. API Reader 实际请求时锁定解析 IP，防止 DNS rebinding

**涉及文件**：
- `configforge/utils/security.py`、`configforge/services/api_reader.py`

**验证标准**：
- [ ] 域名指向内网 IP 时被拦截
- [ ] 正常外部域名可通过验证
- [ ] 现有 SSRF 测试通过

---

### T-5A-09 审计日志完善

**关联优化**：O-04
**优先级**：P1

**问题**：审计日志仅记录部分安全事件，RBAC 拒绝操作未记录。

**方案**：
1. `require_role` 依赖在拒绝时记录审计日志：
   ```python
   audit_logger.log(
       action="permission_denied",
       user=user.username,
       resource=f"{request.method} {request.url.path}",
       detail=f"需要角色 {roles}，当前角色 {user.role}"
   )
   ```
2. 所有写操作（POST/PUT/DELETE）记录审计日志
3. 审计日志 API 支持按用户、操作类型、时间范围筛选

**涉及文件**：
- `configforge/middleware/auth.py`、`configforge/services/audit_logger.py`、`configforge/server.py`（审计日志端点）

**验证标准**：
- [ ] RBAC 拒绝操作记录在审计日志中
- [ ] 所有写操作有审计记录
- [ ] 审计日志 API 支持筛选

---

### T-5A-10 HTTPS 部署文档与配置示例

**关联缺陷**：D-12
**优先级**：P1

**问题**：当前 nginx 仅监听 80 端口，无 HTTPS/TLS 配置，生产环境传输未加密。此为部署基础设施层面问题，本任务提供文档和配置示例，委派给部署团队实施。

**方案**：
1. 新建 `docs/DEPLOYMENT.md` 部署指南，包含：
   - 生产环境部署前置检查清单（`CONFIGFORGE_ENV`、`CONFIGFORGE_JWT_SECRET`、`CONFIGFORGE_ENCRYPTION_KEY`、SSL 证书）
   - nginx HTTPS 反向代理完整配置示例（含 HSTS、证书续期、HTTP→HTTPS 跳转）
   - docker-compose SSL 卷挂载示例
2. 提供 `deploy/nginx.conf.example` 配置示例
3. `docker-compose.yml` 添加 SSL 卷挂载示例（注释形式）
4. 文档说明 Let's Encrypt 免费证书申请流程（certbot）

**涉及文件**：
- `docs/DEPLOYMENT.md`（新建）、`deploy/nginx.conf.example`（新建）、`docker-compose.yml`、`README.md`

**验证标准**：
- [ ] `docs/DEPLOYMENT.md` 存在且内容完整
- [ ] nginx 配置示例可通过 `nginx -t` 语法检查
- [ ] 文档包含证书申请、续期、回滚说明
- [ ] docker-compose 包含 SSL 卷挂载示例

---

## Phase 5B：性能与体验（v0.9.0）

> **目标**：提升系统性能和用户体验，解决大文件处理和配置列表性能问题。
> **验收标准**：100MB 文件预览 < 3 秒，配置列表 500 条加载 < 1 秒。

---

### T-5B-01 大文件流式预览

**关联缺陷**：D-10
**关联优化**：O-06
**优先级**：P1

**问题**：`preview_file()` 和 `infer_input()` 将整个文件读入内存，大文件可能导致 OOM。

**方案**：
1. `configforge/services/excel_reader.py`：
   - `read_excel_info()` 使用 `openpyxl.load_workbook(read_only=True)`
   - 仅读取前 100 行作为 sample_rows
   - 列名从第一行获取
2. `configforge/services/csv_reader.py`：
   - 使用 `pandas.read_csv(chunksize=100)` 流式读取
   - 仅保留前 100 行
3. `configforge/services/parquet_reader.py`：
   - 使用 `pyarrow.parquet.ParquetFile.iter_batches(batch_size=100)`
4. `configforge/api/preview.py` 添加文件大小警告（> 10MB 时提示）

**涉及文件**：
- `configforge/services/excel_reader.py`、`configforge/services/csv_reader.py`、`configforge/services/parquet_reader.py`、`configforge/api/preview.py`

**验证标准**：
- [ ] 50MB Excel 文件预览 < 3 秒
- [ ] 50MB CSV 文件预览 < 3 秒
- [ ] 内存占用 < 200MB
- [ ] 预览结果与全量读取一致（前 100 行）

---

### T-5B-02 配置列表索引优化

**关联缺陷**：D-11
**关联优化**：O-07
**优先级**：P1
**架构评审检查点**：是 — 涉及 `index.json` schema 变更和数据迁移

**问题**：`list_configs()` 每次加载整个 `index.json` 到内存排序过滤；`ConnectionStore.count_references()` 对每个配置单独读取 state.json。

**方案**：
1. `configs/index.json` 结构升级（schema_version=2）：
   ```json
   {
     "schema_version": 2,
     "configs": [
       {
         "id": "xxx",
         "name": "配置名称",
         "description": "描述",
         "version": "1.0",
         "updated_at": "2026-06-20T10:00:00",
         "created_at": "2026-06-19T10:00:00",
         "tags": ["销售", "月报"],
         "input_types": ["excel"],
         "output_type": "csv"
       }
     ]
   }
   ```
2. `list_configs()` 支持服务端分页、排序、搜索：
   - `GET /api/configs?page=1&page_size=10&sort=updated_at&order=desc&search=keyword`
   - 仅返回索引字段，不读取 state.json
3. `ConnectionStore.count_references()` 改为遍历 `index.json` 的 `input_types` 字段
4. `migration.py` 添加 v1→v2 迁移（含回滚方案）：
   - **迁移前**：备份 `index.json` 到 `index.json.bak`（带时间戳）
   - **dry-run 模式**：迁移脚本支持 `--dry-run` 参数，仅输出迁移计划不实际写入
   - **迁移过程**：遍历所有 state.json 提取字段到 index.json，写入失败时跳过并记录
   - **失败恢复**：检测到迁移异常时自动从 `index.json.bak` 恢复
   - **迁移日志**：记录迁移开始时间、处理配置数、成功/失败数、结束时间

**涉及文件**：
- `configforge/api/configs.py`、`configforge/utils/migration.py`、`configforge/services/connection_store.py`

**验证标准**：
- [ ] 500 条配置列表加载 < 1 秒
- [ ] 服务端分页正常
- [ ] 搜索功能正常
- [ ] v1 数据自动迁移到 v2
- [ ] `--dry-run` 模式输出迁移计划不写入
- [ ] 迁移失败时从备份恢复 `index.json`

---

### T-5B-03 缓存策略优化

**关联优化**：O-08
**优先级**：P1

**问题**：缓存 TTL 过短（5 秒），高频读取场景磁盘 I/O 开销大。

**方案**：
1. `configforge/utils/cache.py` 的 `TTLCache` 默认 TTL 从 5 秒延长到 30 秒
2. 连接列表、模板列表使用 30 秒 TTL
3. 配置列表使用 10 秒 TTL（变更频率较高）
4. AI 诊断结果 LRU 缓存从 100 条增加到 200 条
5. 添加缓存失效方法：`cache.invalidate(key)` 在数据变更时主动失效

**涉及文件**：
- `configforge/utils/cache.py`、`configforge/services/connection_store.py`、`configforge/services/template_store.py`、`configforge/services/ai/auto_diagnose.py`

**验证标准**：
- [ ] 连续读取连接列表 10 次，磁盘 I/O 仅 1 次
- [ ] 修改连接后缓存立即失效
- [ ] AI 诊断缓存命中率提升

---

### T-5B-04 配置向导手风琴模式

**关联优化**：O-09
**优先级**：P1

**问题**：5 步全部展开，页面很长，用户需要大量滚动。
**注意事项**：当前 `ConfigWizardView.vue` 使用固定 170px 滚动步长对齐步骤切换。手风琴模式会动态改变各步骤卡片高度，可能破坏现有滚动对齐逻辑，需同步适配。

**方案**：
1. `ConfigWizardView.vue` 添加 `expandedStep` ref，默认为当前步骤
2. `WizardStepCard.vue` 添加 `collapsed` prop：
   - 展开时显示完整内容
   - 折叠时显示摘要（场景名称、输入源数量、处理步骤数量、输出类型）
3. 点击步骤标题切换展开/折叠
4. 当前步骤自动展开，不可折叠
5. 已完成步骤折叠显示摘要，点击可展开编辑
6. **适配滚动对齐逻辑**：
   - 移除固定 170px 滚动步长
   - 改为动态计算目标步骤卡片的 `offsetTop`
   - 使用 `scrollIntoView({ behavior: 'smooth', block: 'start' })` 替代手动滚动
   - 步骤切换时等待 DOM 更新后再滚动（`nextTick`）

**涉及文件**：
- `configforge-web/src/views/ConfigWizardView.vue`、`configforge-web/src/components/wizard/WizardStepCard.vue`

**验证标准**：
- [ ] 默认只展开当前步骤
- [ ] 点击已完成步骤标题可展开编辑
- [ ] 折叠状态显示摘要信息
- [ ] 移动端体验改善
- [ ] 步骤切换时滚动对齐正常（无跳动、无错位）

---

### T-5B-05 实时执行进度（SSE）

**关联优化**：O-10
**优先级**：P1

**问题**：Pipeline 执行时无进度反馈，用户只能等待。

**方案**：
1. 后端 `configforge/api/wizard.py` 新增 `GET /api/wizard/execute/stream` 端点：
   - 使用 SSE（Server-Sent Events）推送进度
   - 事件类型：`input_start`、`input_done`、`processor_start`、`processor_done`、`output_start`、`output_done`、`complete`、`error`
2. `configforge/services/execution_service.py` 添加进度回调：
   ```python
   async def execute_with_progress(state, on_progress):
       on_progress("input_start", {"table": "users"})
       # ... 执行输入阶段 ...
       on_progress("input_done", {"rows": 1000})
       # ...
   ```
3. 前端 `ExportActions.vue` 添加进度条 UI：
   - 显示当前阶段（输入→处理→输出）
   - 显示已处理行数
   - 完成后自动切换到结果预览

**涉及文件**：
- `configforge/api/wizard.py`、`configforge/services/execution_service.py`、`configforge-web/src/components/step4/ExportActions.vue`

**验证标准**：
- [ ] 执行时显示实时进度
- [ ] 各阶段切换有视觉反馈
- [ ] 错误时显示错误阶段

---

### T-5B-06 配置版本对比可视化

**关联优化**：O-11
**优先级**：P2

**问题**：版本历史仅显示版本号和时间，无法直观看到变更内容。

**方案**：
1. 后端 `GET /api/configs/{id}/versions/diff?v1=1&v2=2` 返回结构化 diff：
   ```json
   {
     "added": [{"path": "processors[1]", "value": {...}}],
     "removed": [{"path": "inputs[0].config.sheet", "value": "Sheet1"}],
     "modified": [{"path": "scene.name", "old": "旧名称", "new": "新名称"}]
   }
   ```
2. 前端 `ConfigVersionPanel.vue` 添加 diff 视图：
   - 树形结构展示配置
   - 新增项绿色高亮，删除项红色删除线，修改项黄色高亮
   - 支持展开/折叠子节点

**涉及文件**：
- `configforge/api/configs.py`、`configforge-web/src/components/config/ConfigVersionPanel.vue`

**验证标准**：
- [ ] 选择两个版本可查看 diff
- [ ] 新增/删除/修改项有不同颜色标识
- [ ] 树形结构可展开折叠

---

### T-5B-07 模板市场增强

**关联优化**：O-12
**优先级**：P2

**问题**：模板市场功能较基础，缺少评分、导入导出等功能。

**方案**：
1. 模板导入/导出：
   - `GET /api/templates/{id}/export` 导出模板 JSON
   - `POST /api/templates/import` 导入模板 JSON
   - 前端添加"导出"和"导入"按钮
2. 模板使用排行榜：
   - 前端模板市场添加"热门模板"排序选项
   - 按 `usageCount` 降序排列
3. 模板搜索增强：
   - 支持按标签搜索（当前仅搜名称和描述）
   - 搜索高亮匹配关键词

**涉及文件**：
- `configforge/api/templates.py`、`configforge-web/src/views/TemplateMarketView.vue`

**验证标准**：
- [ ] 可导出模板为 JSON 文件
- [ ] 可导入模板 JSON 文件
- [ ] 热门模板排序正常
- [ ] 标签搜索正常

---

### T-5B-08 前端错误处理统一

**关联优化**：O-03
**优先级**：P1
**工作量估算**：2-3 天（跨文件重构）
**Breaking Change**：是 — `request()` 行为变更，需渐进式迁移

**问题**：部分组件直接使用 `fetch()` 绕过 composable 层；`useApi.ts` 的 `request()` 返回 null 而非抛出异常。

**方案**（渐进式迁移）：
1. `SchedulesPage.vue` 和 `auth.ts` 中的直接 `fetch()` 调用改为使用 composable
2. `useApi.ts` **新增** `requestOrThrow()` 方法，抛出 `ApiError` 异常
3. **保留** 旧 `request()` 方法，标记 `@deprecated`，内部改为调用 `requestOrThrow()` 并 catch 返回 null
4. 逐个 composable 迁移到 `requestOrThrow()`：
   - 每迁移一个 composable，运行对应测试确认无回归
   - 迁移顺序：`useConfigApi` → `useConnectionApi` → `useTemplateApi` → `useAiApi` → `useNotificationApi` → `useScheduleApi` → `useExecutionApi`
5. 所有 composable 迁移完成后，移除 `request()` 方法和 `@deprecated` 标记
6. 添加全局错误处理 composable `useApiError()`：
   - 统一显示错误提示（NMessage 或 NNotification）
   - 401 自动跳转登录
   - 403 显示"权限不足"
   - 500 显示"服务器错误"

**涉及文件**：
- `configforge-web/src/composables/useApi.ts`、`configforge-web/src/views/SchedulesPage.vue`、`configforge-web/src/stores/auth.ts`、所有调用 `request()` 的 composable

**验证标准**：
- [ ] 无直接 `fetch()` 调用
- [ ] 所有 API 错误有统一提示
- [ ] 401/403/500 有不同处理
- [ ] 迁移过程中无回归（每个 composable 迁移后测试通过）
- [ ] 最终 `request()` 方法被移除

---

### T-5B-09 移动端响应式优化

**优先级**：P2

**问题**：部分页面在移动端体验不佳。

**方案**：
1. 配置向导：移动端步骤导航改为底部固定栏
2. 模板市场：移动端卡片改为单列布局
3. 执行历史：移动端表格改为卡片列表
4. 设置页面：移动端标签页改为手风琴
5. 全局：移动端导航栏改为汉堡菜单

**涉及文件**：
- `configforge-web/src/views/ConfigWizardView.vue`、`configforge-web/src/views/TemplateMarketView.vue`、`configforge-web/src/views/ExecutionHistoryView.vue`、`configforge-web/src/views/SettingsPage.vue`、`configforge-web/src/components/common/AppNavBar.vue`

**验证标准**：
- [ ] 375px 宽度下所有页面可用
- [ ] 无横向滚动
- [ ] 触摸操作友好（按钮 ≥ 44px）

---

### T-5B-10 暗色模式完善

**优先级**：P2

**问题**：部分组件暗色模式样式不完整。

**方案**：
1. 全局 CSS 变量审查，确保所有颜色使用 CSS 变量
2. CodeMirror 暗色主题适配
3. Naive UI 暗色主题配置完善
4. 截图对比所有页面的亮色/暗色模式

**涉及文件**：
- `configforge-web/src/assets/`、`configforge-web/src/components/common/CodeEditor.vue`、所有组件的 `<style>`

**验证标准**：
- [ ] 所有页面暗色模式无白色背景
- [ ] 文字对比度 ≥ 4.5:1（WCAG AA）
- [ ] CodeEditor 暗色主题正常

---

## Phase 5C：代码质量（v0.9.5）

> **目标**：提升代码质量，补齐测试覆盖，消除技术债。
> **验收标准**：前端测试覆盖率 ≥ 60%，后端无测试模块覆盖 ≥ 80%，无 `as any`。

---

### T-5C-01 前端 Views 测试补齐

**关联缺陷**：D-07
**关联优化**：O-13
**优先级**：P1

**问题**：所有 8 个 views 无测试。

**方案**：
1. 为每个 view 编写测试：
   - `HomeView.test.ts`：配置列表渲染、搜索、分页、操作菜单
   - `ConfigWizardView.test.ts`：5 步流程、步骤导航、校验
   - `TemplateMarketView.test.ts`：列表、筛选、删除、使用模板
   - `ExecutionHistoryView.test.ts`：列表、详情、下载
   - `SchedulesPage.test.ts`：列表、创建、编辑、删除
   - `SettingsPage.test.ts`：AI 设置、连接管理
   - `LoginView.test.ts`：登录、错误提示
   - `ChangePasswordView.test.ts`：修改密码
2. Mock 依赖：API composable、router、auth store

**涉及文件**：
- `configforge-web/tests/views/*.test.ts`（8 个新建）

**验证标准**：
- [ ] 8 个 views 都有测试
- [ ] 覆盖率 ≥ 60%
- [ ] CI 通过

---

### T-5C-02 后端无测试模块补齐

**关联缺陷**：D-07
**关联优化**：O-13
**优先级**：P1

**问题**：模板 API/Store、调度 API、执行历史 API、YAML 构建器、通知子系统无测试。

**方案**：
1. `test_templates_api.py`（已有，补充）：更新、兼容性检查
2. `test_templates_store.py`（新建）：模板 CRUD、内置模板加载
3. `test_schedules_api.py`（新建）：CRUD、启停、cron 验证
4. `test_executions_api.py`（新建）：列表、详情、下载、删除
5. `test_yaml_builder.py`（新建）：各输入/输出组合的 YAML 生成
6. `test_notifier_email.py`（新建）：SMTP 发送、模板渲染
7. `test_notifier_webhook.py`（新建）：各平台格式、重试
8. `test_notifier_dispatcher.py`（新建）：异步分发、错误处理
9. `test_ai_backends.py`（补充）：OpenAI/Anthropic mock 测试
10. `test_parquet_reader.py`（新建）：Parquet 读取

**涉及文件**：
- `configforge/tests/test_*.py`（10 个新建/补充）

**验证标准**：
- [ ] 10 个测试文件创建/补充
- [ ] 后端覆盖率 ≥ 80%
- [ ] CI 通过

---

### T-5C-03 E2E 测试集成 CI

**关联缺陷**：D-08
**关联优化**：O-13
**优先级**：P1

**问题**：Playwright E2E 测试存在但未在 GitHub Actions 中运行。

**方案**：
1. `.github/workflows/ci.yml` 添加 `e2e` job：
   ```yaml
   e2e:
     runs-on: ubuntu-latest
     needs: [backend, frontend]
     steps:
       - uses: actions/checkout@v4
       - name: Setup Node
         uses: actions/setup-node@v4
       - name: Install frontend deps
         run: cd configforge-web && npm ci
       - name: Install Playwright
         run: cd configforge-web && npx playwright install --with-deps
       - name: Build and start
         run: |
           cd configforge-web && npm run build &
           cd .. && python -m uvicorn configforge.server:app --port 8000 &
           sleep 5
       - name: Run E2E tests
         run: cd configforge-web && npx playwright test
   ```
2. 添加 E2E 测试用例：
   - 登录流程
   - 完整向导流程（上传文件→SQL→输出→执行）
   - 模板使用流程

**涉及文件**：
- `.github/workflows/ci.yml`、`configforge-web/e2e/*.spec.ts`

**验证标准**：
- [ ] CI 中 E2E job 运行
- [ ] E2E 测试通过
- [ ] PR 时自动运行

---

### T-5C-04 代码覆盖率报告

**关联优化**：O-13
**优先级**：P2

**问题**：CI 未生成覆盖率报告，无法量化测试质量。

**方案**：
1. 后端：`pytest --cov=configforge --cov-report=xml --cov-report=html`
2. 前端：`vitest run --coverage`（需安装 `@vitest/coverage-v8`）
3. CI 上传覆盖率到 Codecov 或 GitHub Actions Artifact
4. PR 中添加覆盖率变化评论

**涉及文件**：
- `pyproject.toml`（添加 pytest-cov）、`configforge-web/package.json`（添加 coverage 依赖）、`.github/workflows/ci.yml`

**验证标准**：
- [ ] CI 生成覆盖率报告
- [ ] 覆盖率数据可视化
- [ ] PR 显示覆盖率变化

---

### T-5C-05 类型安全提升与 ESLint 规则强化

**关联优化**：O-14
**优先级**：P2
**状态说明**（2026-06-21 核查）：
- `configforge-web/src/` 目录下 `as any` 已清零（0 处）
- `configforge-web/tests/` 目录下仍有 4 处 `as any`：
  - `tests/stores/wizard.test.ts:244`
  - `tests/components/YamlPreview.test.ts:77`
  - `tests/components/CheckpointSection.test.ts:86, 101`
- 原 Plan 声称的"21 处 `as any`"基于过时快照，已不适用

**问题**：`src/` 下 `as any` 虽已清零，但缺乏 lint 规则防止回潮；`tests/` 下仍有 4 处需清理。

**方案**（预防性维护 + 清理残留）：
1. 清理 `tests/` 下 4 处 `as any`：
   - `wizard.test.ts:244`：为 `updateProcessor` 参数构造完整类型对象
   - `YamlPreview.test.ts:77`：使用 `ComponentPublicInstance` 类型或 `defineExpose` 暴露的方法类型
   - `CheckpointSection.test.ts:86, 101`：使用 `emitted()` 的泛型重载
2. 启用 `@typescript-eslint/no-explicit-any` lint 规则（error 级别）防止回潮
3. 启用 `@typescript-eslint/recommended-type-checked`
4. 启用 `vue/recommended`
5. 添加自定义规则：`no-console: error`、`no-debugger: error`、`prefer-const: error`、`no-unused-vars: error`
6. 修复现有 lint 警告

**涉及文件**：
- `configforge-web/tests/stores/wizard.test.ts`、`configforge-web/tests/components/YamlPreview.test.ts`、`configforge-web/tests/components/CheckpointSection.test.ts`、`configforge-web/eslint.config.js`、所有 `.vue`/`.ts` 文件

**验证标准**：
- [ ] `src/` 和 `tests/` 下 0 处 `as any`
- [ ] TypeScript strict 模式通过
- [ ] ESLint 无 no-explicit-any 警告
- [ ] CI lint job 通过

---

### T-5C-06 前端大组件拆分

**关联优化**：O-02
**优先级**：P2

**问题**：以下组件行数较大，需评估是否拆分。

**实际行数**（2026-06-21 核查）：

| 文件 | 实际行数 | 原 Plan 声称 | 差异 |
|------|---------|-------------|------|
| HomeView.vue | 765 | 963 | -198 |
| OutputConfigTab.vue | 511 | 787 | -276 |
| InputSourceCard.vue | 551 | 645 | -94 |

> 注：实际行数低于原计划声称的行数，工作量相应调低。OutputConfigTab.vue（511 行）接近 400 行阈值，优先拆分。

**方案**：
1. HomeView 拆分：
   - `ConfigListSection.vue`（列表区域）
   - `ConfigToolbar.vue`（搜索 + 批量管理）
   - `ConfigPagination.vue`（分页控件）
2. OutputConfigTab 拆分：
   - 已有 FileOutputForm/DatabaseOutputForm，提取 ColumnMappingEditor 为独立组件
   - 提取 OutputTypeSelector 为独立组件
3. InputSourceCard 拆分：
   - 已有 FileInputForm/DatabaseForm/ApiForm，提取 InputSourceHeader 为独立组件
   - 提取 ColumnPreviewPanel 为独立组件

**涉及文件**：
- `configforge-web/src/views/HomeView.vue`、`configforge-web/src/components/step3/OutputConfigTab.vue`、`configforge-web/src/components/step2/InputSourceCard.vue`、新建子组件

**验证标准**：
- [ ] 拆分后每个组件 < 400 行
- [ ] 功能不变
- [ ] 测试通过

---

### T-5C-07 `api_infer_api_input` 使用 Pydantic 模型

**关联缺陷**：D-15
**优先级**：P2

**问题**：`api/wizard.py:70` 的 `api_infer_api_input(input_name: str, req: dict)` 未使用 Pydantic 模型。

**方案**：
1. `configforge/models/wizard.py` 新增 `ApiInferRequest` 模型：
   ```python
   class ApiInferRequest(BaseModel):
       model_config = ConfigDict(extra="forbid")
       url: str
       method: str = "GET"
       headers: dict[str, str] = {}
       params: dict[str, str] = {}
       body: dict | None = None
       data_path: str = ""
       pagination: str = "none"
       page_size: int = 20
       max_pages: int = 10
   ```
2. `api/wizard.py` 修改端点签名使用 `ApiInferRequest`

**涉及文件**：
- `configforge/models/wizard.py`、`configforge/api/wizard.py`

**验证标准**：
- [ ] 端点使用 Pydantic 模型
- [ ] 请求体验证正常
- [ ] 前端调用不受影响

---

### T-5C-08 前端 Composable 测试补齐

**关联缺陷**：D-07
**关联优化**：O-13
**优先级**：P2

**问题**：8 个 composable 无测试。

**方案**：
1. `useConnectionApi.test.ts`：连接 CRUD、测试连接
2. `useNotificationApi.test.ts`：通知配置 CRUD、测试
3. `useTemplateApi.test.ts`：模板 CRUD、实例化
4. `useAiApi.test.ts`：AI 建议、编排、设置
5. `useAiStatus.test.ts`：AI 状态检测
6. `useBreakpoint.test.ts`：断点检测
7. `useTheme.test.ts`：主题切换
8. `useConnections.test.ts`：连接列表加载

**涉及文件**：
- `configforge-web/tests/composables/*.test.ts`（8 个新建）

**验证标准**：
- [ ] 8 个 composable 都有测试
- [ ] 覆盖率 ≥ 80%
- [ ] CI 通过

---

### T-5C-09 后端代码规范检查

**优先级**：P2

**问题**：后端无 lint 工具，代码风格依赖人工维护。

**方案**：
1. 安装 `ruff` 作为 Python linter 和 formatter
2. `pyproject.toml` 添加 ruff 配置：
   ```toml
   [tool.ruff]
   line-length = 120
   target-version = "py310"

   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4"]
   ```
3. CI 添加 ruff check job
4. 运行 `ruff format` 统一格式

**涉及文件**：
- `pyproject.toml`、`.github/workflows/ci.yml`

**验证标准**：
- [ ] ruff check 通过
- [ ] CI 集成 ruff
- [ ] 代码格式统一

---

### T-5C-10 前端 ESLint 规则强化（已合并到 T-5C-05）

**优先级**：P2
**状态**：✅ 已合并到 T-5C-05（类型安全提升与 ESLint 规则强化）

> 本任务内容（启用 `@typescript-eslint/recommended-type-checked`、`vue/recommended`、自定义规则等）已合并到 T-5C-05 中统一执行，避免重复工作。本任务编号保留以维持依赖图引用稳定性，不再单独执行。

---

### T-5C-11 API 文档完善

**优先级**：P2

**问题**：部分 API 端点缺少 OpenAPI 文档。

**方案**：
1. 审查所有 API 端点的 `summary`、`description`、`response_model`
2. 添加请求/响应示例
3. 添加错误码说明
4. 前端集成 OpenAPI 类型生成（`openapi-typescript`）

**涉及文件**：
- 所有 `configforge/api/*.py`、`configforge-web/package.json`

**验证标准**：
- [ ] 所有端点有文档
- [ ] `/docs` 页面信息完整
- [ ] 前端有生成的 API 类型

---

## Phase 5D：功能增强（v1.0.0）

> **目标**：补齐功能短板，提升产品竞争力。
> **验收标准**：核心功能对标同类产品，用户满意度提升。

---

### T-5D-01 监控与可观测性

**关联优化**：O-15
**优先级**：P3

**方案**：
1. 后端添加 Prometheus metrics：
   - `configforge_http_requests_total`（请求计数）
   - `configforge_http_request_duration_seconds`（请求延迟）
   - `configforge_pipeline_executions_total`（Pipeline 执行计数）
   - `configforge_pipeline_duration_seconds`（Pipeline 执行耗时）
2. `GET /api/metrics` 端点暴露 metrics
3. 前端错误上报：集成 Sentry 或自建错误收集端点
4. 结构化日志：统一 JSON 格式，支持日志级别配置

**涉及文件**：
- `configforge/utils/metrics.py`（新建）、`configforge/server.py`、`configforge-web/src/utils/errorReport.ts`（新建）

**验证标准**：
- [ ] `/api/metrics` 返回 Prometheus 格式数据
- [ ] 前端错误自动上报
- [ ] 日志为 JSON 格式

---

### T-5D-02 数据备份与恢复

**关联缺陷**：D-13
**优先级**：P3

**方案**：
1. `configforge/utils/backup.py`（新建）：
   - `create_backup()`：打包 `data/` 和 `configs/` 到 zip
   - `restore_backup(zip_path)`：从 zip 恢复
2. API 端点：
   - `POST /api/backup`：触发备份，返回下载链接
   - `POST /api/restore`：上传 zip 恢复
3. 定时备份：APScheduler 每日备份到 `data/backups/`
4. 保留策略：保留最近 7 个备份

**涉及文件**：
- `configforge/utils/backup.py`（新建）、`configforge/api/backup.py`（新建）、`configforge/server.py`、`configforge/scheduler.py`

**验证标准**：
- [ ] 可手动触发备份
- [ ] 可从备份恢复
- [ ] 定时备份正常
- [ ] 旧备份自动清理

---

### T-5D-03 配置导入导出

**优先级**：P3

**方案**：
1. `GET /api/configs/{id}/export`：导出配置为 YAML/JSON 文件
2. `POST /api/configs/import`：导入 YAML/JSON 文件创建配置
3. 前端 HomeView 添加"导入配置"按钮
4. 配置列表操作菜单添加"导出"选项

**涉及文件**：
- `configforge/api/configs.py`、`configforge-web/src/views/HomeView.vue`、`configforge-web/src/components/config/ConfigActionsMenu.vue`

**验证标准**：
- [ ] 可导出配置为 YAML
- [ ] 可导入 YAML 创建配置
- [ ] 导入时校验格式

---

### T-5D-04 Pipeline 执行通知增强

**优先级**：P3

**方案**：
1. 通知内容增强：
   - 成功：包含输出文件名、行数、耗时
   - 失败：包含错误信息、诊断建议
   - 异常：包含异常类型、堆栈摘要
2. 通知模板自定义：
   - 用户可自定义通知模板（支持变量替换）
   - `{{config_name}}`、`{{status}}`、`{{duration}}`、`{{rows}}`、`{{error}}`
3. 通知频率控制：
   - 防止短时间内重复通知（如 5 分钟内同一配置只通知一次）

**涉及文件**：
- `configforge/services/notifier/formatters.py`、`configforge/services/notifier/dispatcher.py`、`configforge-web/src/components/step5/NotificationSettings.vue`

**验证标准**：
- [ ] 通知内容包含执行详情
- [ ] 可自定义通知模板
- [ ] 频率控制生效

---

### T-5D-05 AI 辅助增强

**优先级**：P3

**方案**：
1. AI 推荐 CheckRule：
   - `POST /api/ai/suggest-checkpoint`：根据数据特征推荐检查规则
   - 如：检测到 email 列 → 推荐 `regex` 检查；检测到数值列 → 推荐 `range` 检查
2. AI 列映射智能匹配：
   - `POST /api/ai/suggest-mapping`：根据源列和目标列名称智能匹配
   - 支持同义词、缩写、中英文对照
3. AI 配置优化建议：
   - 分析配置后给出优化建议（如"建议添加去重步骤"、"建议添加数据检查点"）

**涉及文件**：
- `configforge/api/ai.py`、`configforge/services/ai/orchestrator.py`、`configforge-web/src/composables/useAiApi.ts`

**验证标准**：
- [ ] AI 可推荐检查规则
- [ ] AI 可智能匹配列映射
- [ ] AI 可给出优化建议

---

### T-5D-06 国际化（i18n）— 基础设施 + 高频页面

**关联缺陷**：D-14
**优先级**：P3
**分期说明**：200+ 处硬编码中文的国际化是体力密集型工作，本任务仅完成框架搭建和 20% 高频页面翻译，剩余 80% 页面翻译拆分到 T-5E-06（v1.2.0）。

**翻译范围**（本任务覆盖）：
- `LoginView.vue`（登录页）
- `AppNavBar.vue`（导航栏）
- `HomeView.vue`（配置列表页）
- `SettingsPage.vue`（设置页）

**方案**：
1. 安装 `vue-i18n`
2. 搭建 i18n 基础设施：
   - `configforge-web/src/locales/zh-CN.json`（中文）
   - `configforge-web/src/locales/en-US.json`（英文）
   - 语言切换组件
   - Auth Store 持久化语言偏好
3. 提取上述 4 个高频页面的硬编码中文到语言文件
4. 后端 AI 提示词支持多语言（基础框架）
5. 用户设置中添加语言切换

**涉及文件**：
- `configforge-web/src/locales/`（新建）、`configforge-web/src/main.ts`、`LoginView.vue`、`AppNavBar.vue`、`HomeView.vue`、`SettingsPage.vue`、`configforge/services/ai/orchestrator.py`

**验证标准**：
- [ ] i18n 框架搭建完成，可切换中文/英文
- [ ] 4 个高频页面文案有对应翻译
- [ ] 语言偏好持久化
- [ ] 剩余页面文案仍显示中文（不报错）

> 剩余 80% 页面翻译见 T-5E-06

---

### T-5D-07 PWA 离线支持

**优先级**：P3

**方案**：
1. 安装 `vite-plugin-pwa`
2. 配置 Service Worker：
   - 缓存静态资源
   - 离线时显示缓存页面
3. 添加 `manifest.json`
4. 支持安装到桌面

**涉及文件**：
- `configforge-web/vite.config.ts`、`configforge-web/public/manifest.json`（新建）

**验证标准**：
- [ ] 可安装到桌面
- [ ] 离线时可访问缓存页面
- [ ] 在线时自动更新

---

## Phase 5E：架构演进（v1.2.0）

> **目标**：为长期发展奠定架构基础。
> **验收标准**：存储层支持 SQLite，可平滑迁移到 PostgreSQL。

---

### T-5E-01 存储层抽象

**关联缺陷**：D-01
**关联优化**：O-01
**优先级**：P4
**架构评审检查点**：是 — 涉及存储层架构决策，影响所有 Store 类

**方案**：
1. 定义存储层抽象接口：
   ```python
   # configforge/storage/base.py
   class ConfigStore(Protocol):
       def list_configs(self, page, page_size, search, sort) -> list[ConfigSummary]: ...
       def get_config(self, config_id) -> Config: ...
       def save_config(self, config) -> None: ...
       def delete_config(self, config_id) -> None: ...
   ```
2. 实现两个后端：
   - `JsonConfigStore`：当前 JSON 文件实现
   - `SqliteConfigStore`：SQLite 实现
3. 通过环境变量 `CONFIGFORGE_STORAGE_BACKEND=json|sqlite` 切换
4. 所有 Store 类（ConnectionStore、TemplateStore、UserStore 等）统一抽象

**涉及文件**：
- `configforge/storage/base.py`（新建）、`configforge/storage/json_backend.py`（新建）、`configforge/storage/sqlite_backend.py`（新建）、所有 Store 类

**验证标准**：
- [ ] JSON 和 SQLite 后端功能一致
- [ ] 环境变量切换正常
- [ ] 数据可从 JSON 迁移到 SQLite

---

### T-5E-02 SQLite 后端实现

**关联优化**：O-01
**优先级**：P4

**方案**：
1. SQLite 数据库 schema 设计：
   - `configs` 表：id, name, description, version, state_json, created_at, updated_at
   - `config_versions` 表：config_id, version, state_json, created_at
   - `connections` 表：id, name, type, config_json, created_at
   - `templates` 表：id, name, description, category, config_json, created_at
   - `users` 表：id, username, password_hash, role, must_change_password, created_at
   - `schedules` 表：id, config_id, cron, enabled, created_at
   - `notifications` 表：id, config_id, type, config_json, created_at
   - `executions` 表：id, config_id, status, result_json, created_at
   - `audit_log` 表：id, action, user, resource, detail, created_at
2. 使用 SQLAlchemy 2.0 ORM
3. WAL 模式支持并发读
4. 数据迁移脚本：JSON → SQLite

**涉及文件**：
- `configforge/storage/sqlite_backend.py`、`configforge/storage/models.py`（新建）、`configforge/utils/migrate_to_sqlite.py`（新建）

**验证标准**：
- [ ] SQLite 后端功能完整
- [ ] 并发读写正常
- [ ] JSON 数据可迁移

---

### T-5E-03 PostgreSQL 支持

**关联优化**：O-01
**优先级**：P4

**方案**：
1. 复用 SQLAlchemy ORM，添加 PostgreSQL 连接配置
2. 环境变量 `CONFIGFORGE_DATABASE_URL=postgresql://user:pass@host:5432/db`
3. docker-compose.yml 添加 PostgreSQL 服务选项
4. 数据迁移脚本：SQLite → PostgreSQL

**涉及文件**：
- `configforge/storage/sqlite_backend.py`（重构为通用 SQL 后端）、`docker-compose.yml`

**验证标准**：
- [ ] PostgreSQL 后端功能完整
- [ ] SQLite 数据可迁移到 PostgreSQL

---

### T-5E-04 多实例部署支持

**优先级**：P4

**方案**：
1. 移除文件锁依赖（`fcntl.flock`），改用数据库事务
2. APScheduler 使用 `JobStore` 持久化到数据库
3. 限流状态存储到数据库
4. 文件上传使用共享存储（如 MinIO/S3）

**涉及文件**：
- `configforge/scheduler.py`、`configforge/utils/rate_limit.py`、`configforge/services/file_storage.py`（新建）

**验证标准**：
- [ ] 多实例同时运行无冲突
- [ ] 定时任务不重复执行
- [ ] 限流跨实例生效

---

### T-5E-05 本地插件系统

**优先级**：P4
**范围说明**：仅包含本地插件接口和自动加载机制。插件市场（远程安装、版本管理、安全审核）范围过大，拆分到 v2.0.0。

**方案**：
1. 定义插件接口：
   ```python
   class InputPlugin(Protocol):
       name: str
       def read_info(self, source: str) -> FileInfo: ...
       def read_data(self, source: str) -> pd.DataFrame: ...

   class ProcessorPlugin(Protocol):
       name: str
       def process(self, dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]: ...

   class OutputPlugin(Protocol):
       name: str
       def write(self, df: pd.DataFrame, config: OutputConfig) -> str: ...
   ```
2. 插件注册机制：`configforge/plugins/` 目录自动加载
3. 插件配置 UI：前端动态渲染插件配置表单

**涉及文件**：
- `configforge/plugins/`（新建）、`configforge/core/registry.py`（重构）

**验证标准**：
- [ ] 可自定义插件
- [ ] 插件自动加载
- [ ] 前端动态渲染配置

---

### T-5E-06 国际化剩余页面翻译

**关联缺陷**：D-14
**优先级**：P4
**前置依赖**：T-5D-06（i18n 基础设施）

**方案**：
1. 完成剩余 80% 页面的中文提取和翻译：
   - 配置向导（ConfigWizardView 及所有子组件）
   - 模板市场（TemplateMarketView）
   - 执行历史（ExecutionHistoryView）
   - 定时任务（SchedulesPage）
   - 所有 composable 的错误提示
2. 补充英文翻译
3. 审查翻译质量（术语一致性）

**涉及文件**：
- 所有未在 T-5D-06 中翻译的 `.vue` 文件

**验证标准**：
- [ ] 所有文案有对应翻译
- [ ] 中英文切换无遗漏
- [ ] 术语翻译一致

---

## 附录

### A. 任务依赖关系

```
Phase 5A 内部并行组：
┌─ 组 1（无依赖，可并行）─────────────────────┐
│  T-5A-01 (强制改密)                          │
│  T-5A-03 (PyJWT)                            │
│  T-5A-06 (安全默认值 + CONFIGFORGE_ENV) ◄── 前置 │
│  T-5A-07 (版本号统一)                        │
└──────────────────────────────────────────────┘
         │
         ▼
┌─ 组 2（依赖组 1）────────────────────────────┐
│  T-5A-02 (Fernet 检测) ◄── 依赖 T-5A-06     │
│  T-5A-04 (RBAC 后端) ◄── 架构评审检查点      │
│  T-5A-08 (SSRF)                             │
│  T-5A-10 (HTTPS 文档)                       │
└──────────────────────────────────────────────┘
         │
         ▼
┌─ 组 3（依赖组 2）────────────────────────────┐
│  T-5A-05 (RBAC 前端) ◄── 依赖 T-5A-04       │
│  T-5A-09 (审计日志) ◄── 依赖 T-5A-04        │
└──────────────────────────────────────────────┘
         │
         ▼
Phase 5B: T-5B-01 ~ T-5B-10（大部分可并行）
         │
         ▼
Phase 5C 内部顺序：
  T-5C-04 (覆盖率报告) ◄── 先执行，便于测试时观察覆盖率
         │
         ▼
  T-5C-01 (views 测试) ──┐
  T-5C-02 (后端测试) ────┤── 跨 Phase 依赖：
  T-5C-08 (composable 测试) ◄── 依赖 T-5B-08 (API 统一)
         │                │   T-5C-01 依赖 T-5A-01 (ChangePasswordView)
         │                │   T-5C-01 依赖 T-5A-04/05 (RBAC)
         ▼                │
  T-5C-03 (E2E CI) ──────┤
  T-5C-05 (类型安全) ────┤
  T-5C-06 (组件拆分) ────┤
  T-5C-07 (Pydantic) ────┤
  T-5C-09 (后端 lint) ───┤
  T-5C-10 (前端 lint) ───┤  ← 已合并到 T-5C-05
  T-5C-11 (API 文档) ────┘
         │
         ▼
Phase 5D: T-5D-01 ~ T-5D-07（并行）
         │
         ▼
Phase 5E:
  T-5E-01 → T-5E-02 → T-5E-03 → T-5E-04 → T-5E-05
                                           T-5E-06 (依赖 T-5D-06)

跨 Phase 硬依赖：
- T-5C-01（views 测试）→ 依赖 T-5A-01（ChangePasswordView.vue）、T-5A-04/05（RBAC 逻辑）
- T-5C-08（composable 测试）→ 依赖 T-5B-08（API 层统一）
- T-5E-06（i18n 剩余翻译）→ 依赖 T-5D-06（i18n 基础设施）
```

### B. 工作量估算

| Phase | 任务数 | 估算工作量 |
|-------|--------|-----------|
| 5A | 10 | 中（2-3 周），含并行组，可压缩约 30% |
| 5B | 10 | 中（2-3 周） |
| 5C | 11 | 大（4-5 周），测试编写约 11.5 工作日 + 重构 3 天 + lint 3 天 |
| 5D | 7 | 中（2-3 周） |
| 5E | 6 | 大（4-6 周），存储层迁移是核心工作 |
| **合计** | **44** | **大（14-20 周）** |

### C. Phase 5A 并行任务组

| 并行组 | 任务 | 原因 |
|--------|------|------|
| 组 1 | T-5A-01, T-5A-03, T-5A-06, T-5A-07 | 修改不同文件，无相互依赖 |
| 组 2 | T-5A-02, T-5A-04, T-5A-08, T-5A-10 | 依赖组 1 完成后的基建 |
| 组 3 | T-5A-05, T-5A-09 | 依赖 T-5A-04 完成 |

### D. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 存储层迁移数据丢失 | 高 | 完整备份 + 迁移脚本 + 回滚方案 |
| RBAC 变更影响现有用户 | 中 | 灰度发布 + 兼容旧 token |
| 前端重构引入 bug | 中 | 充分测试 + 逐步重构 |
| AI 功能依赖外部服务 | 低 | 降级处理 + 错误提示 |
| E2E 测试环境不稳定 | 低 | 重试机制 + 超时配置 |
| T-5B-08 Breaking Change | 中 | 渐进式迁移 + `requestOrThrow()` 过渡 |
| T-5B-04 滚动对齐冲突 | 中 | 动态计算 offsetTop 替代固定步长 |
| T-5B-02 索引迁移失败 | 高 | 迁移前备份 + dry-run + 自动恢复 |
