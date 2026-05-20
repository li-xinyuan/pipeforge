# v0.2.1 数据库输入源设计审查报告

> **审查日期**: 2026-05-13  
> **审查文档**: `2026-05-19-database-input-source-design.md`  
> **审查范围**: 架构兼容性、数据模型、安全设计、数据流完整性、API 设计

---

## 一、与现有架构的兼容性验证

| 设计点 | 现有代码验证 | 结论 |
|--------|-------------|------|
| `InputPlugin` 基类复用 | `plugins/base.py` L27-30，`table_name` 注入机制完整 | ✅ 完全兼容 |
| `InputSpec` 使用 discriminated union | `models.py` L39 已有 `Annotated[ExcelInputConfig \| CsvInputConfig, Field(discriminator="type")]` | ✅ 扩展为三成员即可 |
| `register_plugin` 注册机制 | `excel.py` L44 `@register_plugin("excel", "input")` | ✅ 新增 `"database"` 即可 |
| `context.db.create_table` + `insert_row` | `excel.py` L54-57 统一写入 SQLite | ✅ 数据库插件同样使用 |
| 前端 `InputSource` 类型 | `wizard.ts` L40-47 已有 `plugin: 'excel' \| 'csv'` | ✅ 扩展为三成员即可 |
| Fernet 加密已有实现 | `settings.py` L11-25 `_get_cipher()` | ✅ 可复用 |

---

## 二、严重问题（2 个）

### 🔴 P1: 密码加密方案自相矛盾

**设计文档描述**：
- 第四节：`password: string // Fernet 加密存储`
- 第六节：`密码 Fernet 加密，密钥存 sessionStorage`
- 第八节：`密码 Fernet 加密存储（localStorage），密钥存 sessionStorage`

**问题**：
- Fernet 是**对称加密**，密钥和密文存在同一浏览器中等于**明文存储**。攻击者只需打开 DevTools 即可同时获取密钥和密文
- 现有 AI API Key 的 Fernet 加密是在**服务端**完成的（`settings.py`），密钥存在服务端文件系统，这是安全的
- 但数据库连接密码设计为**前端加密 + localStorage**，密钥在 sessionStorage，这**没有实际安全价值**

**建议**：
- **方案 A（推荐）**：连接密码存服务端，复用现有 `_get_cipher()` 机制，前端只传明文密码到 API，API 加密后存储
- **方案 B**：如果必须前端存储，直接明文存 localStorage 并明确告知用户风险（本地工具场景下可接受）

---

### 🔴 P2: connectionId → connection_string 转换流程缺失

**设计文档描述**：
- 第四节 Python 模型：`DbInputConfig` 包含 `connection_string: str`
- 第六节：`管道 YAML 只存 connectionId`，`API 层拼连接串`

**问题**：
- 管道执行时 `PipelineEngine` 从 YAML 读取配置，但 YAML 只有 `connectionId`，没有 `connection_string`
- 引擎需要连接串才能创建 SQLAlchemy Engine，但引擎不应该知道连接注册中心的存在
- 设计文档没有说明 **API 层如何将 connectionId 转换为 connection_string 并注入到引擎**

**建议**：
- 推荐方案：API 层在调用引擎前，将 `connectionId` 解析为 `connection_string`，写入 `DbInputConfig`，引擎拿到的始终是完整配置
- 具体流程：
  ```
  1. 前端提交配置 → API 收到 connectionId
  2. API 从 ConnectionStore 查询连接 → 解密密码 → 拼接 connection_string
  3. API 将 connection_string 写入 DbInputConfig → 传给引擎
  4. 引擎执行时直接使用 connection_string
  ```
- 需要在设计文档中补充这个数据转换流程

---

## 三、中等问题（5 个）

### 🟡 P3: SQLite 文件路径与 host 字段语义冲突

**设计文档描述**：`host: string // SQLite 用 filePath`

**问题**：
- `DbConnection` 的 `host` 字段对 SQLite 来说存的是文件路径，对 MySQL/PostgreSQL 来说存的是主机名
- 同一个字段语义完全不同，验证逻辑会变得复杂（SQLite 不需要 port/database/username/password）

**建议**：使用 discriminated union，每种数据库类型有独立的字段集：

