# ConfigForge Phase 4 详细实施计划

> 编制日期：2026-06-19
> 版本范围：v0.8.0 → v1.0.0
> 前置文档：[PROJECT_STATUS_ANALYSIS.md](PROJECT_STATUS_ANALYSIS.md)
> 总任务数：38 项

---

## 总览

| Phase | 版本 | 核心目标 | 子任务数 | 优先级 |
|-------|------|----------|----------|--------|
| 4A | v0.8.0 | 生产就绪 | 13 | P0 — 阻塞生产部署 |
| 4B | v0.8.1 | 代码质量 | 10 | P1 — 影响可维护性 |
| 4C | v0.9.0 | 性能稳定 | 7 | P2 — 影响用户体验 |
| 4D | v1.0.0 | 功能增强 | 8 | P3 — 补齐功能短板 |

---

## Phase 4A：生产就绪（v0.8.0）

> **目标**：解决所有阻碍生产部署的问题，确保系统可以在生产环境安全稳定运行。
> **验收标准**：系统可通过 Docker Compose 一键部署，所有安全风险已缓解，健康检查通过。

---

### T-4A-01 统一 DATA_DIR 配置

**问题**：`connection_store.py` 和 `template_store.py` 的 `DATA_DIR` 使用 `os.path.join(os.path.dirname(__file__), "..", "..", "data")` 硬编码相对路径，不受 `CONFIGFORGE_DATA_DIR` 环境变量控制。Docker 部署时数据可能无法持久化到正确位置。

**方案**：
1. 在 `configforge/utils/paths.py`（新建）中定义统一的路径获取函数：
   ```python
   import os

   def get_data_dir() -> str:
       return os.environ.get("CONFIGFORGE_DATA_DIR",
                             os.path.join(os.getcwd(), "data"))

   def get_upload_dir() -> str:
       return os.environ.get("CONFIGFORGE_UPLOAD_DIR", "tmp/uploads")

   def get_log_dir() -> str:
       return os.environ.get("CONFIGFORGE_LOG_DIR", "tmp/logs")

   def get_output_dir() -> str:
       return os.environ.get("CONFIGFORGE_OUTPUT_DIR",
                             os.path.join(os.getcwd(), "data", "outputs"))
   ```
2. 修改 `connection_store.py` 第 8 行：`DATA_DIR = get_data_dir()`
3. 修改 `template_store.py` 第 13 行：`DATA_DIR = get_data_dir()`
4. 修改 `executions.py`、`scheduler.py`、`ai/settings.py`、`smtp_settings.py`、`notifications.py` 中的 `DATA_DIR` 定义，统一使用 `get_data_dir()`
5. 修改 `files.py`、`preview.py`、`pipeline.py` 中的路径定义，统一使用 `get_upload_dir()`/`get_log_dir()`/`get_output_dir()`

**涉及文件**：
- 新建：`configforge/utils/paths.py`
- 修改：`connection_store.py`, `template_store.py`, `executions.py`, `scheduler.py`, `ai/settings.py`, `notifier/smtp_settings.py`, `notifications.py`, `files.py`, `preview.py`, `pipeline.py`

**验证标准**：
- [ ] 设置 `CONFIGFORGE_DATA_DIR=/tmp/test_data` 后启动，所有数据文件写入该目录
- [ ] 不设置环境变量时，默认行为与当前一致
- [ ] Docker 部署时数据目录可通过环境变量控制

---

### T-4A-02 统一 CONFIGS_DIR 配置

**问题**：`configs.py` 第 60 行 `CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")` 硬编码，不受任何环境变量控制。

**方案**：
1. 在 `utils/paths.py` 中添加：
   ```python
   def get_configs_dir() -> str:
       return os.environ.get("CONFIGFORGE_CONFIGS_DIR",
                             os.path.join(os.getcwd(), "configs"))
   ```
2. 修改 `configs.py` 第 60 行使用 `get_configs_dir()`

**涉及文件**：
- 修改：`utils/paths.py`, `api/configs.py`

**验证标准**：
- [ ] 设置 `CONFIGFORGE_CONFIGS_DIR` 后配置文件读写到指定目录
- [ ] 不设置时默认行为不变

---

### T-4A-03 修复 Fernet 密钥管理

**问题**：未设置 `CONFIGFORGE_ENCRYPTION_KEY` 时，系统自动生成 `.fernet_key` 文件。Docker 重启后容器内文件丢失，导致所有已加密的数据库密码和 API Key 不可恢复。

**方案**：
1. 修改 `ai/settings.py` 和 `smtp_settings.py` 中的 `_get_cipher()`：
   - 如果 `CONFIGFORGE_ENCRYPTION_KEY` 环境变量已设置，使用该值
   - 如果未设置，检查 `.fernet_key` 文件是否存在
   - 如果不存在，**生成新密钥并写入 `.fernet_key`，同时在启动日志中打印 WARNING**
2. 在 `server.py` 的 `lifespan()` 中添加启动检查：
   ```python
   if not os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"):
       logger.warning("CONFIGFORGE_ENCRYPTION_KEY not set. "
                      "Auto-generated key will be lost on container restart. "
                      "All encrypted credentials will become unrecoverable.")
   ```
3. 在 `.env.example` 中加强注释说明

**涉及文件**：
- 修改：`services/ai/settings.py`, `services/notifier/smtp_settings.py`, `server.py`, `.env.example`

