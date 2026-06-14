# ConfigForge 优化与修复方案

> 生成时间：2026-06-13
> 状态：待审查

---

## 一、BLOCKER 级别（安全漏洞 / 数据丢失风险）

### B-1. SQL 注入风险 — 执行引擎直接执行用户 SQL

**问题文件**: `src/pipeforge/plugins/processor/sql.py` 第21行

**现状**: `context.db.execute(rendered_sql)` 直接执行 Jinja2 渲染后的 SQL，无参数化查询保护。虽然使用了 `SandboxedEnvironment`，但 Jinja2 沙箱仅限制模板操作，不限制 SQL 语句本身。用户可写入 `DROP TABLE`、`ATTACH DATABASE` 等破坏性 SQL。

**影响范围**: 当 pipeline 连接到 MySQL/PostgreSQL 时，恶意 SQL 可删除生产数据、读取敏感信息。当前 SQLite 场景下风险较低（因为是临时数据库），但真实数据库连接场景下是致命漏洞。

**修复方案**:

方案 A（推荐）：对真实数据库连接增加 SQL 语句白名单检查

```python
# src/pipeforge/plugins/processor/sql.py

import re

# 仅允许 SELECT 语句（含 CTE）
_SELECT_ONLY_RE = re.compile(
    r'^\s*(WITH\s+.*?\s+)?SELECT\s',
    re.IGNORECASE | re.DOTALL,
)

def _is_read_only_sql(sql: str) -> bool:
    """Check if SQL is a read-only SELECT statement."""
    stripped = sql.strip().rstrip(';').strip()
    return bool(_SELECT_ONLY_RE.match(stripped))

class SqlProcessor(BaseProcessor):
    def execute(self, context: PipelineContext) -> None:
        rendered_sql = self._render_template(context)
        
        # 对真实数据库连接（非 SQLite 临时库）强制只读
        if not context.db_is_temp and not _is_read_only_sql(rendered_sql):
            raise ValueError(
                "出于安全考虑，连接真实数据库时仅允许 SELECT 查询。"
                "如需写入，请使用 CSV/Excel 输出方式。"
            )
        
        context.db.execute(rendered_sql)
```

方案 B：在数据库连接配置中增加"只读模式"选项，默认开启

- 在 `ConnectionConfig` 模型中增加 `read_only: bool = True` 字段
- 连接真实数据库时，使用只读事务 (`SET TRANSACTION READ ONLY`)
- 用户明确需要写操作时，需手动关闭只读模式

---

### B-2/B-3/B-4. 路径遍历 — API 路径参数缺少 ID 验证

**问题文件**:
- `configforge/api/connections.py` 第72、82、97、112行 — `conn_id` 未校验
- `configforge/api/executions.py` 第162、172、190行 — `exec_id` 未校验
- `configforge/api/schedules.py` 第70、88、97行 — `schedule_id` 未校验

**现状**: 项目已有 `validate_id()` 函数（`configforge/utils/security.py`），且 `configs.py` 中已使用。但上述三个模块的路径参数未调用该校验，攻击者可构造 `../../../etc/passwd` 等路径遍历字符串。

**修复方案**: 在每个端点的开头添加 `validate_id()` 调用

```python
# configforge/api/connections.py
from configforge.utils.security import validate_id

@router.get("/{conn_id}")
async def get_connection(conn_id: str):
    validate_id(conn_id, "conn_id")  # 新增
    ...

@router.put("/{conn_id}")
async def update_connection(conn_id: str, ...):
    validate_id(conn_id, "conn_id")  # 新增
    ...

@router.delete("/{conn_id}")
async def delete_connection(conn_id: str):
    validate_id(conn_id, "conn_id")  # 新增
    ...

@router.post("/{conn_id}/test")
async def test_connection(conn_id: str):
    validate_id(conn_id, "conn_id")  # 新增
    ...
```

```python
# configforge/api/executions.py
from configforge.utils.security import validate_id

@router.get("/{exec_id}")
async def get_execution(exec_id: str):
    validate_id(exec_id, "exec_id")  # 新增
    ...

@router.get("/{exec_id}/download")
async def download_execution(exec_id: str):
    validate_id(exec_id, "exec_id")  # 新增
    ...

@router.delete("/{exec_id}")
async def delete_execution(exec_id: str):
    validate_id(exec_id, "exec_id")  # 新增
    ...
```

