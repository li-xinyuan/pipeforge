# Changelog

All notable changes to ConfigForge / PipeForge will be documented in this file.

## [v1.2.1] - 2026-06-27

### E2E 全流程测试 + UI 优化

通过模拟真实用户的端到端全流程测试（登录 → 向导 5 步 → 保存配置 → 首页操作 → 执行流水线），发现并修复 6 个 bug，优化多处 UI 布局。

#### Bug 修复（6 个）

1. **连接创建 camelCase/snake_case 字段名不匹配** — `ConnectionManager.vue` 的 `buildCreatePayload()` 添加 camelCase→snake_case 转换
2. **连接列表显示 "(undefined)"** — `useConnectionApi.ts` 添加 `db_type`→`dbType` 归一化
3. **Python/SQL schema 丢失 `x-ui-widget: code-editor`** — `models.py` 中 `SqlProcessorConfig.sql` 和 `PythonProcessorConfig.script` 重新声明 `json_schema_extra`（Pydantic v2 子类覆盖父类字段时需重新声明）
4. **Step 4 源表不自动选择导致"下一步"禁用** — `OutputConfigTab.vue` 的 `syncSourceTable()` watch 添加 `immediate: true`
5. **版本历史"当前版本"硬编码为 v0** — 前端绑定 `cfg.currentVersion`，`SavedConfig` 类型新增 `currentVersion` 字段
6. **执行配置时 `file_id`/`fileId` 别名冲突导致 `extra_forbidden`** — 后端 `execute_config` 统一使用 alias `fileId`

#### UI 优化

- **版本号统一管理** — 移除 Step 1 版本号手动输入，由系统自动递增 `current_version`，首页和版本历史统一显示 `v1`/`v2`/`v3`
- **输出配置字段布局修复** — `SchemaForm` 新增 `grid` prop 启用内部 2 列网格，CSV/Excel/Database 三种输出类型字段均匀分布
- **Database 输出隐藏 `connection_string` 运行时字段** — 该字段由 pipeline 执行时根据 `connectionId` 自动填充，用户无需手动填写
- **输入配置自动弹出文件选择框** — 选择 Excel/CSV/JSON/XML/Parquet 文件类型后自动触发文件选择对话框，与 Excel 输出模板上传行为一致
- **启用 JSON/XML/Parquet 输入源** — 后端已注册这三个输入插件（基于 `ReaderBackedInputPlugin`，支持完整执行流程），移除前端过时的"仅预览"限制
- **进度条位置优化** — 顶部 padding 24px→10px，与第一步卡片 10px 间距上下对称
- **AI 助手面板间距** — GuidePanel 顶部和底部各留 10px 间距，与进度条对齐

#### 测试覆盖

- 登录/认证、主页导航、Wizard 5 步全流程、首页配置列表/下载/导出/执行/导入/版本历史/连接管理
- 后端配置 API（list/save/update/delete/download/export/versions）全部通过
- 前端 565 测试、后端 200 测试全部通过，无回归

## [v1.2.0] - 2026-06-26

### Phase 5E：架构演进

#### T-5E-01 存储层抽象

引入统一的存储层抽象，使后端实现可在 JSON / SQLite / PostgreSQL 之间切换，为多实例部署和数据库后端铺路。

**抽象层定义（`configforge/storage/base.py`）**
- 7 个 `@runtime_checkable` Protocol 接口：`ConfigStoreProtocol`、`ConnectionStoreProtocol`、`TemplateStoreProtocol`、`UserStoreProtocol`、`ScheduleStoreProtocol`、`AuditStoreProtocol`、`SettingsStoreProtocol`
- 每个 Protocol 与现有 Store 的公开方法签名保持一致，确保向后兼容

**JSON 后端实现（`configforge/storage/json_backend.py`）**
- 6 个委托式实现：`JsonConnectionStore`、`JsonTemplateStore`、`JsonUserStore`、`JsonScheduleStore`、`JsonAuditStore`、`JsonSettingsStore`（SMTP/AI）
- 委托模式：JSON 后端直接调用现有 Store 类/模块函数，不修改任何现有代码，零风险
- `JsonScheduleStore` 适配 `scheduler` 模块函数式 API 到 Protocol 的 dict 接口（含 `add_schedule`/`update_schedule`/`toggle_schedule`/`remove_schedule`/`list_schedules`）

**工厂函数与环境变量切换（`configforge/storage/__init__.py`）**
- `get_connection_store()` / `get_template_store()` / `get_user_store()` / `get_audit_store()` / `get_schedule_store()` / `get_settings_store(kind)` 6 个工厂函数
- 环境变量 `CONFIGFORGE_STORAGE_BACKEND=json|sqlite` 切换后端（默认 `json`，大小写不敏感）
- `lru_cache(maxsize=1)` 缓存单例（`get_settings_store` 因 kind 参数不缓存）
- 未实现后端抛 `NotImplementedError`（SQLite 留待 T-5E-02）

