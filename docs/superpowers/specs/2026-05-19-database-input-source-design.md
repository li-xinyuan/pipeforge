# v0.2.1 — 数据库输入源 设计文档

> 日期: 2026-05-19
> 方案: B — 连接注册中心 + 引用
> 审查: 2026-05-13 v1（P1-P7 + 3 轻微建议）→ 已修正
> 审查: 2026-05-13 v2（N1-N7）→ 已修正

## 一、目标

支持从外部数据库（SQLite / MySQL / PostgreSQL）加载数据作为管道输入源，业务用户无需每次手动上传文件即可创建定期报表管道。

## 二、设计原则

| 原则 | 应用 |
|------|------|
| 策略模式 | InputSourceCard 根据 plugin 类型切换不同表单组件（ExcelForm / CsvForm / DatabaseForm） |
| 适配器模式 | SQLAlchemy 屏蔽三种数据库差异，统一接口 |
| 工厂方法 | ConnectionFactory 根据连接配置创建 SQLAlchemy Engine |
| 仓库模式 | ConnectionStore 封装连接持久化、加密、CRUD |
| 高内聚低耦合 | 连接管理和管道配置各自独立，通过 connectionId 关联 |

## 三、架构分层

```
表示层 (Vue Components)
├── ConnectionManager.vue    新增：连接管理（嵌入 SettingsPage）
├── DatabaseForm.vue          新增：数据库输入表单（策略模式）
├── TableBrowser.vue          新增：表列表 + 列预览
├── InputSourceCard.vue      修改：根据 plugin 切换表单
├── InputSourceList.vue      修改：addInput 支持 'database'
└── SettingsPage.vue         修改：嵌入 ConnectionManager

领域层 (Stores)
├── dbConnections.ts         新增：连接 CRUD + 测试（仓库模式）
└── wizard.ts                修改：InputSource 扩展 database 字段

基础设施层 (PipeForge Engine)
├── plugins/input/database.py 新增：数据库输入插件
├── config/models.py          修改：新增 DbInputConfig
└── plugins/base.py           不变：复用 InputPlugin 基类
```

## 四、ConnectionStore 持久化格式（修复 N2）

ConnectionStore 持久化到 `data/db_connections.json`，与 AI Settings（`data/ai_settings.json`）同目录，文件结构：

```json
{
  "connections": {
    "<connection-id>": {
      "id": "<connection-id>",
      "name": "公司财务库",
      "db_type": "mysql",
      "host": "10.0.1.5",
      "port": 3306,
      "database": "finance",
      "username": "report_user",
      "password": "<Fernet-encrypted>",
      "created_at": "2026-05-19T10:00:00",
      "updated_at": "2026-05-19T10:00:00"
    }
  }
}
```

- 密码字段使用与 AI Settings 相同的 `_get_cipher()` 加密
- 每次保存时做文件锁（`fcntl.flock`）防并发写入冲突
- API 返回时密码字段始终脱敏（只返回 `passwordSet: true/false`）

## 五、数据模型

### 前端类型