**验证标准**：
- [ ] 未设置 `CONFIGFORGE_ENCRYPTION_KEY` 时启动日志有 WARNING
- [ ] 设置后无 WARNING，且已有加密数据可正常解密
- [ ] Docker 重启后加密数据仍可解密

---

### T-4A-04 修复 FastAPI 版本号

**问题**：`server.py` 第 50 行 `version="0.1.0"` 与 `pyproject.toml` 的 `0.7.0` 不一致。

**方案**：
1. 在 `server.py` 中动态读取版本号：
   ```python
   from importlib.metadata import version as pkg_version
   _VERSION = pkg_version("pipeforge")

   app = FastAPI(title="ConfigForge", version=_VERSION, lifespan=lifespan)
   ```
2. 如果 `importlib.metadata` 读取失败（开发模式），回退到读取 `pyproject.toml`

**涉及文件**：
- 修改：`server.py`

**验证标准**：
- [ ] `/docs` Swagger UI 显示正确版本号
- [ ] `/api/health` 返回正确版本号

---

### T-4A-05 Dockerfile 安全加固

**问题**：容器以 root 运行，未设置 `NODE_ENV=production`。

**方案**：
1. 添加非 root 用户：
   ```dockerfile
   RUN groupadd -r appuser && useradd -r -g appuser appuser
   RUN chown -R appuser:appuser /app
   USER appuser
   ```
2. 前端构建阶段添加 `ENV NODE_ENV=production`
3. 添加资源限制注释（实际限制在 docker-compose.yml 中设置）
4. 在 docker-compose.yml 中添加：
   ```yaml
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '1.0'
   ```

**涉及文件**：
- 修改：`Dockerfile`, `docker-compose.yml`

**验证标准**：
- [ ] `docker run` 后容器内进程以非 root 运行（`ps aux | grep uvicorn`）
- [ ] 前端构建产物为 production 模式

---

### T-4A-06 添加 nginx 配置

**问题**：生产环境直接使用 uvicorn 服务静态文件，缺少 SSL 终止、缓存、压缩等。

**方案**：
1. 新建 `nginx/nginx.conf`：
   - 反向代理 `/api/` 到 uvicorn:8000
   - 静态文件缓存（.js/.css/images 30 天）
   - Gzip 压缩
   - 安全头（X-Frame-Options、X-Content-Type-Options、CSP）
   - 请求体大小限制（50MB，与后端一致）
2. 修改 `docker-compose.yml` 添加 nginx 服务
3. 修改 `Dockerfile` 分离前后端（前端产物由 nginx 服务）

**涉及文件**：
- 新建：`nginx/nginx.conf`
- 修改：`docker-compose.yml`, `Dockerfile`

**验证标准**：
- [ ] 通过 nginx 访问前端页面正常
- [ ] API 请求正确代理到后端
- [ ] 静态文件有缓存头
- [ ] 响应有安全头

---

### T-4A-07 增强健康检查

**问题**：`/api/health` 仅返回 `{"status": "ok"}`，未检查实际依赖状态。

**方案**：
1. 修改 `server.py` 的 `health()` 端点：
   ```python
   @app.get("/api/health")
   async def health():
       checks = {
           "status": "ok",
           "version": _VERSION,
           "data_dir_writable": os.access(get_data_dir(), os.W_OK),
           "scheduler_running": _scheduler.running if _scheduler else False,
           "encryption_key_set": bool(os.environ.get("CONFIGFORGE_ENCRYPTION_KEY")),
       }
       if not checks["data_dir_writable"]:
           checks["status"] = "degraded"
       return checks
   ```

**涉及文件**：
- 修改：`server.py`

**验证标准**：
- [ ] `/api/health` 返回版本号、数据目录状态、调度器状态
- [ ] 数据目录不可写时返回 `degraded` 状态

---

### T-4A-08 SSRF 防护

**问题**：`api_reader.py` 用户可指定任意 URL，可访问内网服务（如 `http://169.254.169.254/` 获取云元数据）。

**方案**：
1. 在 `utils/security.py` 中添加 `validate_url()`：
   ```python
   import ipaddress
   from urllib.parse import urlparse

   BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal",
                    "metadata.azure.com"}
   BLOCKED_NETWORKS = [
       ipaddress.ip_network("10.0.0.0/8"),
       ipaddress.ip_network("172.16.0.0/12"),
       ipaddress.ip_network("192.168.0.0/16"),
       ipaddress.ip_network("127.0.0.0/8"),
       ipaddress.ip_network("fd00::/8"),
   ]

   def validate_url(url: str) -> str:
       parsed = urlparse(url)
       if parsed.scheme not in ("http", "https"):
           raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
       hostname = parsed.hostname
       if hostname in BLOCKED_HOSTS:
           raise ValueError(f"Blocked host: {hostname}")
       try:
           ip = ipaddress.ip_address(hostname)
           for network in BLOCKED_NETWORKS:
               if ip in network:
                   raise ValueError(f"Blocked internal IP: {ip}")
       except ValueError:
           pass  # hostname is a domain, not IP — allow DNS resolution
       return url
   ```
2. 在 `api_reader.py` 的 `read_api_info()` 中调用 `validate_url(url)`

**涉及文件**：
- 修改：`utils/security.py`, `services/api_reader.py`

