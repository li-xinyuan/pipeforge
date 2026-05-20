# v0.2.1 数据库输入源设计审查报告（第二轮）

> **审查日期**: 2026-05-13  
> **审查文档**: `2026-05-19-database-input-source-design.md`  
> **对照**: 第一轮审查 P1-P7 + 3 轻微建议的修正情况

---

## 一、第一轮问题修正验证

| # | 问题 | 修正情况 | 结论 |
|---|------|----------|------|
| P1 | 密码加密自相矛盾 | ✅ 改为服务端 Fernet 加密，前端不持久化密码 | ✅ 已修复 |
| P2 | connectionId 转换流程缺失 | ✅ 第 5.3 节新增完整 6 步转换流程 | ✅ 已修复 |
| P3 | SQLite host 字段语义冲突 | ✅ DbConnection 使用 discriminated union | ✅ 已修复 |
| P4 | API 端点未定义 | ✅ 第六章新增 8 个 API 端点 | ✅ 已修复 |
| P5 | 互斥验证规则不明确 | ✅ Python model_validator + 前端 queryType 切换 | ✅ 已修复 |
| P6 | 缺少连接被引用检查 | ✅ 删除时检查引用，有引用返回 409 | ✅ 已修复 |
| P7 | addInput 扩展未说明 | ✅ 第八章新增默认配置和反序列化说明 | ✅ 已修复 |
| 轻微1 | SQLAlchemy 依赖 | ✅ 第十一章列出依赖 | ✅ 已修复 |
| 轻微2 | 连接超时可配置 | ✅ 默认 10s，可自定义 | ✅ 已修复 |
| 轻微3 | 连接池区分 | ✅ SQLite NullPool，MySQL/PG pool_size=5 | ✅ 已修复 |

**第一轮 10 项问题全部已修正。**

---

## 二、新发现的问题

### 🟡 N1: 连接测试超时数据不一致

**位置**: 第六章 L203 vs 第九章 L250 vs 第十一章 L275

| 位置 | 超时值 |
|------|--------|
| 第六章 API 端点表 | "超时 **5s**" |
| 第九章 错误处理表 | "默认 **10s** 超时" |
| 第十一章 依赖配置表 | "默认 **10s**" |

**建议**: 统一为 10s，修改第六章 API 端点表中的描述。

---

### 🟡 N2: ConnectionStore 持久化存储格式未说明

**位置**: 第五章 L148 "存服务端 ConnectionStore"

**问题**: 设计文档多次提到 ConnectionStore，但没有说明：
- 数据存储在哪里？（JSON 文件？SQLite 数据库？与 AI settings 同目录？）
- 文件名和路径是什么？
- 是否复用 `data/` 目录（与 AI settings 一致）？

**建议**: 补充一段说明，如：
```
ConnectionStore 持久化到 data/db_connections.json，
与 AI settings (data/ai_settings.json) 同目录，
使用相同的 _get_cipher() 加密密码字段。
```

---

### 🟡 N3: DbInputConfig 前后端字段不完全对应

**问题**: Python 模型 `DbInputConfig` 有 `db_type` 和 `connection_string` 字段，但前端 `DbInputConfig` 没有这两个字段：

| 字段 | 前端 TS | Python | 说明 |
|------|---------|--------|------|
| `type` | ✅ | ✅ | 一致 |
| `connectionId` | ✅ | ❌ | Python 无此字段 |
| `db_type` | ❌ | ✅ | 前端无此字段 |
| `connection_string` | ❌ | ✅ | 前端无此字段 |
| `queryType` | ✅ | ❌ | Python 无此字段 |
| `tables` | ✅ | ✅ | 一致 |
| `sql` | ✅ | ✅ | 一致 |

**分析**: 这是因为 API 层负责转换（connectionId → connection_string），前后端模型确实不需要完全一致。但设计文档没有明确说明这个转换映射关系，开发时容易混淆。

**建议**: 补充一段"前后端模型映射"说明：

```
前端 → API 提交:
  DbInputConfig { connectionId, queryType, tables, sql }
    ↓ API 层转换
  Python DbInputConfig { db_type, connection_string, tables, sql }
    - connectionId → 查询 ConnectionStore → 填充 db_type + connection_string
    - queryType → 决定使用 tables 还是 sql（已在互斥验证中处理）
```

---

### 🟡 N4: queryType='table' + 多表时的 SQL 生成逻辑未说明

**问题**: `tables: list[str]` 可以包含多个表名（如 `['users', 'orders']`），但设计文档没有说明：
- 多表时，每个表各生成一条 `SELECT * FROM {table}` 并各写入一个 SQLite 表？
- 还是所有表的数据合并写入同一个 SQLite 表？
- 如果各写各的，那 `InputSpec.table` 字段只能指定一个目标表名，多表时如何处理？

**建议**: 明确多表处理策略。推荐方案：
- 一个 `InputSpec` 只对应一个源表（`tables` 限制为 `list[str]` 但 `max_length=1`）
- 如果需要多个表，用户添加多个 database 类型的 InputSource
- 或者 `queryType='sql'` 时用 JOIN 查询合并多表

---

### 🟢 N5: DbConnectionSummary 的 host 字段仍有语义歧义

**位置**: 第四节 L77 `host: string // SQLite 为 filePath`

**问题**: `DbConnection` 已经用 discriminated union 解决了 SQLite/MySQL 字段差异，但 `DbConnectionSummary` 仍然用单一 `host` 字段同时表示主机名和文件路径。

**建议**: 虽然 Summary 是扁平化展示可以接受，但建议将注释改为更明确的说明，或也使用 discriminated union。

---

### 🟢 N6: SQLite 文件路径安全未考虑

**问题**: SQLite 连接的 `filePath` 可以是任意文件路径，存在路径遍历风险（如 `/etc/passwd` 虽然不是 SQLite 文件但会报错泄露信息）。

**建议**: 在 API 层对 SQLite filePath 做基本校验：
- 限制在允许的目录范围内
- 或至少验证文件是有效的 SQLite 文件（检查文件头 `SQLite format 3`）

---

### 🟢 N7: 连接创建时是否必须测试连通

**位置**: 第五章 L147-148 "服务端校验连通性"

**问题**: 创建连接时强制测试连通，如果目标数据库暂时不可用，用户就无法保存连接配置。

**建议**: 连通测试作为可选步骤。创建连接时允许保存未验证的配置，但标记为"未验证"，在使用时再测试。

---

## 三、评分

| 维度 | 第一轮评分 | 本轮评分 | 变化 |
|------|-----------|----------|------|
| 架构兼容性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — |
| 数据模型 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | — |
| 安全设计 | ⭐⭐⭐ | ⭐⭐⭐⭐½ | ↑ 服务端加密方案正确 |
| API 设计 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ↑ 端点已定义 |
| 数据流完整性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ↑ 转换流程已补充 |
| 内部一致性 | — | ⭐⭐⭐⭐ | 新增维度，超时数据不一致 |

---

## 四、结论

第一轮 **10 项问题全部已修正**，设计质量显著提升。

本轮新发现 **4 个中等问题 + 3 个轻微问题**，均为细节层面，不影响整体架构方向：

| 级别 | 数量 | 关键项 |
|------|------|--------|
| 🟡 中等 | 4 | 超时数据不一致、ConnectionStore 存储格式、前后端模型映射、多表处理策略 |
| 🟢 轻微 | 3 | Summary host 歧义、SQLite 路径安全、连通测试可选 |

**建议**: 修复 N1（超时不一致）和 N4（多表策略）后即可进入开发，其余可在开发过程中细化。

---

*审查时间: 2026-05-13*