**ConfigStore 低级存储抽取（`configforge/services/config_store.py`）**
- 从 `api/configs.py` 抽取 `CONFIGS_DIR`、`INDEX_PATH`、`INDEX_SCHEMA_VERSION`、`_cache`、`_load_index`、`_save_index`、`_read_version_state`、`_list_version_files`
- `_save_index` 中保留 `configs_total.set(len(data))` Prometheus 指标更新
- `api/configs.py` 改为从 `services.config_store` import 这些符号

**调用点迁移（11 个文件）**
- `api/connections.py`：`ConnectionStore` → `get_connection_store()`，`_update_verified` → `update_verified`
- `api/templates.py`：`TemplateStore` / `audit_logger` / `ai.settings` 懒导入 / `ConnectionStore` 全部迁移到工厂
- `core/pipeline.py`：`ConnectionStore` 懒导入迁移
- `api/auth.py`：`user_store` / `audit_logger` 迁移
- `middleware/auth.py`：`user_store` / `audit_logger` 懒导入迁移
- `api/wizard.py`：`user_store` 懒导入迁移
- `server.py`：`user_store` / `audit_logger` 迁移，`/api/audit-log` 端点改用 `get_audit_store()`
- `api/notifications.py`：`audit_logger` / SMTP `settings` 迁移
- `api/backup.py`：`audit_logger` 迁移
- `api/ai.py`：AI `settings` 迁移
- `api/schedules.py`：5 个 scheduler 函数调用迁移到 `get_schedule_store()`，保留 `ScheduleConfig` 类型导入和 `get_next_run_time` 查询函数

**测试适配**
- `tests/api/test_versions.py`、`tests/api/test_config_versions.py`、`tests/test_schedules_api.py`：monkeypatch 同时 patch `api.configs` 和 `services.config_store` 两个模块的 `CONFIGS_DIR`/`INDEX_PATH`，并 invalidate `_cache`
- 696 个后端测试全部通过

**已知限制（留待 T-5E-02）**
- `JsonScheduleStore` 委托的 `scheduler` 模块函数同时管理存储和 `BackgroundScheduler` 任务注册，"存储"操作有调度器副作用，需在 SQLite 后端中进一步解耦
- Notifications 和 Executions 仍使用内联 JSON 存储，未抽象到 Protocol 层（这两个存储点逻辑复杂且与业务耦合，留作独立子任务）
- RateLimit 是运行时状态而非持久化数据，不纳入 Store 抽象

#### T-5E-02 SQLite 后端实现

实现 SQLite 存储后端，使用 SQLAlchemy 2.0 Core API + WAL 模式，支持并发读。提供 JSON → SQLite 迁移脚本，加密字段（密码、API key）和密码哈希在迁移时直接复制，无需重新加密/哈希。

**Schema 定义与引擎管理（`configforge/storage/sqlite_schema.py`）**
- 6 张表定义：`connections` / `templates` / `users` / `schedules` / `audit_log` / `settings`
- `@lru_cache(maxsize=1)` 缓存引擎实例；`PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL` + `PRAGMA foreign_keys=ON`
- `check_same_thread=False` 兼容 FastAPI 异步；`pool_pre_ping=True` 自动检测断连
- `init_schema()` / `drop_all()` 用于建表和测试清理
- 数据库路径由 `CONFIGFORGE_SQLITE_PATH` 控制（默认 `<data_dir>/configforge.db`）

**6 个 SQLite Store 实现（`configforge/storage/sqlite_backend.py`）**
- `SqliteConnectionStore`：CRUD + Fernet 加密 + `build_connection_string`/`count_references` 委托给现有 `ConnectionStore`（纯逻辑/跨域查询）
- `SqliteTemplateStore`：CRUD + JSON 字段序列化（tags/config_state/requirements）+ `extract_requirements` 委托
- `SqliteUserStore`：CRUD + 复用 `user_store._hash_password`/`_verify_password` + 返回 `User` 模型
- `SqliteAuditStore`：`log_audit` + `get_audit_log` + 自动修剪 `MAX_ENTRIES=10000` + `func.count()` 查询
- `SqliteSettingsStore`：upsert + Fernet 加解密 + Pydantic 模型返回（SMTP/AI）
- `SqliteScheduleStore`：CRUD + `_validate_cron` 验证 + **纯存储（不管理 BackgroundScheduler）** — 与 JSON 后端不同，调度器集成留待 T-5E-04

**工厂函数接入（`configforge/storage/__init__.py`）**
- 新增 `_get_sqlite_class(name)` 懒加载函数，避免 JSON 模式下加载 SQLAlchemy
- 6 个工厂函数添加 `if backend == "sqlite"` 分支，返回对应 `Sqlite*Store` 实例
- 所有 SQLite Store 通过 `@runtime_checkable` Protocol 检查