**验证标准**：
- [ ] `http://169.254.169.254/` 被拒绝
- [ ] `http://10.0.0.1/` 被拒绝
- [ ] `http://192.168.1.1/` 被拒绝
- [ ] `https://api.example.com/` 正常通过
- [ ] `ftp://example.com/` 被拒绝（非 HTTP/S 协议）

---

### T-4A-09 API Key 安全加固

**问题**：`auth.py` 使用 `key != API_KEY` 简单字符串比较，存在时序攻击风险；`api_key` 查询参数会出现在 URL 和日志中。

**方案**：
1. 修改 `middleware/auth.py`：
   ```python
   import hmac

   # 替换 key != API_KEY 为：
   if not hmac.compare_digest(key, API_KEY):
       ...
   ```
2. 移除查询参数传递方式（`request.query_params.get("api_key")`）
3. 仅保留 `X-API-Key` 请求头方式

**涉及文件**：
- 修改：`middleware/auth.py`

**验证标准**：
- [ ] `X-API-Key` 头方式正常工作
- [ ] `api_key` 查询参数方式不再工作
- [ ] 使用 `hmac.compare_digest()` 防时序攻击

---

### T-4A-10 CORS 生产配置

**问题**：CORS 默认值为 `http://localhost:5173,http://localhost:5174`，`allow_methods=["*"]` 和 `allow_headers=["*"]` 过于宽松。

**方案**：
1. 修改 `server.py`：
   ```python
   _cors_origins_env = os.environ.get("CORS_ORIGINS", "")
   _cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

   # 开发模式自动添加 localhost
   if not _cors_origins:
       _cors_origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]

   app.add_middleware(
       CORSMiddleware,
       allow_origins=_cors_origins,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
       allow_headers=["Content-Type", "X-API-Key", "Authorization"],
   )
   ```
2. 更新 `.env.example` 说明

**涉及文件**：
- 修改：`server.py`, `.env.example`

**验证标准**：
- [ ] 未设置 `CORS_ORIGINS` 时开发模式正常
- [ ] 设置 `CORS_ORIGINS=https://example.com` 时仅允许该域
- [ ] 非白名单域的跨域请求被拒绝

---

### T-4A-11 CI/CD 完善

**问题**：CI 仅有后端 pytest + 前端 vitest + vue-tsc，缺少 Docker 构建、E2E 测试、安全扫描。

**方案**：
1. 修改 `.github/workflows/ci.yml`，添加 Job：
   - `docker-build`：构建 Docker 镜像，验证启动
   - `e2e`：启动服务后运行 Playwright E2E 测试
   - `security-scan`：运行 `pip audit` / `npm audit`
2. 添加 `docker-push` Job（仅 master 分支触发）：构建并推送到 Docker Hub

**涉及文件**：
- 修改：`.github/workflows/ci.yml`

**验证标准**：
- [ ] CI 流水线包含 4 个 Job：backend、frontend、docker-build、security-scan
- [ ] Docker 构建成功且健康检查通过

---

### T-4A-12 数据版本管理

**问题**：JSON 文件无 schema 版本号，格式变更时无法判断是否需要迁移。

**方案**：
1. 为所有 JSON 存储文件添加 `schema_version` 字段：
   - `data/db_connections.json`: `"schema_version": 1`
   - `data/templates.json`: `"schema_version": 1`
   - `data/schedules.json`: `"schema_version": 1`
   - `data/notifications.json`: `"schema_version": 1`
   - `configs/index.json`: `"schema_version": 1`
2. 在各 Store 的 `_load()` 中检查版本号，如果版本低于当前版本则执行迁移
3. 将现有 `_migrate_state_dict()` 迁移逻辑纳入版本化框架

**涉及文件**：
- 修改：`connection_store.py`, `template_store.py`, `scheduler.py`, `notifications.py`, `configs.py`

**验证标准**：
- [ ] 新创建的 JSON 文件包含 `schema_version` 字段
- [ ] 旧格式文件加载时自动迁移并添加版本号
- [ ] 迁移过程有日志记录

---

### T-4A-13 Store 缓存基础版

**问题**：`connection_store`/`template_store`/`configs` 的 `_load()` 每次请求都从磁盘读取，高频场景下磁盘 I/O 成为瓶颈。

**方案**：
1. 在 `utils/cache.py`（新建）中实现简单的 TTL 内存缓存：
   ```python
   import time

   class TTLCache:
       def __init__(self, ttl: float = 5.0):
           self._cache = {}
           self._ttl = ttl

       def get(self, key: str):
           entry = self._cache.get(key)
           if entry and time.monotonic() - entry["time"] < self._ttl:
               return entry["data"]
           return None

       def set(self, key: str, data):
           self._cache[key] = {"data": data, "time": time.monotonic()}

       def invalidate(self, key: str = None):
           if key:
               self._cache.pop(key, None)
           else:
               self._cache.clear()
   ```
2. 在各 Store 中使用缓存：
   ```python
   _cache = TTLCache(ttl=5.0)

   @classmethod
   def _load(cls) -> dict:
       cached = _cache.get("connections")
       if cached is not None:
           return cached
       data = _load_from_disk()
       _cache.set("connections", data)
       return data

   @classmethod
   def _save(cls, data: dict):
       _save_to_disk(data)
       _cache.invalidate("connections")
   ```
3. 写入时自动失效缓存，读取时优先命中缓存

