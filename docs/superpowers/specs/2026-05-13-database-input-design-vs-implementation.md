# v0.2.1 数据库输入源 — 设计对比与问题清单

> **验证日期**: 2026-05-13  
> **代码位置**: `.worktrees/v0.2.1-db-input/`  
> **设计文档**: `docs/superpowers/specs/2026-05-19-database-input-source-design.md`

---

## 一、测试结果总览

| 项目 | 结果 |
|------|------|
| 后端测试 | ✅ **230 passed** in 0.98s（比主分支多 21 个新测试） |
| 前端类型检查 | ✅ 零错误 |
| API 创建连接 | ✅ `POST /api/connections` 正常 |
| API 列出连接 | ✅ `GET /api/connections` 正常 |
| API 测试连通 | ❌ 500 Internal Server Error |
| API 加载表列表 | ❌ 500 Internal Server Error |
| API 获取列信息 | ❌ 500 Internal Server Error |

---

## 二、设计 vs 实现对比

### 2.1 后端 Python 对比

| # | 设计要求 | 实现状态 | 偏差说明 |
|---|----------|----------|----------|
| 1 | `DbInputConfig` 模型 | ✅ 已实现 | `models.py` L32-39，字段完全匹配 |
| 2 | `InputSpec.config` 三成员 union | ✅ 已实现 | L49 `ExcelInputConfig \| CsvInputConfig \| DbInputConfig` |
| 3 | `tables` 和 `sql` 互斥验证 | ❌ **未实现** | `DbInputConfig` 无 `@model_validator` |
| 4 | `database.py` 输入插件 | ✅ 已实现 | `plugins/input/database.py`，49 行 |
| 5 | `@register_plugin("database", "input")` | ✅ 已实现 | L8 |
| 6 | SQLAlchemy 连接 + NullPool/pool_size | ✅ 已实现 | L17, L21 |
| 7 | `ConnectionStore` 持久化 | ✅ 已实现 | `services/connection_store.py`，171 行 |
| 8 | Fernet 加密密码 | ✅ 已实现 | L47-50，复用 `_get_cipher()` |
| 9 | `data/db_connections.json` 存储 | ✅ 已实现 | L9 |
| 10 | 文件锁 `fcntl.flock` | ✅ 已实现 | L21, L31 |
| 11 | `build_connection_string()` | ✅ 已实现 | L131-146，支持 sqlite/mysql/postgresql |
| 12 | `count_references()` 引用检查 | ⚠️ Stub | L149-152 返回空列表 `[]`，未实际实现 |
| 13 | 8 个 API 端点 | ✅ 已实现 | `api/connections.py`，163 行 |
| 14 | 创建连接验证 | ✅ 已实现 | SQLite 必须有 file_path |
| 15 | 删除连接引用检查 | ⚠️ 调用 Stub | L82 调用 `count_references()` 但返回空 |
| 16 | 连接测试超时 10s | ❌ **未实现** | `test_connection()` 无超时设置 |
| 17 | `verified` 字段更新 | ❌ **未实现** | 测试成功后未更新 `verified=True` |
| 18 | SQLite 文件头校验 | ❌ **未实现** | 无文件头 `SQLite format 3` 检查 |
| 19 | 连接密码脱敏返回 | ✅ 已实现 | `_summarize()` 返回 `passwordSet: bool` |
| 20 | `connectionId → connection_string` 转换 | ⚠️ 部分实现 | `ConnectionStore.build_connection_string()` 存在，但 `pipeline.py` 未调用 |

### 2.2 前端 Vue/TS 对比

| # | 设计要求 | 实现状态 | 偏差说明 |
|---|----------|----------|----------|
| 21 | `DatabaseInputConfig` 类型 | ✅ 已实现 | `wizard.ts` L42-48 |
| 22 | `DbConnection` discriminated union | ✅ 已实现 | `wizard.ts` L50-70 |
| 23 | `DbConnectionSummary` 类型 | ✅ 已实现 | `wizard.ts` L72-85 |
| 24 | `InputSource.plugin` 三成员 | ✅ 已实现 | `wizard.ts` L88 `'excel' \| 'csv' \| 'database'` |
| 25 | `addInput('database')` | ✅ 已实现 | `stores/wizard.ts` L37-53 |
| 26 | `DatabaseForm.vue` | ✅ 已实现 | 132 行，含连接选择/测试/表浏览/SQL编辑 |
| 27 | `ConnectionManager.vue` | ✅ 已实现 | `components/common/`，145 行 |
| 28 | `useConnectionApi()` composable | ✅ 已实现 | `useWizardApi.ts` L112-184 |
| 29 | `SettingsPage` 嵌入 ConnectionManager | ✅ 已实现 | L85-87 |
| 30 | `InputSourceList` Database 卡片 | ✅ 已实现 | 可点击，不再标记 v0.4 |
| 31 | `TableBrowser.vue` 独立组件 | ❌ **未实现** | 表浏览逻辑内联在 `DatabaseForm.vue` 中 |
| 32 | `dbConnections.ts` 独立 Store | ❌ **未实现** | 使用 `useConnectionApi()` composable 替代 |
| 33 | 连接密码前端不持久化 | ✅ 已实现 | 前端不存储密码，仅传到 API |
| 34 | `queryType` 切换 UI | ✅ 已实现 | NRadioGroup table/sql 切换 |
| 35 | 反序列化 database 类型 | ⚠️ 部分 | `DatabaseForm.vue` L74-83 用 `as any` 读取 config |

### 2.3 实现率统计