```typescript
type DbType = 'sqlite' | 'mysql' | 'postgresql'

// 使用 discriminated union，每种数据库类型有独立的字段集（修复 P3）
type DbConnection =
  | {
      id: string
      name: string           // 别名，如 "公司财务库"
      dbType: 'sqlite'
      filePath: string        // SQLite 文件路径
      createdAt: number
      updatedAt: number
    }
  | {
      id: string
      name: string
      dbType: 'mysql' | 'postgresql'
      host: string
      port: number
      database: string
      username: string
      password: string        // 明文密码，仅内存中使用，不持久化
      createdAt: number
      updatedAt: number
    }

// 连接存储在前端的脱敏表示（从 API 返回，密码已脱敏）
interface DbConnectionSummary {
  id: string
  name: string
  dbType: DbType
  // 扁平化展示字段，含义因 dbType 而异：
  //   sqlite → 文件路径（如 /data/report.db）
  //   mysql / postgresql → 主机名或 IP
  host: string
  port?: number
  database?: string
  username?: string
  passwordSet: boolean       // 是否已设置密码（true = 服务端已有加密密码）
  verified: boolean          // 连通性是否已验证（仅保存未测试 → false）
  createdAt: number
  updatedAt: number
}

// InputSource 扩展
interface InputSource {
  plugin: 'excel' | 'csv' | 'database'
  table: string
  paramKey: string
  fileId: string              // excel/csv 用
  connectionId: string        // database 用
  queryType: 'table' | 'sql'
  sqlQuery: string            // 自定义 SQL
  selectedTables: string[]
  config: ExcelInputConfig | CsvInputConfig | DbInputConfig
  confirmedAnalysis?: ConfirmedAnalysis
}

// 多表策略：一个 InputSource 只对应一个源表（tables 最多 1 个元素）
// 需要多表数据 → 添加多个 database 类型 InputSource，或用 queryType='sql' 写 JOIN
interface DbInputConfig {
  type: 'database'
  connectionId: string
  queryType: 'table' | 'sql'
  tables: string[]    // max 1 element when queryType='table'
  sql: string
}
```

### Python 模型

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Annotated, Literal

class DbInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    db_type: str
    connection_string: str      # API 层在调用引擎前解析 connectionId → 拼完整连接串
    tables: list[str] = []   # 最多 1 个元素，多表需求用多个 InputSource 或 SQL JOIN
    sql: str = ""

    # 互斥验证（修复 P5）
    @model_validator(mode="after")
    def validate_tables_sql_mutual_exclusion(self):
        has_tables = len(self.tables) > 0
        has_sql = bool(self.sql.strip())
        if has_tables and has_sql:
            raise ValueError("tables 和 sql 互斥，只能二选一")
        if not has_tables and not has_sql:
            raise ValueError("tables 和 sql 必须提供一个")
        return self

class InputSpec(BaseModel):
    config: Annotated[
        ExcelInputConfig | CsvInputConfig | DbInputConfig,
        Field(discriminator="type")
    ]
```

### 前后端模型映射（修复 N3）

前端 `DbInputConfig` 和 Python `DbInputConfig` 字段不完全一致，API 层负责转换：

```
前端提交 (TS)                          API 转换后 (Python)
┌─────────────────────────┐           ┌──────────────────────────────┐
│ connectionId: "abc123"  │──┐        │ db_type: "mysql"             │
│ queryType: "table"      │  │        │ connection_string: "mysql://"│
│ tables: ["users"]       │  │  API   │ tables: ["users"]            │
│ sql: ""                 │  │ ────→  │ sql: ""                      │
│ type: "database"        │  │ 查询   │ type: "database"             │
└─────────────────────────┘  │ Store  └──────────────────────────────┘
                             │
                    ┌────────┘
                    │ 1. connectionId → ConnectionStore 查连接
                    │ 2. 解密密码 → 拼完整 connection_string
                    │ 3. db_type 从连接配置中提取
                    │ 4. queryType 用于前端 UI 切换，互斥验证后不需传递
                    └────────────────
```

- `connectionId` → API 层解析为 `db_type` + `connection_string`（前端不感知）
- `queryType` → 前端 UI 切换，验证后决定使用 `tables` 还是 `sql`
- API 传给引擎的始终是完整 Python `DbInputConfig`

## 六、数据流

### 5.1 连接创建与管理

```
创建连接:
  前端 ConnectionManager → API POST /api/connections
    → 连通测试可选：可选择 "保存并测试" 或 "仅保存"
    → "仅保存"：连接标记为 "未验证"（unverified），后续使用前可再测试
    → 密码用 Fernet 加密（复用 _get_cipher()）→ 存服务端 ConnectionStore
    → API 返回脱敏连接信息（密码字段返回是否已设置 + 验证状态）

列出连接:
  前端 ConnectionManager → API GET /api/connections
    → 返回脱敏连接列表（不含密码明文，passwordSet: true/false）

更新密码:
  前端输入新密码 → API PUT /api/connections/{id}
    → 重新加密存储