**JSON → SQLite 迁移脚本（`configforge/utils/migrate_to_sqlite.py`）**
- 7 个迁移函数：`migrate_connections` / `migrate_templates` / `migrate_users` / `migrate_schedules` / `migrate_audit_log` / `migrate_settings(kind)`
- CLI 入口：`python -m configforge.utils.migrate_to_sqlite [--dry-run] [--sqlite-path PATH]`
- 幂等性：重复运行跳过已存在记录（audit_log 例外，只在空表时迁移）
- 加密字段（password、api_key）和密码哈希直接复制 Fernet 密文/哈希值，无需重新加密/哈希
- Configs（pipeline 配置）仍使用 JSON 文件存储，不在迁移范围

**测试覆盖（`configforge/tests/storage/`）**
- `conftest.py`：`sqlite_env` / `json_env` fixtures，每个测试独立临时 DB + lru_cache 清理
- `test_sqlite_backend.py`：60 项 — 6 个 Store 的 CRUD + 加密字段 + JSON 序列化 + 密码哈希 + 审计修剪 + Settings 加解密 + cron 验证
- `test_storage_factory.py`：23 项 — JSON/SQLite 后端切换 + Protocol 合规 + 大小写不敏感 + NotImplementedError + lru_cache 缓存
- `test_migrate_to_sqlite.py`：13 项 — dry-run + 实际迁移 + 幂等性 + 加密保持 + JSON 字段 round-trip
- 全量测试 960 项通过（含新增 96 项 storage 测试，无 regression）
- SQLite 模式 schedules API 烟雾测试 9/9 通过（list/add/update/toggle/remove/invalid_cron/nonexistent_config）

**依赖补全**
- `requirements.txt` 添加 `prometheus_client>=0.20.0`（Phase 5D T-5D-01 遗漏）

**已知限制（留待 T-5E-03 / T-5E-04）**
- `api/schedules.py` 等模块在 import 时绑定 `_schedule_store = get_schedule_store()`，后端切换需在 import 前设置环境变量；运行时切换需重构为每次调用获取 store
- `SqliteScheduleStore` 不管理 `BackgroundScheduler` 任务注册，使用 SQLite 后端时新创建/修改的调度不会自动注册到调度器 — 将在 T-5E-04 通过 APScheduler JobStore 解决
- 其他 API（connections/templates/auth/audit）仍直接调用现有 Store 类，未通过工厂函数，需在后续任务中迁移
- Pipeline configs（configs/）仍使用 JSON 文件存储，未纳入 SQLite 后端

**Bug 修复（全流程测试发现）**
- 修复 SMTP/AI settings API 返回 400 的 bug：`smtp_settings.json` / `ai_settings.json` 中的 `schema_version` 字段（由 `load_with_migration` 元数据写入）被 Pydantic `extra="forbid"` 模型拒绝
  - `configforge/services/notifier/smtp_settings.py` `load_settings()` — 构造模型前 `raw.pop("schema_version", None)`
  - `configforge/services/ai/settings.py` `load_settings()` — 同上
  - `configforge/storage/sqlite_backend.py` `SqliteSettingsStore.load_settings()` — 同上
  - `configforge/utils/migrate_to_sqlite.py` `migrate_settings()` — 迁移时不复制 `schema_version` 到 DB

#### T-5E-03 PostgreSQL 后端支持

**架构重构 — 通用 SQL 后端**
- 新增 `configforge/storage/sql_schema.py` — 通用 SQL schema，支持 SQLite 和 PostgreSQL 双引擎
  - `get_database_url()`：优先读取 `CONFIGFORGE_DATABASE_URL`（PostgreSQL），否则构造 SQLite URL
  - `get_engine()`：根据 URL 自动选择方言；SQLite 启用 WAL/外键，PostgreSQL 使用连接池（`pool_size=10`, `max_overflow=20`, `pool_recycle=3600`）
  - 保留 `Integer` 表示布尔值（0/1），跨方言兼容，避免 `Boolean` 在 Python 端返回 `True/False` 的差异
- 新增 `configforge/storage/sql_backend.py` — 通用 SQL 后端 Store 实现，6 个 `Sqlite*Store` 类从 `sql_schema` 导入，方言无关
- `configforge/storage/sqlite_schema.py` / `sqlite_backend.py` 改为 thin shim，re-export 新模块（向后兼容，现有引用无需修改）

**工厂函数扩展**
- `configforge/storage/__init__.py` 支持 `CONFIGFORGE_STORAGE_BACKEND=postgresql`
- SQLite 和 PostgreSQL 共用 `sql_backend` Store 类（SQLAlchemy Core 自动适配方言）
- PostgreSQL 前置校验：缺少 `CONFIGFORGE_DATABASE_URL` 时抛 `RuntimeError`（含使用示例）
- 后端名称大小写不敏感（`POSTGRESQL` / `Postgresql` 均可）

**数据迁移脚本**
- 新增 `configforge/utils/migrate_to_postgres.py` — SQLite → PostgreSQL 迁移
  - 支持 `--sqlite-path` / `--database-url` / `--dry-run`
  - 幂等：重复运行跳过已存在记录（audit_log 除外，仅在目标表为空时迁移）
  - 加密字段（Fernet）和密码哈希直接复制，无需重新加密