```python
# configforge/api/schedules.py
from configforge.utils.security import validate_id

@router.put("/{schedule_id}")
async def update_schedule(schedule_id: str, ...):
    validate_id(schedule_id, "schedule_id")  # 新增
    ...

@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    validate_id(schedule_id, "schedule_id")  # 新增
    ...

@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    validate_id(schedule_id, "schedule_id")  # 新增
    ...
```

---

### B-5. 无认证/授权机制

**问题文件**: `configforge/server.py`

**现状**: 整个应用无任何认证机制。所有 API 端点（包括数据库连接管理、AI 密钥配置、pipeline 执行）完全开放。

**修复方案**:

方案 A（推荐）：基于 API Key 的简单认证

```python
# configforge/middleware/auth.py
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

API_KEY = os.environ.get("CONFIGFORGE_API_KEY", "")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 无需认证的路径
        public_paths = ["/", "/health"]
        if not API_KEY or request.url.path in public_paths:
            return await call_next(request)
        
        # 检查 API Key
        key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "code": "AUTH_FAILED"},
            )
        
        return await call_next(request)

# configforge/server.py
from configforge.middleware.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)
```

使用方式：
- 启动时设置环境变量 `CONFIGFORGE_API_KEY=your-secret-key`
- 前端请求时在 header 中携带 `X-API-Key`
- 不设置 `CONFIGFORGE_API_KEY` 则不启用认证（开发模式）

方案 B：Basic Auth

- 适合单用户场景
- 用户名/密码通过环境变量配置
- 前端在 axios/fetch 中自动处理

---

### B-6. 数据库密码明文暴露在连接字符串中

**问题文件**: `configforge/services/connection_store.py` 第131-145行

**现状**: `build_connection_string` 将解密后的密码直接拼接到 URL 中（如 `mysql://user:password@host/db`）。异常发生时，包含密码的连接字符串可能出现在日志、错误消息或 API 响应中。

**修复方案**:

1. 日志中统一过滤连接字符串

```python
# configforge/utils/log_filter.py
import re

def sanitize_connection_string(text: str) -> str:
    """Mask passwords in connection strings within log text."""
    return re.sub(
        r'(mysql|postgresql|mongodb)://([^:]+):([^@]+)@',
        r'\1://\2:***@',
        text
    )
```

2. 使用 SQLAlchemy `URL.create()` 避免密码出现在字符串中

```python
# configforge/services/connection_store.py
from sqlalchemy import URL

def create_connection_url(config: dict) -> URL:
    """Create SQLAlchemy URL without exposing password as string."""
    return URL.create(
        drivername=config.get("driver", "mysql+pymysql"),
        username=config.get("user", ""),
        password=config.get("password", ""),  # 不拼接到字符串
        host=config.get("host", "localhost"),
        port=config.get("port"),
        database=config.get("database", ""),
    )
```

3. 在异常处理中过滤连接字符串

```python
try:
    engine = create_engine(url)
    engine.connect()
except Exception as e:
    # 过滤错误信息中的连接字符串
    safe_msg = sanitize_connection_string(str(e))
    raise ConnectionError(safe_msg)
```

---

## 二、HIGH 级别（重大功能缺失 / 严重 UX 问题）

### H-1. 文件操作竞态条件 — scheduler 和 executions 模块

**问题文件**:
- `configforge/scheduler.py` 第36-46行
- `configforge/api/executions.py` 第48-73行

**现状**: `schedules.json` 和 `executions/index.json` 的读写操作没有使用文件锁，而 `configs/index.json` 和 `db_connections.json` 已经使用了 `fcntl.flock`。并发写入时可能导致数据丢失或文件损坏。

**修复方案**: 统一使用 `fcntl.flock` 保护所有 JSON 文件操作