**涉及文件**：
- 新建：`utils/cache.py`
- 修改：`connection_store.py`, `template_store.py`, `api/configs.py`

**验证标准**：
- [ ] 连续 2 次请求只产生 1 次磁盘读取
- [ ] 写入后立即读取返回最新数据（缓存已失效）
- [ ] TTL 过期后重新从磁盘读取

---

## Phase 4B：代码质量提升（v0.8.1）

> **目标**：消除代码重复、改善可维护性，降低后续开发成本。
> **验收标准**：无超过 100 行的重复逻辑，前端最大组件不超过 400 行。

---

### T-4B-01 提取执行引擎

**问题**：`configs.py`/`wizard.py`/`scheduler.py` 中的 Pipeline 执行逻辑（成功记录、失败处理、AI 诊断、通知推送）高度重复，总计约 400 行重复代码。

**方案**：
1. 新建 `configforge/services/execution_service.py`：
   ```python
   class ExecutionService:
       @staticmethod
       async def execute(state_dict, config_id=None, config_name=""):
           """统一执行入口：准备 → 执行 → 记录 → 通知"""
           ...

       @staticmethod
       def _save_success(exec_id, config_id, config_name, output_files, duration):
           """保存成功执行记录"""

       @staticmethod
       async def _handle_failure(exec_id, config_id, config_name, error, yaml_text, state_dict):
           """失败处理：AI 诊断 + 保存记录 + 通知"""
   ```
2. 修改 `configs.py` 的 `execute_config()` 调用 `ExecutionService.execute()`
3. 修改 `wizard.py` 的 `api_execute()` 调用 `ExecutionService.execute()`
4. 修改 `scheduler.py` 的 `_run_scheduled_pipeline()` 调用 `ExecutionService.execute()`

**涉及文件**：
- 新建：`services/execution_service.py`
- 修改：`api/configs.py`, `api/wizard.py`, `scheduler.py`

**验证标准**：
- [ ] 3 个执行入口行为与重构前一致
- [ ] 执行成功/失败/超时场景均通过测试
- [ ] 重复代码行数减少 300+ 行

---

### T-4B-02 提取 `_get_cipher()`

**问题**：`ai/settings.py` 和 `smtp_settings.py` 中的 `_get_cipher()` 函数完全相同。

**方案**：
1. 新建 `configforge/utils/crypto.py`：
   ```python
   from cryptography.fernet import Fernet
   import os

   _fernet_key_path = os.path.join(os.environ.get("CONFIGFORGE_DATA_DIR", "data"), ".fernet_key")

   def get_cipher() -> Fernet:
       key_env = os.environ.get("CONFIGFORGE_ENCRYPTION_KEY")
       if key_env:
           return Fernet(key_env.encode())
       if os.path.exists(_fernet_key_path):
           with open(_fernet_key_path) as f:
               return Fernet(f.read().strip().encode())
       key = Fernet.generate_key()
       os.makedirs(os.path.dirname(_fernet_key_path), exist_ok=True)
       with open(_fernet_key_path, "w") as f:
           f.write(key.decode())
       return Fernet(key)
   ```
2. 修改 `ai/settings.py` 和 `smtp_settings.py` 导入 `from configforge.utils.crypto import get_cipher`

**涉及文件**：
- 新建：`utils/crypto.py`
- 修改：`services/ai/settings.py`, `services/notifier/smtp_settings.py`

**验证标准**：
- [ ] AI 设置和 SMTP 设置的加密解密功能正常
- [ ] 无重复的 `_get_cipher()` 函数

---

### T-4B-03 提取文件类型分发

**问题**：`preview.py` 和 `pipeline.py` 都有根据文件类型分发到不同 reader 的逻辑。

**方案**：
1. 在 `utils/reader_dispatch.py`（新建）中提取：
   ```python
   def read_file_info(file_path: str, content: bytes, file_type: str, **kwargs) -> dict:
       if file_type == "csv":
           return read_csv_info(content, ...)
       elif file_type == "json":
           return read_json_info(content, ...)
       elif file_type == "xml":
           return read_xml_info(content, ...)
       elif file_type == "parquet":
           return read_parquet_info(file_path, ...)
       else:
           return read_excel_info(io.BytesIO(content))
   ```
2. 修改 `preview.py` 和 `pipeline.py` 使用统一分发函数

**涉及文件**：
- 新建：`utils/reader_dispatch.py`
- 修改：`api/preview.py`, `core/pipeline.py`

**验证标准**：
- [ ] 所有文件类型的预览和推断功能正常
- [ ] 新增文件类型只需修改一处

---

### T-4B-04 清理未使用代码

**问题**：`generators/` 目录业务流程未使用（仅基类继承和测试引用），`error_messages.py` 无任何调用，`AiChatPanel.vue` 标记 `@deprecated` 但未清理。

**方案**：
1. 评估 `generators/` 目录：
   - 保留 `base.py`（ConfigGenerator 基类可能被未来功能使用）
   - 删除 `input/`、`output/`、`processor/` 子目录中的具体实现
   - 更新 `registry.py` 移除对已删除 Generator 的注册
   - 删除 `tests/test_input_generator.py`、`tests/test_processor_generator.py`、`tests/test_output_generator.py`
2. 删除 `utils/error_messages.py`
3. 删除 `components/wizard/AiChatPanel.vue`，检查是否有其他组件引用并移除