```typescript
type DbConnection = 
  | { id: string; name: string; dbType: 'sqlite'; filePath: string; createdAt: number; updatedAt: number }
  | { id: string; name: string; dbType: 'mysql'; host: string; port: number; database: string; username: string; password: string; createdAt: number; updatedAt: number }
  | { id: string; name: string; dbType: 'postgresql'; host: string; port: number; database: string; username: string; password: string; createdAt: number; updatedAt: number }
```

---

### 🟡 P4: 连接管理 API 端点未定义

**设计文档描述**：`测试连通 → 加载表列表 → 选表或写 SQL`

**问题**：设计文档提到了连接测试和表列表加载，但没有定义对应的 API 端点

**建议**：补充 API 端点定义：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/connections` | POST | 创建连接 |
| `/api/connections` | GET | 列出连接（密码脱敏） |
| `/api/connections/{id}` | GET | 获取连接（密码脱敏） |
| `/api/connections/{id}` | PUT | 更新连接 |
| `/api/connections/{id}` | DELETE | 删除连接 |
| `/api/connections/{id}/test` | POST | 测试连通 |
| `/api/connections/{id}/tables` | POST | 获取表列表 |
| `/api/connections/{id}/columns` | POST | 获取表的列信息 |

---

### 🟡 P5: queryType 互斥验证规则不明确

**设计文档描述**：`tables 和 sql 互斥，二选一`

**问题**：
- `DbInputConfig` 同时有 `tables: list[str]` 和 `sql: str`，互斥需要在验证层强制执行
- 没有说明互斥验证的具体规则（选了表后 SQL 清空？还是两者都有时以谁为准？）

**建议**：
- 在 `DbInputConfig` 中添加 Pydantic `@model_validator` 强制互斥
- 在前端用 `queryType: 'table' | 'sql'` 切换 UI，只发送对应字段

---

### 🟡 P6: 缺少连接被引用检查

**设计文档描述**：`连接被删除后管道报明确错误`

**问题**：只在执行时报错太晚了，应该在删除连接时就提示用户"该连接被 N 个管道引用"

**建议**：
- 删除连接前检查已保存配置，如果有引用则弹出确认对话框
- 或者在连接管理页面显示引用计数

---

### 🟡 P7: 前端 addInput 函数扩展未说明

**现状**：`wizard.ts` L37 `addInput(plugin: 'excel' | 'csv' = 'excel')`

**问题**：
- 需要扩展为 `addInput(plugin: 'excel' | 'csv' | 'database')`
- database 类型的默认 config 结构不同（需要 `connectionId`, `queryType` 等）
- `loadFromConfigState` 也需要处理 database 类型的反序列化

**建议**：设计文档应明确 `addInput('database')` 的默认 config 初始值

---

## 四、轻微建议（3 个）

| # | 建议 | 说明 |
|---|------|------|
| 1 | **SQLAlchemy 依赖管理** | 需在 `pyproject.toml` / `requirements.txt` 中添加 SQLAlchemy，且需考虑 MySQL/PostgreSQL 驱动包（`pymysql`, `psycopg2`） |
| 2 | **连接超时可配置** | 5s 对远程数据库可能不够，建议可配置或默认 10s |
| 3 | **连接池区分** | SQLite 不需要连接池，MySQL/PostgreSQL 需要，建议在 `ConnectionFactory` 中区分处理 |

---

## 五、评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构兼容性** | ⭐⭐⭐⭐⭐ | 与现有插件系统完全兼容 |
| **数据模型** | ⭐⭐⭐⭐ | discriminated union 正确，但 SQLite 字段需调整 |
| **安全设计** | ⭐⭐⭐ | 前端 Fernet 加密无实际安全价值 |
| **API 设计** | ⭐⭐⭐ | 缺少连接管理 API 端点定义 |
| **数据流完整性** | ⭐⭐⭐ | connectionId → connection_string 转换流程缺失 |
| **错误处理** | ⭐⭐⭐⭐ | 场景覆盖全面，但缺少删除前引用检查 |

---

## 六、结论

设计方向正确，架构兼容性好，但有 **2 个严重问题需先解决**：

1. **P1 密码加密方案** — 前端 Fernet 加密无实际安全价值，应改为服务端加密存储
2. **P2 connectionId 解析流程** — API 层需在调用引擎前将 connectionId 解析为 connection_string

另有 **5 个中等问题需补充**（SQLite 字段语义、API 端点定义、互斥验证、引用检查、addInput 扩展）。

建议修复严重问题并补充中等问题的设计细节后再进入开发。

---

*审查时间: 2026-05-13*