```python
# configforge/utils/file_lock.py
import fcntl
import json
from contextlib import contextmanager
from typing import Any

@contextmanager
def file_lock(lock_path: str):
    """Acquire an exclusive file lock."""
    lock_fd = open(lock_path + ".lock", "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield lock_fd
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

def read_json_locked(path: str) -> Any:
    """Read JSON file with shared lock."""
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def write_json_locked(path: str, data: Any) -> None:
    """Write JSON file with exclusive lock."""
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

然后在 `scheduler.py` 和 `executions.py` 中替换所有 JSON 读写操作。

---

### H-2. 文件上传整个读入内存

**问题文件**: `configforge/api/files.py` 第78行

**现状**: `content = await file.read()` 将整个文件读入内存。50MB 限制下，并发上传可能导致内存溢出。

**修复方案**: 使用流式写入

```python
# configforge/api/files.py
import shutil

@router.post("/upload")
async def upload_file(file: UploadFile):
    file_id = uuid.uuid4().hex
    dest = os.path.join(UPLOAD_DIR, file_id)
    
    # 流式写入，避免整个文件读入内存
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
    
    return {"file_id": file_id, "filename": file.filename}
```

---

### H-3. SQL 预览基于样本数据，结果与实际不一致

**问题文件**: `configforge/api/preview.py` 第139行

**现状**: 仅将 `sample_rows` 插入内存 SQLite，SQL 预览结果可能与实际执行结果差异巨大（如聚合查询在 5 行样本上无意义）。

**修复方案**:

1. 在预览界面明确提示（前端）

```vue
<!-- 在 SQL 预览结果区域添加提示 -->
<NAlert type="info" :bordered="false" class="mb-2">
  预览基于前 {{ sampleRows }} 行样本数据，结果可能与实际执行不同
</NAlert>
```

2. 在预览 API 响应中增加元数据（后端）

```python
return {
    "columns": columns,
    "rows": rows,
    "total_source_rows": info.get("total_rows", 0),
    "sample_rows_loaded": len(info.get("sample_rows", [])),
    "is_sampled": True,  # 标记为样本数据
}
```

---

### H-4. 前端大量使用 `any` 类型

**问题文件**: 多个前端文件（共 44 处 `: any`）

**修复方案**: 分批替换，优先处理 API 层

```typescript
// configforge-web/src/types/api.ts — 新增 API 响应类型