**涉及文件**：
- 删除：`generators/input/`, `generators/output/`, `generators/processor/`, `utils/error_messages.py`, `AiChatPanel.vue`, 相关测试
- 修改：`generators/registry.py`, 可能的引用文件

**验证标准**：
- [ ] `uv run pytest` 全部通过
- [ ] `npx vue-tsc --noEmit` 无错误
- [ ] 无对已删除文件的引用

---

### T-4B-05 拆分前端大组件

**问题**：`OutputConfigTab.vue` 787 行、`InputSourceCard.vue` 645 行、`HomeView.vue` 963 行。

**方案**：

**OutputConfigTab.vue → 拆为 4 个文件**：
- `OutputConfigTab.vue`（主组件，~200 行）：类型选择 + 子组件切换
- `ExcelOutputForm.vue`（~150 行）：Excel 输出配置
- `CsvOutputForm.vue`（~100 行）：CSV 输出配置
- `DatabaseOutputForm.vue`（~150 行）：数据库输出配置

**InputSourceCard.vue → 拆为 3 个文件**：
- `InputSourceCard.vue`（主组件，~250 行）：卡片框架 + 文件上传
- `FileBasedInputConfig.vue`（~150 行）：文件类输入的通用配置
- `ApiInputConfig.vue`（~100 行）：API 输入配置（复用 ApiForm）

**HomeView.vue → 拆为 3 个文件**：
- `HomeView.vue`（主组件，~300 行）：页面框架 + 路由
- `HeroSection.vue`（~150 行）：Hero 区域
- `ConfigListSection.vue`（~300 行）：配置列表 + 分页 + 批量操作

**涉及文件**：
- 新建：6 个子组件
- 修改：3 个主组件

**验证标准**：
- [ ] 所有组件不超过 400 行
- [ ] 功能与拆分前完全一致
- [ ] `npx vue-tsc --noEmit` 无错误

---

### T-4B-06 消除 `as any`

**问题**：21 处 `as any` 类型断言（8 个文件），主要集中在对 CheckRule 和 config 联合类型的访问。

**方案**：
1. 为 `CheckRule` 联合类型添加统一的 `table` 字段（后端 `models/wizard.py` 已有 `output_tables`，前端类型需同步）
2. 为 `InputSource['config']` 联合类型添加类型守卫：
   ```typescript
   function isExcelConfig(config: InputSource['config']): config is ExcelInputConfig {
     return config.type === 'excel'
   }
   // 类似地定义 isCsvConfig, isDatabaseConfig, isJsonConfig, isXmlConfig, isParquetConfig, isApiConfig
   ```
3. 为 `OutputTarget['config']` 联合类型添加类型守卫
4. 逐个替换 `as any` 为类型守卫或正确的类型断言

**涉及文件**：
- 修改：`types/wizard.ts`, `stores/wizard.ts`, `CheckpointSection.vue`, `ExportActions.vue`, `OutputConfigTab.vue`, `CodeEditor.vue`, `SettingsPage.vue`, `ConfigWizardView.vue`, `useConfigApi.ts`

**验证标准**：
- [ ] `as any` 数量从 21 降至 0（或仅剩 CodeEditor 第三方库类型问题）
- [ ] `npx vue-tsc --noEmit` 无错误

---

### T-4B-07 统一 API 调用

**问题**：`SchedulesPage.vue` 和 `OutputConfigTab.vue` 直接使用 `fetch()` 绕过 composable 层。

**方案**：
1. `SchedulesPage.vue`：创建 `useScheduleApi.ts` composable，封装所有调度 API 调用
2. `OutputConfigTab.vue`：使用已有的 `useConnectionApi()` 替代直接 `fetch('/api/connections')`
3. `InputSourceCard.vue`：将 `loadApiPreview()` 中的直接 `fetch()` 改为使用 `useTemplateApi` 或 `useWizardApi`

**涉及文件**：
- 新建：`composables/useScheduleApi.ts`
- 修改：`SchedulesPage.vue`, `OutputConfigTab.vue`, `InputSourceCard.vue`

**验证标准**：
- [ ] 源码中无直接 `fetch('/api/...')` 调用（除 composable 层外）
- [ ] 所有 API 调用通过 composable 统一错误处理

---

### T-4B-08 拆分 wizard Store

**问题**：唯一的 `wizard.ts` Store 319 行，承载了步骤导航、数据管理、AI 建议、文件引用等过多职责。

**方案**：
1. `useWizardNavigation`（~60 行）：`currentStep`、`canProceed()`、`nextStep()`、`prevStep()`
2. `useWizardData`（~150 行）：`scene`、`inputs`、`processors`、`output`、`uploadedFiles`、CRUD 方法、`loadFromConfigState()`、`resetAll()`
3. `useAiSuggestion`（~60 行）：`aiSuggestions`、`dryRunResults`、`pendingAutofixes`、`applyAutofixes()`
4. 保留 `wizard.ts` 作为聚合导出（向后兼容）

**涉及文件**：
- 新建：`stores/wizardNavigation.ts`, `stores/wizardData.ts`, `stores/aiSuggestion.ts`
- 修改：`stores/wizard.ts`（改为聚合导出）

**验证标准**：
- [ ] 各 Store 不超过 150 行
- [ ] 现有组件无需修改（通过 `wizard.ts` 聚合导出兼容）
- [ ] `npx vitest run` 全部通过

---