**Docker Compose**
- `docker-compose.yml` 新增 `postgres` 服务（PostgreSQL 17-alpine，`profiles: ["postgres"]` 可选启用）
- 启动方式：`docker compose --profile postgres up -d`
- 新增 `postgres_data` volume 持久化数据
- `configforge` 服务新增 `CONFIGFORGE_STORAGE_BACKEND` / `CONFIGFORGE_DATABASE_URL` 环境变量透传

**测试**
- 新增 `configforge/tests/storage/test_postgresql_backend.py` — 31 项 PostgreSQL 集成测试
  - 覆盖引擎/schema/6 个 Store CRUD/加密字段/方言无关性
  - `@pytest.mark.skipif` 无 `CONFIGFORGE_TEST_POSTGRES_URL` 时自动跳过
- 更新 `test_storage_factory.py`：PostgreSQL 无 URL 时抛 `RuntimeError`（原 `NotImplementedError`）
- 全量测试 823 项通过（792 passed + 31 skipped PostgreSQL），无 regression
- SQLite 全栈 CRUD 烟雾测试通过（6 个 Store create/read/update/delete）
- SQLite → PostgreSQL 迁移脚本 dry-run 6 表全部验证通过

**PostgreSQL 17 实测验证（Homebrew postgresql@17 17.10）**
- 31 项 PostgreSQL 集成测试全部通过（修复 2 处 SmtpSettings 字段名错误：`username`/`from_email` → `user`/`sender`）
- JSON → SQLite → PostgreSQL 端到端迁移验证通过：6 表 2602 行（connections 6 / templates 439 / users 8 / audit_log 2147 / settings 2），行数、内容（id/name/role）、加密哈希（password_hash）全部一致
- 幂等性验证通过：重复迁移全部跳过已存在记录
- PostgreSQL 后端全栈 CRUD 烟雾测试通过：6 Store 类（Connection/Template/User/Audit/Settings/Schedule）create/read/update/delete 全部正常，Fernet 加密 + bcrypt 哈希认证正常
- 全量测试套件 823 passed（792 原有 + 31 PostgreSQL），0 failed
- 修复测试隔离问题：module-scoped `postgres_engine` fixture 保存/恢复环境变量 + 清除工厂函数 lru_cache，避免污染后续测试

**已知限制（留待 T-5E-04 / T-5E-05）**
- `api/schedules.py` 等模块在 import 时绑定 store，运行时切换后端需重构（同 T-5E-02 限制）
- Pipeline configs（configs/）仍使用 JSON 文件存储，未纳入 SQL 后端

**部署文档与前端配置入口**
- `.env.example` 补全 Storage Backend 章节（`CONFIGFORGE_STORAGE_BACKEND` / `CONFIGFORGE_SQLITE_PATH` / `CONFIGFORGE_DATABASE_URL` 三个变量 + 三种后端选型说明）
- `docs/DEPLOYMENT.md` 新增「存储后端选择」章节：三种后端对比表、何时用哪个的选型指南、配置方式（JSON/SQLite/PostgreSQL/Docker Compose）、数据迁移命令
- 新增 `GET /api/storage-backend` 只读 API（admin 权限），返回当前后端类型、方言、表数量、配置摘要（PostgreSQL URL 密码脱敏）、切换指引
- `SettingsPage.vue` 新增「存储后端」页签（桌面 NTabPane + 移动 NCollapseItem，admin only），只读展示当前后端信息 + 切换操作指引 + "需重启生效"提示
- i18n 中英文翻译已补全（`settings.tabs.storage` + `settings.storage.*`）
- 全量测试 823 passed，API 端点实测验证通过，前端 vue-tsc 类型检查通过

#### T-5E-04 多实例部署支持

**SQL 后端调度器静默失败 bug 修复（`configforge/storage/sql_backend.py`）**
- 问题：`SqliteScheduleStore` 的 CRUD 操作只写数据库，不注册 `BackgroundScheduler` 任务，导致 SQL 后端下新建的定时任务永远不执行
- 修复：5 个 CRUD 方法（`add_schedule`/`update_schedule`/`remove_schedule`/`toggle_schedule`/`update_last_run`）同步注册/移除 `BackgroundScheduler` 任务
- 新增模块级辅助函数 `_try_register_job()`：Best-effort 注册，失败时只记录日志不抛异常（任务已持久化到 DB，下次 `start_scheduler()` 会重新加载）
- `update_schedule` 的 enabled 检查：disabled 的 schedule 没有 job，更新时不应调用 `remove_job`/`add_job`（`scheduler.py` 和 `sql_backend.py` 两处同步修复）

**`_register_job` / `_unregister_job` 纯函数化（`configforge/scheduler.py`）**
- 分离调度器管理和存储职责：`_register_job(schedule_dict)` 只注册不持久化，`_unregister_job(schedule_id)` 只移除不持久化
- 多实例防重复执行关键配置：`coalesce=True`（多次错过的触发合并为一次）+ `max_instances=1`（同一 job 不并发执行）
- `start_scheduler()` 从 store 层读取调度任务（支持 JSON 和 SQL 后端），fallback 到 `schedules.json`