删除连接:
  前端请求删除 → API 检查引用计数（修复 P6）
    → 有引用：返回被哪些管道引用，前端弹确认框
    → 无引用/确认删除：删除连接配置
```

### 5.2 管道配置

```
Step 2 → 选 database → DatabaseForm
  → 从 API GET /api/connections 拉连接列表（脱敏）
  → 选已有连接 / 新建连接
  → POST /api/connections/{id}/test 测试连通
  → POST /api/connections/{id}/tables 加载表列表
  → 选表或写 SQL
```

### 5.3 管道执行 — connectionId → connection_string 转换流程（修复 P2）

```
1. 前端提交管道执行请求 → API 收到 InputSpec（config 含 connectionId）
2. API 从 ConnectionStore 查询连接 → Fernet 解密密码 → 拼完整 connection_string
3. API 将 connection_string 写入 DbInputConfig.connection_string
4. API 将 DbInputConfig 传给 PipelineEngine
5. Engine 执行时直接使用 connection_string 创建 SQLAlchemy Engine → 执行查询
6. 引擎将查询结果写入 SQLite → 后续流程不变
```

```
管道执行:
  ExportActions → API → PipelineEngine → DatabaseInputPlugin
    → ConnectionFactory 创建 SQLAlchemy Engine
    → 执行 SELECT → 写入 SQLite → 后续流程不变
```

## 六、API 端点定义（修复 P4）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/connections` | POST | 创建连接（接收明文密码，服务端加密存储） |
| `/api/connections` | GET | 列出所有连接（密码脱敏，返回 passwordSet 布尔值） |
| `/api/connections/{id}` | GET | 获取单个连接详情（密码脱敏） |
| `/api/connections/{id}` | PUT | 更新连接（可更新密码，新密码覆盖旧加密值） |
| `/api/connections/{id}` | DELETE | 删除连接（先检查引用计数，有引用返回 409） |
| `/api/connections/{id}/test` | POST | 测试数据库连通性（默认 10s 超时，可配置，返回连接状态） |
| `/api/connections/{id}/tables` | GET | 获取数据库中的表列表 |
| `/api/connections/{id}/tables/{table}/columns` | GET | 获取指定表的列信息 |

## 七、关键决策

| 决策 | 理由 |
|------|------|
| 管道 YAML 只存 connectionId | 连接细节不泄露到配置文件中，修改连接不影响已有管道 |
| 密码服务端 Fernet 加密 | 复用现有 `_get_cipher()` 机制，密钥存服务端文件系统，真正安全 |
| 连接串 API 层拼接 | 引擎不感知连接注册中心，拿到的始终是完整 DbInputConfig |
| 数据实时拉取不缓存 | 定期报表数据总在变化 |
| tables 和 sql 互斥 | 二选一，Pydantic model_validator 强制验证 |
| 连接被删除前检查引用 | 删除时查询引用计数，有引用时前端确认，避免执行时才发现 |
| 前端连接密码不落地 | 密码仅在创建/更新时经前端传递到 API，API 返回脱敏信息 |
| 连接被删除后管道报明确错误 | 用户知道是连接问题，不是 SQL 问题 |

## 八、addInput('database') 默认配置（修复 P7）

```typescript
// wizard.ts addInput 扩展
addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
  const base: InputSource = {
    plugin,
    table: '',
    paramKey: '',
    fileId: '',
    connectionId: '',      // 用户选择连接后填充
    queryType: 'table',    // 默认选表模式
    sqlQuery: '',
    selectedTables: [],
    config: plugin === 'database'
      ? { type: 'database', connectionId: '', queryType: 'table', tables: [], sql: '' }
      : { /* 现有逻辑 */ },
  }
  // ...
}

// loadFromConfigState 反序列化 database 类型
// InputSource 的 config 通过 discriminated union 自动匹配 DbInputConfig
```

## 九、错误处理

