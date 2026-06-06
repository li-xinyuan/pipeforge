# ConfigForge 修复与优化计划

> 日期：2026-06-04
> 基于：2026-06-04-project-comprehensive-review.md
> 原则：按安全 → 数据完整性 → 代码质量 → UX → 清理 的顺序，每步可验证

---

## Phase 1: 安全漏洞修复（Blocking）

### 1.1 Python exec() 沙箱加固
- **文件**: `src/pipeforge/plugins/processor/python.py`
- **问题**: `__builtins__` 完整传入，可执行任意代码
- **方案**: 
  - 构建 `__builtins__` 白名单（len/range/str/int/float/list/dict/tuple/set/bool/print/enumerate/zip/map/filter/sorted/reversed/sum/min/max/abs/round/type/isinstance/hasattr/getattr/None/True/False）
  - AST 预检：禁止 `import`/`__import__`/`eval`/`exec`/`open`/`compile`/`globals`/`locals`/`dir`/`vars`
  - 超时改用 `multiprocessing`（跨平台兼容，避免 SIGALRM 在异步环境不可靠）

### 1.2 SQL 注入修复
- **文件**: `configforge/api/preview.py`, `src/pipeforge/plugins/input/database.py`, `src/pipeforge/core/sqlite.py`
- **方案**:
  - 新增 `safe_identifier()` 工具函数：白名单校验（仅允许字母数字下划线，最大长度 64）
  - `preview.py`: 表名/列名使用 `safe_identifier()` 校验
  - `database.py`: 表名使用 SQLAlchemy `table()` 构造器
  - `sqlite.py`: `query()` 增加参数化支持，`create_table()` 使用 `safe_identifier()`

### 1.3 临时文件磁盘泄漏修复
- **文件**: `configforge/core/pipeline.py`
- **方案**: 使用 FastAPI `BackgroundTasks` 在响应完成后清理 `persist_dir`

### 1.4 连接密码泄漏修复
- **文件**: `configforge/api/connections.py`
- **方案**: `test_connection` 异常时返回脱敏信息，不暴露原始错误

---

## Phase 2: 数据完整性修复（Blocking）

### 2.1 ExportActions.vue 序列化 bug
- **文件**: `configforge-web/src/components/step4/ExportActions.vue`
- **问题**: `saveConfigHandler` 手动构建 state，camelCase 未转换
- **方案**: 删除手动构建，改用 `stateToSnakeCase(store.getWizardState())`

### 2.2 dryRun 序列化 bug
- **文件**: `configforge-web/src/components/step3/SqlProcessorContent.vue`
- **问题**: 直接传 `store.$state`（camelCase）
- **方案**: 改用 `stateToSnakeCase(store.getWizardState())`

### 2.3 loadFromConfigState 缺少 dbType 转换
- **文件**: `configforge-web/src/stores/wizard.ts`
- **方案**: 在 database 分支添加 `cfg.dbType = cfg.db_type || ''` 和 `delete cfg.db_type`

### 2.4 model_dump by_alias 一致性
- **文件**: `configforge/api/configs.py`
- **方案**: `model_dump()` 改为 `model_dump(by_alias=True)` 或统一使用字段名

---

## Phase 3: 代码质量提升（Important）

### 3.1 Pydantic extra="forbid" 统一
- **文件**: `configforge/models/wizard.py`, `configforge/models/ai.py`
- **方案**: 所有模型添加 `model_config = ConfigDict(extra="forbid")`

### 3.2 _has_ddl() 检测补全
- **文件**: `configforge/core/pipeline.py`
- **方案**: 增加 `CREATE VIEW`/`CREATE INDEX`/`WITH` CTE 检测

### 3.3 pipeline.py 代码去重
- **文件**: `configforge/core/pipeline.py`
- **方案**: 提取 `_prepare_execution()` 公共函数

### 3.4 硬编码配置提取
- **文件**: 多处
- **方案**: 提取为环境变量，统一到 `config.py`

### 3.5 API 异常处理补全
- **文件**: `configforge/api/wizard.py`, `configforge/api/configs.py`
- **方案**: 所有端点添加 `_USER_ERRORS` 映射

### 3.6 CheckpointError 信息保留
- **文件**: `configforge/server.py`
- **方案**: 全局异常处理器识别 `CheckpointError`，保留 checks 信息

### 3.7 前端 post 函数非 JSON 响应处理
- **文件**: `configforge-web/src/composables/useWizardApi.ts`
- **方案**: `resp.json()` 加 `.catch()` 处理

### 3.8 count_references 路径修复
- **文件**: `configforge/services/connection_store.py`
- **方案**: 搜索 `*.state.json` 而非 `*.json`

---

## Phase 4: UX 修复

### 4.1 步骤 2 验证补全
- **文件**: `configforge-web/src/views/ConfigWizardView.vue`
- **方案**: 添加表名非空校验

### 4.2 删除操作确认对话框
- **文件**: InputSourceCard.vue, ProcessorCard.vue, OutputConfigTab.vue
- **方案**: 使用 `useDialog` 添加确认

### 4.3 键盘焦点管理
- **文件**: `configforge-web/src/views/ConfigWizardView.vue`
- **方案**: `scrollToStep()` 中添加焦点移动

### 4.4 步骤 1 表单统一为 Naive UI
- **文件**: `configforge-web/src/views/ConfigWizardView.vue`
- **方案**: 原生 input/textarea 替换为 NInput

### 4.5 添加"上一步"按钮
- **文件**: `configforge-web/src/views/ConfigWizardView.vue`
- **方案**: 每个 step footer 添加"← 上一步"

---

## Phase 5: Minor 修复和清理

- 重复导入清理（settings.py, preview.py, pipeline.py）
- @playwright/test 移到 devDependencies
- ExcelOutputPlugin 列宽优化
- CSV 大文件流式读取
- excel_reader try/finally 关闭 workbook
- YAML 序列化脱敏连接字符串