**`update_last_run` 方法（`configforge/storage/sql_backend.py` + `json_backend.py`）**
- `SqliteScheduleStore.update_last_run`：直接写 DB，不依赖 scheduler 模块
- `JsonScheduleStore.update_last_run`：直接写 `schedules.json`，不委托给 `scheduler._update_schedule_last_run`（避免无限递归：后者会调用 `store.update_last_run`）
- `ScheduleStoreProtocol` 已有 `update_last_run` 方法签名

**限流跨实例生效（`configforge/utils/rate_limit.py` + `sql_schema.py`）**
- 新增 `rate_limit_table`（`sql_schema.py`）：`id`/`key`/`timestamp` 三列，`key` 建索引
- `RateLimiter.is_allowed()` 改为 dispatcher：`_is_sql_backend()` 检测后端，SQL 后端走 `_is_allowed_sql()`，JSON 后端走 `_is_allowed_file()`（原 `is_allowed` body）
- `_is_allowed_sql()`：数据库事务内完成 per-key 清理 → 概率性全局清理（1% 防止非活跃 key 条目无限增长）→ 计数 → 插入，原子操作
- Fail-open 策略：数据库不可用时允许请求通过（可用性优先于安全性）
- JSON 后端行为不变，继续使用 `fcntl.flock` 文件锁（单机）

**`api/schedules.py` 解耦（import 时绑定 → 请求级获取）**
- 问题：模块级 `_audit = get_audit_store()` / `_schedule_store = get_schedule_store()` 在 import 时绑定，`cache_clear()` 后模块级变量仍指向旧实例，阻碍后端切换
- 修复：5 个端点改为请求级调用 `get_schedule_store()` / `get_audit_store()`，`lru_cache` 保证正常开销极小，`cache_clear()` 后立即生效
- API 签名不变，不影响路由

**测试**
- 新增 12 个 T-5E-04 调度器注册行为单测（`tests/storage/test_sqlite_backend.py`）：add→register、update→re-register、toggle disable→unregister、toggle enable→register、remove→unregister、disabled schedule 不操作调度器、`update_last_run` success/failed/nonexistent
- 新增 8 个 SQL 后端限流测试（`tests/test_rate_limit.py::TestSqlBackend`）：基本限流、独立 key 隔离、窗口过期、跨实例共享状态（核心）、fail-open、过期条目清理、条目写入验证
- 全量测试 810 passed, 31 skipped（PostgreSQL 集成测试），无 regression

**端到端验证（12 步）**
- SQL 后端 CRUD 同步注册 BackgroundScheduler ✓
- `coalesce=True` + `max_instances=1` 防止多实例重复执行 ✓
- `start_scheduler()` 从 DB 重新加载任务 ✓
- 限流跨实例生效（两个 RateLimiter 实例共享同一 DB，host A 消耗配额后 host B 被拒绝）✓

**已知限制（留待 T-5E-05 / T-5E-06）**
- Pipeline configs（configs/）仍使用 JSON 文件存储，未纳入 SQL 后端
- 文件上传仍使用本地磁盘存储，未使用共享存储（如 MinIO/S3）

#### T-5E-05 本地插件系统

**范围说明**：仅包含本地插件接口和自动加载机制。插件市场（远程安装、版本管理、安全审核）拆分到 v2.0.0。

**插件自动加载机制（`src/pipeforge/plugins/_loader.py` 新建）**
- 问题：`src/pipeforge/__init__.py` 手动 import 8 个插件模块，新增插件需修改注册代码，违反开闭原则
- 修复：`load_all_plugins()` 使用 `pkgutil.iter_modules` 扫描 `input`/`processor`/`output` 三个子包，自动 import 所有模块触发 `@register_plugin` 注册
- 跳过以 `_` 开头的私有模块（如 `_loader`、`_helpers`）
- 幂等操作：`@register_plugin` 是覆盖式注册，重复调用无副作用
- `__init__.py` 改为调用 `load_all_plugins()`，新增插件只需放入对应目录，无需修改任何注册代码

**插件配置 Schema 暴露（`src/pipeforge/plugins/base.py`）**
- `Plugin` 基类新增 `config_schema()` 类方法：默认从 `config_model().model_json_schema()` 自动生成 JSON Schema（Pydantic v2）
- 子类可覆盖 `config_schema()` 提供自定义 schema（如增减字段、调整 UI 提示）
- 现有 8 个插件无需修改即可自动生成 schema

**PluginRegistry 元数据 API（`src/pipeforge/core/registry.py`）**
- 新增 `list_all()` 类方法：返回所有已注册插件的详情列表 `[{name, type, label, config_schema}, ...]`
- label 为空时回退为 name，确保前端始终有显示文本
- config_schema 生成失败时返回空 dict（防御性）