### T-4B-09 添加路由导航守卫

**问题**：用户在向导中途离开时无提示，可能丢失未保存的配置。

**方案**：
1. 在 `router/index.ts` 中添加 `beforeEach` 守卫：
   ```typescript
   router.beforeEach((to, from) => {
     if (from.path === '/config/new' && to.path !== '/config/new') {
       const store = useWizardData()
       if (store.hasUnsavedChanges) {
         return window.confirm('配置尚未保存，确定要离开吗？')
       }
     }
   })
   ```
2. 在 `useWizardData` 中添加 `hasUnsavedChanges` 计算属性（基于是否有输入源或处理器）

**涉及文件**：
- 修改：`router/index.ts`, `stores/wizardData.ts`

**验证标准**：
- [ ] 向导有数据时离开弹出确认提示
- [ ] 空向导离开无提示
- [ ] 确认离开后正常导航

---

### T-4B-10 提取重复逻辑

**问题**：`formatTime` 在 `HomeView.vue` 和 `SchedulesPage.vue` 中重复实现；`encodingOptions` 在 `InputSourceCard.vue` 和 `OutputConfigTab.vue` 中完全相同；连接加载逻辑在多处重复。

**方案**：
1. 新建 `utils/format.ts`：提取 `formatTime()`、`formatFileSize()`
2. 新建 `utils/constants.ts`：提取 `ENCODING_OPTIONS`、`DELIMITER_OPTIONS`、`CATEGORY_OPTIONS`
3. 新建 `composables/useConnections.ts`：提取连接列表加载逻辑

**涉及文件**：
- 新建：`utils/format.ts`, `utils/constants.ts`, `composables/useConnections.ts`
- 修改：`HomeView.vue`, `SchedulesPage.vue`, `InputSourceCard.vue`, `OutputConfigTab.vue`

**验证标准**：
- [ ] 无重复的 `formatTime`、`encodingOptions` 实现
- [ ] 功能与提取前一致

---

## Phase 4C：性能与稳定性（v0.9.0）

> **目标**：提升系统性能和运行稳定性，支撑更大规模的数据处理。
> **验收标准**：1000 条配置列表加载 < 200ms，50MB 文件预览不 OOM。

---

### T-4C-01 大文件流式处理

**问题**：`preview_file()` 和 `infer_input()` 将整个文件读入内存，大文件可能导致 OOM。

**方案**：
1. 为 JSON/XML 读取器添加流式解析选项：
   - JSON：使用 `ijson` 库流式解析，仅读取前 N 条记录
   - XML：使用 `iterparse` 增量解析
2. 为 CSV 读取器添加行数限制参数（已有 `MAX_CSV_ROWS`，但全量读取后再截断）
3. 文件预览端点添加 `max_rows` 参数，默认 100 行

**涉及文件**：
- 修改：`services/json_reader.py`, `services/xml_reader.py`, `services/csv_reader.py`, `api/preview.py`

**验证标准**：
- [ ] 100MB JSON 文件预览不 OOM
- [ ] 预览结果行数不超过 `max_rows` 参数

---

### T-4C-02 配置列表索引优化

**问题**：`list_configs()` 每次全量加载 `index.json` 到内存再排序/过滤，配置数量多时性能差。

**方案**：
1. 在 `configs.py` 中维护内存索引：
   ```python
   _config_index = None
   _index_mtime = 0

   def _get_index():
       global _config_index, _index_mtime
       mtime = os.path.getmtime(INDEX_PATH) if os.path.exists(INDEX_PATH) else 0
       if _config_index is None or mtime > _index_mtime:
           _config_index = _load_index()
           _index_mtime = mtime
       return _config_index
   ```
2. 添加按 `scene_name` 的排序索引
3. 搜索使用二分查找（排序后）

**涉及文件**：
- 修改：`api/configs.py`

**验证标准**：
- [ ] 1000 条配置列表加载 < 200ms
- [ ] 搜索响应 < 50ms

---

### T-4C-03 限流存储持久化

**问题**：AI 限流使用内存存储，多 worker 部署时无效，长期运行可能积累大量 IP 记录。

**方案**：
1. 将限流状态存储到文件（`data/rate_limit.json`），使用文件锁保证一致性
2. 添加定期清理过期记录的逻辑
3. 提供 Redis 后端选项（通过环境变量 `RATE_LIMIT_BACKEND=redis`）

**涉及文件**：
- 修改：`api/ai.py`

**验证标准**：
- [ ] 多 worker 部署时限流生效
- [ ] 过期记录自动清理

---

### T-4C-04 Scheduler 并发控制

**问题**：同一配置的多个调度可能并发执行，无锁机制。

**方案**：
1. 在 `scheduler.py` 中添加执行锁：
   ```python
   _running_configs: set[str] = set()

   def _run_scheduled_pipeline(config_id, ...):
       if config_id in _running_configs:
           logger.info(f"Config {config_id} already running, skipping")
           return
       _running_configs.add(config_id)
       try:
           ...
       finally:
           _running_configs.discard(config_id)
   ```
2. 对于多 worker 部署，使用文件锁（`data/.lock.{config_id}`）

**涉及文件**：
- 修改：`scheduler.py`

**验证标准**：
- [ ] 同一配置不会并发执行
- [ ] 执行失败后锁正确释放

---

### T-4C-05 Scheduler 错误重试

**问题**：定时任务执行失败后无重试机制。