export interface ConfigListResponse {
  items: SavedConfig[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ExecutionListResponse {
  items: ExecutionSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface WizardStateResponse {
  scene: { name: string; version: string; description: string }
  inputs: InputSourceResponse[]
  processors: ProcessorConfigResponse[]
  output: OutputConfigResponse
}

export interface InputSourceResponse {
  name: string
  plugin: string
  table: string
  param_key: string
  file_id: string
  config: Record<string, unknown>
}
```

然后在 `useConfigApi.ts` 和 `useWizardApi.ts` 中替换 `any` 为具体类型。

---

### H-5/H-6. 执行历史/定时任务视图缺少分页

**问题文件**:
- `configforge-web/src/views/ExecutionHistoryView.vue`
- `configforge-web/src/views/SchedulesPage.vue`

**修复方案**: 参照 `HomeView.vue` 的分页实现，添加分页控件

```vue
<!-- ExecutionHistoryView.vue 增加分页 -->
<div class="flex items-center justify-between mt-4">
  <span class="text-xs text-slate-400">共 {{ total }} 条</span>
  <NPagination
    v-model:page="currentPage"
    :page-count="totalPages"
    :page-size="pageSize"
    size="small"
    @update:page="refresh"
  />
</div>
```

后端已支持分页参数（`page`、`page_size`），只需前端传参。

---

### H-7. SQL 预览 DDL/DML 过滤可被绕过

**问题文件**: `configforge/api/preview.py` 第51-54行、第160-166行

**现状**:
1. `PRAGMA query_only=ON` 在数据加载之后才设置，`CREATE TABLE` 和 `INSERT` 在非只读模式下执行
2. DDL/DML 正则不覆盖 `REPLACE INTO`、`ANALYZE`、`PRAGMA` 等语句

**修复方案**:

1. 将 `PRAGMA query_only=ON` 移到数据加载之前

```python
# preview.py — 修改执行顺序
conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA query_only=ON")  # 先设置只读

# 然后用另一个连接加载数据
load_conn = sqlite3.connect(":memory:")
# ... 加载 sample_rows 到 load_conn ...

# 将数据从 load_conn 附加到只读 conn
# 或者：先加载数据，再设置 query_only
```

注意：SQLite 的 `query_only` 会阻止 `CREATE TABLE` 和 `INSERT`，所以需要在数据加载完成后再设置。更好的方案是：

```python
# 先加载数据（需要写权限）
conn = sqlite3.connect(":memory:")
for table_name, rows in sample_data.items():
    conn.execute(f"CREATE TABLE [{table_name}] (...)")
    conn.executemany(f"INSERT INTO [{table_name}] VALUES (...)", rows)

# 数据加载完成后设置只读
conn.execute("PRAGMA query_only=ON")

# 此后所有用户 SQL 只能 SELECT
```

2. 扩展 DDL/DML 正则

```python
_DDL_DML_RE = re.compile(
    r'\b(ALTER|ANALYZE|ATTACH|BEGIN|COMMIT|CREATE|DELETE|DETACH|DROP|INSERT|'
    r'PRAGMA|REINDEX|RELEASE|REPLACE|ROLLBACK|SAVEPOINT|UPDATE|VACUUM)\b',
    re.IGNORECASE,
)
```

---

### H-8. CORS 配置过于宽松

**问题文件**: `configforge/server.py` 第48-54行

**修复方案**: 收紧 CORS 配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        os.environ.get("CONFIGFORGE_ORIGIN", ""),  # 生产环境域名
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 限制方法
    allow_headers=["Content-Type", "X-API-Key"],     # 限制头
)
```

---

### H-9. 废弃的 Step 视图文件未清理

**问题文件**: `configforge-web/src/views/Step1SceneView.vue` ~ `Step5ExportView.vue`

**现状**: 路由已重定向到 `/config/new`，这些文件不再被使用。

**修复方案**: 删除以下文件
- `Step1SceneView.vue`
- `Step2InputView.vue`
- `Step3ProcessView.vue`
- `Step4OutputView.vue`
- `Step5ExportView.vue`

同时清理 `router/index.ts` 中对应的路由定义。

---

## 三、MEDIUM 级别（质量改进 / 边界情况处理）

### M-1/M-2. state.json 读写无文件锁

**问题文件**: `configforge/api/configs.py` 第150-155行、第232-234行

**修复方案**: 使用 H-1 中定义的 `read_json_locked` / `write_json_locked` 函数

---

### M-3. deepdiff 未在 requirements 中声明

**问题文件**: `configforge/api/configs.py` 第464行

**修复方案**: 在 `pyproject.toml` 或 `requirements.txt` 中添加 `deepdiff` 依赖

---

### M-4. WizardState 中 processor/processors 并存

**问题文件**: `configforge/models/wizard.py` 第142-145行

**修复方案**: 
1. 短期：保留 `_migrate_state_dict` 兼容处理
2. 长期：在下一个大版本中移除 `processor` 单数字段，统一使用 `processors`

---

### M-5. 前端 loadFromConfigState 手动字段映射

**问题文件**: `configforge-web/src/stores/wizard.ts` 第144-213行

**修复方案**: 实现统一的 `snakeToCamel` 转换函数

```typescript
// configforge-web/src/utils/transform.ts
export function snakeToCamel(obj: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {}
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
    result[camelKey] = value
  }
  return result
}
```

---

### M-6. useConfigApi 和 useWizardApi 中 post 函数重复

**修复方案**: 提取公共 `useApi` composable

```typescript
// configforge-web/src/composables/useApi.ts
export function useApi() {
  async function post(url: string, body: unknown) {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.error || `Request failed: ${resp.status}`)
    }
    return resp
  }
  // ... get, put, delete
  return { post, get, put, del }
}
```

---

### M-7. 缺少前端错误边界

**修复方案**: 在 `App.vue` 中添加全局错误处理

```typescript
// main.ts
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err, info)
  // 可选：上报到错误追踪服务
}

// 或在 App.vue 中
import { onErrorCaptured } from 'vue'

onErrorCaptured((err, instance, info) => {
  // 显示全局错误提示
  return false // 阻止错误继续传播
})
```

---

### M-8. HomeView 搜索定时器未清理

**问题文件**: `configforge-web/src/views/HomeView.vue` 第325-332行

**修复方案**:

```typescript
import { onUnmounted } from 'vue'

const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)

onUnmounted(() => {
  if (searchTimer.value) clearTimeout(searchTimer.value)
})
```

---

### M-9. ExecutionHistoryView 详情弹窗样式不一致

**修复方案**: 添加 `preset="card"` 使弹窗样式统一

```vue
<NModal v-model:show="detailVisible" preset="card" title="执行详情" style="max-width: 560px">
```

---

### M-10. AI 速率限制基于内存存储

**现状**: 单 worker 场景可接受，多 worker 部署时无效。

**修复方案**: 短期在文档中注明限制；长期考虑 Redis 等共享存储。

---

### M-11. SQLite 文件路径验证不充分

**修复方案**: 限制 SQLite 文件路径必须在特定数据目录下

```python
# configforge/api/connections.py
ALLOWED_SQLITE_DIRS = [
    os.path.abspath("data"),
    os.path.abspath("uploads"),
]

def validate_sqlite_path(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(d) for d in ALLOWED_SQLITE_DIRS)
```

---

### M-12. 表名未校验

**修复方案**: 对 `list_tables` 和 `get_table_columns` 中的 `table` 参数添加 `safe_identifier` 校验

---

### M-13. Pipeline 执行超时未设置

**修复方案**: 使用 `signal.alarm`（Unix）或 `multiprocessing` 实现超时

```python
import signal

class TimeoutError(Exception):
    pass

def _timeout_handler(signum, frame):
    raise TimeoutError("Pipeline execution timed out")

# 在 execute_pipeline 中
signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(300)  # 5分钟超时
try:
    result = engine.execute(params, log_dir=LOG_DIR)
finally:
    signal.alarm(0)
```

---

### M-14. Python 处理器沙箱不完善

**修复方案**: 在文档中明确警告安全风险；长期考虑 `RestrictedPython` 或容器化执行。

---

## 四、LOW 级别（锦上添花 / 代码清理）

### L-1. 前端无障碍性不完整
- 为关键交互元素添加 `aria-label`
- 模态弹窗添加焦点陷阱

### L-2. 移动端响应式部分缺失
- `ExecutionHistoryView.vue` 和 `SchedulesPage.vue` 添加 `@media` 查询

### L-3. GuideView.vue 功能完整性检查
- 审查指南页面内容是否完整

### L-4. 临时文件清理依赖 atexit
- 增加基于时间的定期清理

### L-5. 上传临时文件残留
- 检查 `MAX_FILE_AGE_SECONDS` 配置和清理触发时机

### L-6. 前端 e2e 测试覆盖面极低
- 补充关键流程的 e2e 测试

### L-7. scheduler 模块无单元测试
- 补充 cron 验证、pipeline 执行、状态更新的测试

### L-8. 版本管理端点测试完整性
- 确认版本回滚、diff 的测试覆盖

### L-9. InputSource.name 字段默认为空
- 明确 `name` 用途，统一使用 `table` 字段

### L-10. infer_output 函数硬编码返回空列
- 实现输出推断逻辑或移除该 API 端点

---

## 五、实施优先级总览

| 阶段 | 内容 | 涉及项 | 预计影响范围 |
|------|------|--------|-------------|
| **第一阶段** | 安全加固 | B-1 ~ B-6 | 后端 6 个文件 |
| **第二阶段** | 数据安全与稳定性 | H-1, H-2, H-7, H-8, M-1 ~ M-3, M-13 | 后端 5 个文件 + 中间件 |
| **第三阶段** | 功能完善 | H-3 ~ H-6, H-9, M-4 ~ M-9 | 前端 8 个文件 |
| **第四阶段** | 质量提升 | M-10 ~ M-14, L-1 ~ L-10 | 前后端多个文件 |