**REST API 端点（`configforge/api/plugins.py` 新建）**
- `GET /api/plugins`：返回所有已注册插件清单 + config_schema，支持 `plugin_type` 查询参数过滤
- 权限：viewer/editor/admin（只读端点）
- 注册表为空时自动调用 `load_all_plugins()` 重新加载（处理测试 clear() 场景）
- 前端可据此动态渲染插件配置表单，无需为每个插件硬编码表单字段

**测试**
- 新增 `tests/test_plugin_autoload.py` — 15 项 pipeforge 测试
  - `TestAutoLoad`（5 项）：input/processor/output 插件自动注册、总数 8、幂等性
  - `TestConfigSchema`（4 项）：csv/sql schema 字段验证、所有插件返回 dict、type discriminator 字段
  - `TestListAll`（6 项）：返回 list、8 项、必含字段、type 有效值、label 非空、schema 非空
- 新增 `configforge/tests/test_plugins_api.py` — 7 项 API 端点测试
  - 返回全部 8 插件、按 input/processor/output 过滤、数据结构验证、csv schema 字段、无效类型返回空
  - autouse fixture 处理 `test_registry.py` 的 `clear()` 污染：先 clear 再 reload 真实插件
- 全量测试 1000 passed, 31 skipped，无 regression

**验证标准达成**
- [x] 可自定义插件 — 插件放入 `plugins/{input,processor,output}/` 目录即自动注册
- [x] 插件自动加载 — `load_all_plugins()` 扫描子包，无需手动 import
- [x] 前端动态渲染配置 — `GET /api/plugins` 返回 config_schema，前端可据此渲染表单

**已知限制（留待 T-5E-06 / v2.0.0）**
- 前端尚未实现基于 schema 的动态表单渲染（当前仍为硬编码 v-if 分支），需后续前端工作
- configforge 侧的 `models/wizard.py` 与 pipeforge `config/models.py` 双轨模型未合并
- json/xml/parquet/api 输入源在 configforge 可配置但 pipeforge 未实现对应插件（"幽灵插件"问题）

## [v1.0.0] - 2026-06-26

### Phase 5D：功能增强

#### T-5D-01 监控与可观测性
- **Prometheus 指标**：6 个指标覆盖 HTTP 请求（计数/延迟）、Pipeline 执行（计数/延迟）、活跃连接数、配置总数
- **`/api/metrics` 端点**：标准 Prometheus 文本格式，支持无认证访问
- **前端错误上报**：批量队列（5s 刷新/20 条即时）、全局 `window.error` + `unhandledrejection` + Vue `errorHandler` 捕获
- **`/api/error-report` 端点**：接收前端错误报告并记录到日志，支持无认证访问
- **JSON 结构化日志**：含 `request_id` 关联、日志级别可配置（`CONFIGFORGE_LOG_LEVEL`）

#### T-5D-02 数据备份与恢复
- **备份工具**：`create_backup()` 打包 configs/ 和 data/ 到 zip，含元数据
- **恢复工具**：`restore_backup()` 从 zip 恢复，跳过 backups 目录防递归
- **API 端点**：`GET/POST /api/backup`、`GET /api/backup/download/{filename}`、`POST /api/backup/restore`
- **每日定时备份**：凌晨 2:00 自动执行，保留策略默认最近 7 个
- **安全**：admin 角色鉴权、路径遍历防护、审计日志

#### T-5D-03 配置导入导出
- **导出端点**：`GET /api/configs/{id}/export?format=yaml|json`，RFC 5987 编码支持中文文件名
- **导入端点**：`POST /api/configs/import`，5MB 限制、UTF-8 校验、WizardState 模型校验、自动生成新 ID
- **前端 UI**：首页"导入配置"按钮、配置操作菜单"导出配置/导出为 JSON"
- **前端下载修复**：`useApi.ts` 检测 `Content-Disposition: attachment` 返回 Blob，修复 JSON 导出静默失败

#### T-5D-04 Pipeline 执行通知增强
- **增强字段**：`duration_seconds`、`row_count`、`error_type`、`stack_summary`（含格式化渲染）
- **自定义模板**：`render_template()` 支持 12 个 `{{variable}}` 占位符替换
- **频率控制**：5 分钟冷却期，按 `(config_id, pipeline_id, status)` 三元组去重
- **四种渠道格式化器**：钉钉、企微、飞书、通用 JSON（全部渲染 `stack_summary`）

#### T-5D-05 AI 辅助增强
- **`/api/ai/suggest-checkpoint`**：AI + 规则引擎双路径推荐检查规则
- **`/api/ai/suggest-mapping`**：AI + 规则引擎智能列映射（同义词/规范化/子串匹配）
- **`/api/ai/optimize-suggestions`**：配置优化建议（数据质量/处理/性能）
- **限流**：10 次/60s/IP，30s 超时，AI 失败自动降级到规则引擎