**方案**：
1. 在调度配置中添加重试策略字段：
   ```python
   class ScheduleConfig:
       retry_count: int = 0      # 最大重试次数（0=不重试）
       retry_interval: int = 300 # 重试间隔（秒）
   ```
2. 在 `scheduler.py` 中实现重试逻辑
3. 前端 `SchedulesPage.vue` 添加重试配置 UI

**涉及文件**：
- 修改：`scheduler.py`, `api/schedules.py`, `SchedulesPage.vue`

**验证标准**：
- [ ] 配置重试次数后，失败任务自动重试
- [ ] 重试次数用尽后标记为最终失败

---

### T-4C-06 结构化日志

**问题**：使用标准 `logging.getLogger()`，无统一格式、无请求 ID、无级别配置入口。

**方案**：
1. 在 `utils/logging.py`（新建）中配置结构化日志：
   ```python
   import logging
   import json
   import uuid
   from contextvars import ContextVar

   request_id_var: ContextVar[str] = ContextVar("request_id", default="")

   class JSONFormatter(logging.Formatter):
       def format(self, record):
           return json.dumps({
               "timestamp": self.formatTime(record),
               "level": record.levelname,
               "logger": record.name,
               "message": record.getMessage(),
               "request_id": request_id_var.get(""),
           })

   def setup_logging(level="INFO"):
       handler = logging.StreamHandler()
       handler.setFormatter(JSONFormatter())
       logging.root.handlers = [handler]
       logging.root.setLevel(level)
   ```
2. 在 `server.py` 中添加请求 ID 中间件
3. 添加 `CONFIGFORGE_LOG_LEVEL` 环境变量

**涉及文件**：
- 新建：`utils/logging.py`
- 修改：`server.py`

**验证标准**：
- [ ] 日志输出为 JSON 格式
- [ ] 每个请求有唯一 request_id
- [ ] 可通过环境变量控制日志级别

---

### T-4C-07 审计日志

**问题**：关键操作（删除配置、修改连接、执行 Pipeline）无审计追踪。

**方案**：
1. 新建 `services/audit_logger.py`：
   ```python
   def log_audit(action: str, target_type: str, target_id: str, details: dict = None):
       entry = {
           "timestamp": datetime.now(UTC).isoformat(),
           "action": action,          # create/update/delete/execute
           "target_type": target_type, # config/connection/template/schedule
           "target_id": target_id,
           "details": details or {},
       }
       # 写入 data/audit_log.json（追加模式，使用文件锁）
   ```
2. 在以下端点添加审计记录：
   - `DELETE /api/configs/{id}` → `log_audit("delete", "config", id)`
   - `DELETE /api/connections/{id}` → `log_audit("delete", "connection", id)`
   - `POST /api/configs/{id}/execute` → `log_audit("execute", "config", id)`
   - `PUT /api/connections/{id}` → `log_audit("update", "connection", id)`
   - `DELETE /api/templates/{id}` → `log_audit("delete", "template", id)`
3. 添加 `GET /api/audit-log` 端点（管理员查看）

**涉及文件**：
- 新建：`services/audit_logger.py`
- 修改：`api/configs.py`, `api/connections.py`, `api/templates.py`, `server.py`

**验证标准**：
- [ ] 删除配置后审计日志有记录
- [ ] 执行 Pipeline 后审计日志有记录
- [ ] 审计日志可通过 API 查询

---

## Phase 4D：功能增强（v1.0.0）

> **目标**：补齐功能短板，达到 1.0 里程碑，可正式对外发布。
> **验收标准**：支持多用户、中英文切换、WCAG 2.1 AA 级无障碍。

---

### T-4D-01 用户认证系统

**方案**：
1. 后端：JWT 认证 + 用户模型 + 注册/登录端点
2. 前端：登录页面 + 路由守卫 + Token 管理
3. 角色：admin（全权限）/ editor（创建编辑）/ viewer（只读）
4. 用户数据存储：`data/users.json`（密码 bcrypt 哈希）

**涉及文件**：
- 新建：`models/user.py`, `services/user_store.py`, `api/auth.py`, `middleware/jwt.py`
- 新建：`views/LoginView.vue`, `composables/useAuth.ts`
- 修改：`middleware/auth.py`, `server.py`, `router/index.ts`

**验证标准**：
- [ ] 用户可注册、登录、获取 Token
- [ ] 不同角色有不同权限
- [ ] Token 过期后自动跳转登录页

---

### T-4D-02 国际化（i18n）

**方案**：
1. 集成 `vue-i18n`
2. 提取所有硬编码中文到 `locales/zh-CN.json` 和 `locales/en.json`
3. 添加语言切换 UI（设置页或导航栏）
4. 后端 API 错误消息也支持中英文

**涉及文件**：
- 新建：`locales/zh-CN.json`, `locales/en.json`, `i18n.ts`
- 修改：所有 Vue 组件（200+ 处硬编码中文）

**验证标准**：
- [ ] 切换到英文后所有 UI 文本为英文
- [ ] 切换回中文后所有 UI 文本为中文
- [ ] 语言偏好持久化

---

### T-4D-03 组件级 ErrorBoundary

**方案**：
1. 新建 `components/common/ErrorBoundary.vue`：
   ```vue
   <template>
     <slot v-if="!error" />
     <div v-else class="error-boundary">
       <p>组件渲染出错</p>
       <button @click="retry">重试</button>
     </div>
   </template>
   ```