| 层次 | 设计项数 | 完全实现 | 部分实现 | 未实现 | 实现率 |
|------|----------|----------|----------|--------|--------|
| 后端 Python | 20 | 15 | 2 | 3 | **75%** |
| 前端 Vue/TS | 15 | 12 | 1 | 2 | **80%** |
| **合计** | **35** | **27** | **3** | **5** | **77%** |

---

## 三、问题清单

### 🔴 严重问题（2 个）

#### P1: SQLAlchemy 未安装导致 API 500 错误

**现象**: `POST /api/connections/{id}/test`、`GET /api/connections/{id}/tables`、`GET /api/connections/{id}/tables/{table}/columns` 均返回 500 Internal Server Error

**根因**: 运行中的 uvicorn 进程使用的 Python 环境未安装 `sqlalchemy` 模块

**验证**:
```bash
/opt/homebrew/bin/python3 -c "import sqlalchemy"
→ ModuleNotFoundError: No module named 'sqlalchemy'
```

**影响**: 所有数据库连接功能（测试连通、加载表列表、获取列信息）完全不可用

**修复**: 在运行服务的 Python 环境中安装 `pip install sqlalchemy`

---

#### P2: connectionId → connection_string 转换未在管道执行时调用

**现象**: `ConnectionStore.build_connection_string()` 方法存在，但 `pipeline.py` 中未调用

**影响**: 通过 ConfigForge 创建的数据库输入配置（YAML 中只有 `connectionId`）在 CLI 执行时会因缺少 `connection_string` 而失败

**设计要求**: API 层在调用引擎前，将 `connectionId` 解析为 `connection_string`

**当前状态**: `connections.py` 的 `test_connection()` 和 `list_tables()` 中调用了 `build_connection_string()`，但 `wizard.py` 的 `generate_yaml()` 和 `execute_pipeline()` 中未处理 database 类型的 `connectionId` 转换

---

### 🟡 中等问题（5 个）

#### P3: `DbInputConfig` 缺少 tables/sql 互斥验证

**设计要求**: `@model_validator` 强制 `tables` 和 `sql` 互斥

**现状**: `models.py` L32-39 的 `DbInputConfig` 无任何互斥验证

**风险**: 用户可能同时传入 `tables` 和 `sql`，行为不确定

---

#### P4: `count_references()` 是空 Stub

**设计要求**: 删除连接时检查引用，有引用返回 409

**现状**: `connection_store.py` L149-152 返回空列表 `[]`，删除连接永远不会触发 409

**风险**: 删除被引用的连接后，相关管道执行时会报错

---

#### P5: 连接测试成功后未更新 `verified` 字段

**设计要求**: 测试连通后标记 `verified=True`

**现状**: `connections.py` L96-115 的 `test_connection()` 返回结果但不更新 store

**影响**: 前端显示的"未验证"标签永远不会消失

---

#### P6: 连接测试无超时设置

**设计要求**: 默认 10s 超时

**现状**: `connections.py` L96-115 的 `test_connection()` 中 `create_engine()` 无 `connect_args={"connect_timeout": 10}`

**影响**: 对不可达的远程数据库，测试请求可能长时间挂起

---

#### P7: SQLite 文件路径无安全校验

**设计要求**: 校验文件头 `SQLite format 3`

**现状**: 无任何校验，用户可填入任意路径

**影响**: 可能触发路径遍历或读取非 SQLite 文件导致错误

---

### 🟢 轻微问题（4 个）

#### P8: `TableBrowser.vue` 未独立抽取

**设计要求**: 独立的 `TableBrowser.vue` 组件

**现状**: 表浏览逻辑内联在 `DatabaseForm.vue` 中

**影响**: 代码组织略差，但不影响功能

---

#### P9: `dbConnections.ts` 独立 Store 未创建

**设计要求**: 独立的 Pinia Store

**现状**: 使用 `useConnectionApi()` composable 替代

**影响**: composable 方案更轻量，实际是合理的简化

---

#### P10: `DatabaseForm.vue` 中 `as any` 类型断言

**位置**: L74-83

**影响**: 类型安全风险，但功能正常

---

#### P11: `ConnectionManager.vue` 缺少编辑功能

**设计要求**: CRUD 完整

**现状**: 仅有创建、测试、删除，无编辑（PUT）

**影响**: 修改连接需删除后重建

---

## 四、设计偏差总结

| 偏差类型 | 数量 | 说明 |
|----------|------|------|
| **功能缺失** | 5 | 互斥验证、引用检查、verified更新、超时、文件校验 |
| **架构简化** | 2 | TableBrowser 内联、Store 用 composable 替代（合理简化） |
| **依赖缺失** | 1 | SQLAlchemy 未安装 |
| **功能不完整** | 1 | ConnectionManager 缺编辑 |

---

## 五、修复优先级建议

| 优先级 | 问题 | 修复量 |
|--------|------|--------|
| 🔴 P1 | 安装 SQLAlchemy | 1 条命令 |
| 🔴 P2 | pipeline 中 connectionId 转换 | ~20 行 |
| 🟡 P3 | 添加互斥 model_validator | ~10 行 |
| 🟡 P4 | 实现 count_references | ~15 行 |
| 🟡 P5 | 测试成功更新 verified | ~5 行 |
| 🟡 P6 | 添加连接超时 | ~3 行 |
| 🟡 P7 | SQLite 文件头校验 | ~8 行 |
| 🟢 P8-P11 | 轻微项 | 可后续处理 |

---

*报告时间: 2026-05-13*