#### T-5D-06 国际化（i18n）— 基础设施 + 高频页面
- **vue-i18n 框架**：`legacy: false` Composition API 模式
- **语言文件**：`zh-CN.json` / `en-US.json`，覆盖 common/nav/login/home/settings/pwa 六大分区
- **4 个高频页面翻译**：LoginView、AppNavBar、HomeView、SettingsPage
- **语言切换器**：SettingsPage 语言 Tab，`NSelect` 组件，立即生效
- **语言持久化**：`configforge_locale` localStorage，启动时自动检测

#### T-5D-07 PWA 离线支持
- **vite-plugin-pwa**：Service Worker 自动注册（`autoUpdate`）、静态资源缓存
- **Manifest**：standalone 模式、完整图标集（192/512/maskable/apple-touch-icon）
- **运行时缓存策略**：Google Fonts (StaleWhileRevalidate)、API (NetworkFirst 5min)
- **离线回退**：`navigateFallback: index.html`，API 路径排除
- **更新提示 UI**：`PwaUpdatePrompt` 组件（新版本 + 离线就绪通知）
- **i18n**：PWA 相关文案中英文翻译

### Bug 修复

- **认证白名单**：`/api/metrics` 和 `/api/error-report` 加入 `PUBLIC_PATHS`，允许 Prometheus 抓取和未登录用户上报错误
- **Pipeline metrics 接入**：`record_pipeline_execution()` 在 `_handle_success/_handle_failure` 中调用，`active_connections` 在执行前后 inc/dec
- **configs_total Gauge**：在 `_save_index()` 中更新，配置增删后自动同步
- **中文场景名导出**：`safe_name` 使用 `c.isascii() and c.isalnum()`，`Content-Disposition` 使用 RFC 5987 `filename*` 编码
- **JSON 导出前端**：`useApi.ts` 检测 `Content-Disposition: attachment` 返回 Blob，不再解析为 JSON 对象
- **通知 `stack_summary`**：四种格式化器 + `render_template` + `get_template_variables` 全部补上该字段
- **语言切换提示**：从"刷新后生效"改为"立即生效"（vue-i18n 响应式切换）
- **PWA 离线就绪 UI**：`PwaUpdatePrompt` 添加 `offlineReady` 通知，5 秒自动消失
- **认证 probe 修复**：`checkJwtStatus()` 使用原生 `fetch` 而非 `useApi`，避免 401 probe 触发全局 `clearAuth()`

## [v0.7.0] - 2026-06-19

### Phase 3E：配置市场

- **模板市场页面**：分类浏览（销售/财务/人力/运维/通用）、搜索、预览弹窗
- **4 个内置模板**：月度销售报表、财务汇总报表、库存跟踪管理、用户数据清洗（中文）
- **使用模板**：一键加载模板配置到向导，从步骤 1 开始逐步检查
- **保存为模板**：向导 Step 5 新增"保存为模板"按钮，将当前配置保存为可复用模板
- **兼容性检查**：模板详情中检查数据库连接、AI 配置等环境依赖
- **模板 API**：7 个端点（CRUD + 实例化 + 兼容性检查）
- **导航集成**：首页"浏览模板市场"按钮、导航栏"模板市场"入口

### Phase 3D：数据源扩展

- **JSON 输入**：支持 .json 文件，自动展平嵌套字段，可配置展平分隔符
- **XML 输入**：支持 .xml 文件，自动检测行元素，可手动指定 XPath 路径
- **Parquet 输入**：支持 .parquet 大数据文件，自动推断 schema
- **REST API 输入**：从 HTTP 接口拉取数据，支持 GET/POST、自定义请求头和参数、数据路径、三种分页模式
- **文件上传白名单扩展**：支持 .json / .xml / .parquet 格式
- **API 推断端点**：新增 `/api/wizard/infer-api-input/{input_name}` 专门处理 REST API 输入
- **Preview 端点扩展**：文件预览和 SQL 预览支持新文件类型

### Phase 3C：AI 自愈

- **自动诊断**：Pipeline 执行失败时自动调用 AI 诊断，返回错误原因和修复建议
- **一键修复**：诊断结果可直接应用到配置（SQL 修正、参数调整等）
- **诊断趋势**：执行历史页面新增诊断趋势标签页，含 AnomalyChart 异常图表
- **DiagnosisPanel 组件**：展示错误分析、影响评估、修复建议、AI 对话
- **LRU 缓存**：诊断结果缓存（100 条，1 小时 TTL），避免重复调用 AI

### Phase 3B：推送分发

- **通知推送系统**：邮件（SMTP）和 Webhook 两种通知渠道
- **通知配置管理**：创建/编辑/删除/测试通知规则
- **Pipeline 执行通知**：执行成功/失败后自动推送通知
- **SMTP 设置**：独立的 SMTP 服务器配置和测试
- **通知历史**：查看已发送的通知记录
- **NotificationSettings 组件**：向导 Step 5 集成通知设置

### Phase 3A：技术债务清理