2. 包裹关键组件（向导步骤、配置列表、模板市场）

**涉及文件**：
- 新建：`components/common/ErrorBoundary.vue`
- 修改：`ConfigWizardView.vue`, `HomeView.vue`, `TemplateMarketView.vue`

**验证标准**：
- [ ] 子组件抛出错误时显示友好 UI 而非白屏
- [ ] 点击"重试"可恢复组件

---

### T-4D-04 键盘导航增强

**方案**：
1. 全局快捷键：`Ctrl+S` 保存、`Ctrl+Enter` 执行、`Ctrl+1~5` 跳转步骤
2. Tab 序列优化：向导步骤内表单字段按逻辑顺序 Tab
3. `Escape` 关闭弹窗

**涉及文件**：
- 新建：`composables/useKeyboard.ts`
- 修改：`ConfigWizardView.vue`, 各步骤组件

**验证标准**：
- [ ] `Ctrl+S` 触发保存
- [ ] `Ctrl+Enter` 触发执行
- [ ] Tab 键在表单字段间按逻辑顺序移动

---

### T-4D-05 无障碍增强

**方案**：
1. 为所有交互元素添加 `aria-label`
2. 数据表格添加 `<caption>` 和 `scope` 属性
3. 弹窗添加焦点陷阱和 `aria-modal`
4. 步骤卡片添加 `role="tablist"` / `role="tab"`
5. 颜色对比度检查，确保满足 WCAG 2.1 AA 标准

**涉及文件**：
- 修改：所有 Vue 组件

**验证标准**：
- [ ] Lighthouse 无障碍评分 > 90
- [ ] 屏幕阅读器可正确朗读所有交互元素

---

### T-4D-06 离线支持

**方案**：
1. 注册 Service Worker 缓存静态资源
2. API 请求失败时使用缓存数据（stale-while-revalidate 策略）
3. 离线提示横幅

**涉及文件**：
- 新建：`sw.ts`, `composables/useOffline.ts`
- 修改：`vite.config.ts`（添加 PWA 插件）

**验证标准**：
- [ ] 离线后已访问过的页面可正常显示
- [ ] 离线时显示提示横幅

---

### T-4D-07 测试覆盖率提升

**方案**：
1. 后端补齐：模板 API/Store、调度 API、执行历史 API、YAML 构建器、通知子系统
2. 前端补齐：TemplateMarketView、SaveAsTemplateModal、ApiForm、NotificationSettings
3. 目标：后端 70%+、前端 60%+

**涉及文件**：
- 新建：多个测试文件

**验证标准**：
- [ ] 后端测试覆盖率 > 70%
- [ ] 前端测试覆盖率 > 60%

---

### T-4D-08 API 文档增强

**方案**：
1. 为所有 60 个端点添加 `summary` 和 `description`
2. 为所有端点添加 `response_model`
3. 添加请求/响应示例
4. 添加标签分组

**涉及文件**：
- 修改：所有 API 路由文件

**验证标准**：
- [ ] `/docs` Swagger UI 展示完整的 API 文档
- [ ] 每个端点有描述、请求体和响应体示例

---

## 执行策略

### 依赖关系

```
T-4A-01 (DATA_DIR) ──→ T-4A-03 (Fernet) ──→ T-4A-12 (数据版本)
     │                                          ↑
     └──→ T-4A-02 (CONFIGS_DIR) ───────────────┘

T-4B-01 (执行引擎) ──→ T-4C-04 (并发控制) ──→ T-4C-05 (重试)
T-4B-02 (crypto)   ──→ T-4A-03 (Fernet)
T-4B-08 (Store 拆分) ──→ T-4B-09 (路由守卫)
T-4D-01 (认证)     ──→ T-4C-07 (审计日志)
```

### 建议执行顺序

**Phase 4A**（可并行分组）：
- 第 1 批：T-4A-01 + T-4A-02 + T-4A-04（配置统一，独立）
- 第 2 批：T-4A-03 + T-4A-09 + T-4A-10（安全相关）
- 第 3 批：T-4A-05 + T-4A-06 + T-4A-07（部署相关）
- 第 4 批：T-4A-08 + T-4A-11 + T-4A-12 + T-4A-13（独立任务）

**Phase 4B**（可并行分组）：
- 第 1 批：T-4B-01 + T-4B-02 + T-4B-03（后端重构）
- 第 2 批：T-4B-04 + T-4B-07 + T-4B-10（清理统一）
- 第 3 批：T-4B-05 + T-4B-06 + T-4B-08 + T-4B-09（前端重构）

**Phase 4C**：按编号顺序执行，T-4C-04 和 T-4C-05 依赖 T-4B-01。

**Phase 4D**：T-4D-01（认证）优先，其余可并行。

### 版本发布节奏

| 里程碑 | 版本 | 触发条件 |
|--------|------|----------|
| Phase 4A 完成 | v0.8.0 | 全部 13 项通过验证 + Docker 部署测试通过 |
| Phase 4B 完成 | v0.8.1 | 全部 10 项通过验证 + 无重复代码 |
| Phase 4C 完成 | v0.9.0 | 全部 7 项通过验证 + 性能基准测试通过 |
| Phase 4D 完成 | v1.0.0 | 全部 8 项通过验证 + E2E 全流程测试通过 |