| 场景 | 处理 |
|------|------|
| 连接失败 | 红色提示 + 具体原因（超时/认证/库不存在） |
| 连接未验证 | 使用时提示 "该连接尚未验证，请先测试连通性"，允许跳过 |
| 连接超时 | 默认 10s 超时，可在连接配置中自定义，支持重试 |
| 表列表加载失败 | 不阻断，允许手动输入表名或写 SQL |
| 密码解密失败 | 提示重新配置连接 |
| 表不存在 | 引擎报错，提示检查表名 |
| SQL 语法错误 | 返回完整 SQL 错误信息 |
| tables 和 sql 同时提供 | Pydantic 验证直接拒绝，返回明确错误 |
| 空表/空结果 | 允许通过，管道继续执行 |
| 连接被删除 | 删除时检查引用，有引用时弹确认框；执行时提示 "连接不存在，请重新配置" |
| 旧管道兼容 | 完全兼容，不受影响 |

## 十、安全

- 密码服务端 Fernet 加密存储（复用 `services/ai/settings.py` 的 `_get_cipher()`，密钥存服务端文件系统）
- 前端不持久化密码（仅在创建/更新连接时经内存传递，API 返回脱敏信息）
- 连接串仅服务端使用，API 不返回给前端
- YAML 配置文件不含连接细节（只存 connectionId）
- SQL 注入防护：已有 validator 阻断 DROP/DELETE 等危险语句
- SQLite 路径校验：API 层验证 `filePath` 为有效 SQLite 文件（检查文件头 `SQLite format 3`），拒绝非数据库文件

## 十一、依赖与配置

| 项目 | 说明 |
|------|------|
| SQLAlchemy | `pyproject.toml` 添加 `sqlalchemy>=2.0` |
| MySQL 驱动 | `pip install pymysql`（可选，按需安装） |
| PostgreSQL 驱动 | `pip install psycopg2-binary`（可选，按需安装） |
| 连接超时 | 默认 10s，可在 ConnectionFactory 中按 dbType 配置 |
| 连接池 | SQLite 禁用连接池（`poolclass=NullPool`），MySQL/PostgreSQL 启用（`pool_size=5`） |

## 十二、不改的部分

- 引擎 `execute()` 主流程不变
- 处理器/输出插件完全不动
- OutputConfigTab / SqlEditorTab 不动
- Step 1/4/5 不动

---

## 审查修正记录

| 问题 | 严重度 | 修正内容 |
|------|--------|----------|
| P1: 密码加密自相矛盾 | 🔴 严重 | 从前端 Fernet 加密改为服务端 Fernet 加密，复用 `_get_cipher()` |
| P2: connectionId 转换流程缺失 | 🔴 严重 | 第 5.3 节新增完整转换流程 |
| P3: SQLite host 字段语义冲突 | 🟡 中等 | DbConnection 使用 discriminated union |
| P4: API 端点未定义 | 🟡 中等 | 第六章新增 8 个 API 端点 |
| P5: 互斥验证规则不明确 | 🟡 中等 | Python 模型新增 model_validator，前端 UI 用 queryType 切换 |
| P6: 缺少连接被引用检查 | 🟡 中等 | 删除流程增加引用检查，有引用时返回 409 |
| P7: addInput 扩展未说明 | 🟡 中等 | 第八章新增默认配置和反序列化说明 |
| 轻微建议 × 3 | ⚪ 轻微 | 第十一章新增依赖、超时、连接池配置 |
| N1: 超时数据不一致 | 🟡 中等 | 第六章 API 端点描述统一为 10s |
| N2: ConnectionStore 存储格式 | 🟡 中等 | 第四章新增持久化格式说明（JSON 文件 + 文件锁） |
| N3: 前后端模型映射 | 🟡 中等 | 第 5.6 节新增映射转换说明 |
| N4: 多表处理策略 | 🟡 中等 | tables 限定 1 个元素，多表用多个 InputSource 或 JOIN |
| N5: Summary host 歧义 | 🟢 轻微 | 改进注释，区分 SQLite/MySQL/PostgreSQL 含义 |
| N6: SQLite 路径安全 | 🟢 轻微 | 安全章节新增文件头校验说明 |
| N7: 连通测试可选 | 🟢 轻微 | 创建流程支持 "仅保存"（标记未验证），DbConnectionSummary 新增 verified 字段 |