- **删除根目录 package.json**：消除版本冲突
- **pyproject.toml 补充依赖**：pymysql、psycopg2-binary 声明
- **Dockerfile / docker-compose.yml / .env.example / Makefile**：生产部署基础设施
- **CI/CD**：GitHub Actions（后端 pytest + 前端 vitest + vue-tsc）
- **前端 API 拆分**：useConfigApi / useConnectionApi / useAiApi / useNotificationApi / useTemplateApi
- **前端测试扩展**：24 个测试文件，201 个测试用例
- **移动端适配**：@media 响应式布局

### Bug 修复

- 修复 XML 文件上传返回 "Unsupported format" 错误
- 修复 `sample_values` 按列取值错误（所有列返回相同值）
- 修复模板实例化后数据被 `onMounted` 的 `resetAll()` 清空
- 修复分类筛选值不匹配（前端中文 vs 后端英文）
- 修复 API 推断端点 URL 错误

## [v0.5.0] - 2026-06-14

### Security (BLOCKER)

- **B-1** SQL 注入防护：`_is_read_only_sql()` 白名单检查，仅允许 SELECT 语句执行
- **B-1b** 数据库输出 `source_table` 注入防护：`safe_identifier()` 校验 SQL 标识符
- **B-2/B-3/B-4** 路径遍历防护：`validate_id()` 校验 connections/executions/schedules 的 ID 参数
- **B-6** 密码脱敏：`sanitize_connection_string()` 隐藏 API 返回中的数据库密码
- **B-7** DDL/DML 正则扩展：拦截 ATTACH/DETACH/PRAGMA/VACUUM/REINDEX 等操作
- **B-8** 文件上传流式写入：大文件分块写入，避免 OOM

### Stability (HIGH)

- **H-1** 文件操作竞态条件：`read_json_locked()`/`write_json_locked()` 统一文件锁（fcntl.flock）
- **H-2** SQL 预览样本提示：前端显示"预览基于样本数据"提示文案
- **H-3** 废弃 Step 视图清理：移除未使用的旧组件
- **H-4** MySQL 兼容性：反引号引用 + ON DUPLICATE KEY UPDATE 语法
- **H-5** replace 模式事务一致性：使用 `engine.begin()` 确保事务
- **H-6** DataPreviewTable 集成到 Step 5
- **H-7** Pipeline 执行超时：`PipelineTimeoutError` + signal.alarm 保护
- **H-8** API Key 认证中间件：`AuthMiddleware`（可选，默认关闭）

### Features (MEDIUM)

- **M-1~M-21** 21 项中等优先级优化：类型系统改进、死代码清理、测试修复、错误消息完善等
- 数据库输出（MySQL/PostgreSQL/SQLite）：支持 append/replace/upsert 模式
- 配置版本管理：自动保存历史版本，可查看和回滚
- 执行历史：查看每次执行的状态、时间、日志
- 定时任务：APScheduler Cron 调度，支持启用/禁用
- Pipeline `infer_output()` 基于输入源推断输出列

### UI/UX

- **CodeMirror 6 编辑器**：替换 SQL/Python/YAML 的 textarea 为语法高亮编辑器
  - SQL：蓝色关键字、绿色字符串、橙色数字、粉红运算符
  - Python：紫色关键字、蓝色函数名、橙色装饰器
  - YAML：紫色键名、绿色字符串、蓝色关键字
  - 亮色/暗色双主题，自动跟随系统切换
  - 行号、自动补全、括号匹配、代码折叠
  - happy-dom 测试环境自动降级为 textarea
- **暗色模式全组件适配**：17+ 个 Vue 组件添加 `dark:` Tailwind 变体
- **步骤类型选择风格统一**：Step 2/3/4 类型选择卡片统一为实线边框+背景色+描述文字
- **主题持久化修复**：`AppNavBar` 改用 `useTheme()` 共享状态，localStorage 正确保存
- **按钮大小统一**："上一步"/"下一步"/导出操作按钮统一为默认大小
- **GuideView 文档补充**：数据库输入/输出、多步骤处理、版本管理、执行历史等

### Quality (LOW)

- **L-1~L-10** 10 项低优先级改进：无障碍性、响应式、测试覆盖等
- 后端 `_periodic_cleanup()` 定时清理临时文件/日志
- Playwright E2E 测试框架搭建（home + wizard 测试用例）
- 前端测试从 113 增至 143 个

## [v0.4.0] - 2026-05-xx

- Python 处理器（exec + 超时 + ctx API）
- SQL+Python 混合 DAG
- 文件名标签
- 步骤 3 操作统一

## [v0.3.1] - 2026-05-xx

- AI 编排步骤链（自然语言 → 多步 SQL）
- Typewriter 效果
- Confetti 庆祝动画

## [v0.3.0] - 2026-04-xx

- 多步 SQL Pipeline + DAG 拓扑排序
- 处理步骤卡片列表
- 错误中文提示

## [v0.2.1] - 2026-04-xx

- 数据库输入源（SQLite/MySQL/PG）
- 安全加固（31 项缺陷修复）

## [v0.2.0] - 2026-03-xx

- 前端重设计（单页滚动向导）
- AI SQL 生成
- 暗色模式
- 配置管理
- CSV 支持
