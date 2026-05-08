# ConfigForge 设计文档 v1.1 审核

> 审核文档: 2026-05-04-configforge-design-v1.1.md  
> 对比基线: CONFIGFORGE_REVIEW.md (v1.0 审核，15 个问题)  
> 审核日期: 2026-05-03

---

## 一、v1.0 问题修复情况：逐项核验

### P0 问题

| # | v1.0 问题 | v1.1 修复 | 结果 |
|---|----------|----------|------|
| P0-1 | `columns` 错放在 inputs 下 | §3.3 数据流图：`columns` 移入 `output.config`；§6.5 Step 4 YAML 预览中 columns 在 output 下；附录 B 变更清单记录 | ✅ |
| P0-2 | 数据流使用 camelCase | §3.3 标题改为「snake_case 命名」，所有字段改为 `param_key`/`output_tables`/`source_table` 等；明确标注「前端 TS 用 camelCase，yaml_builder 负责转换」 | ✅ |
| P0-3 | §9 SceneConfig 缺少默认值 | §14 补充 `inputs: list[InputSpec] = []`、`processors: list[ProcessorSpec] = []`、`output: OutputSpec \| None = None`；注释说明与 PipeForge models.py:92-98 一致 | ✅ |

### P1 问题

| # | v1.0 问题 | v1.1 修复 | 结果 |
|---|----------|----------|------|
| P1-1 | §2.1 与 §7.1 依赖描述矛盾 | §2.1 改为「复用 PipeForge 的 config.models 作为接口契约；openpyxl 为 ConfigForge 自身依赖」 | ✅ |
| P1-2 | `Map<string, File>` 不可序列化 | §6.4 `uploadedFiles: Record<string, UploadedFileMeta>`、`aiSuggestions: Record<string, AiSuggestion>`；新增 `UploadedFileMeta` 和 `AiSuggestion` 类型定义；文件由 `useFileUpload` 独立管理 | ✅ |
| P1-3 | `source_id` 未定义 | §5.2 API 表改为 `/api/wizard/infer-input/{input_name}`，说明 `input_name` 为 `InputSpec.name`；§6.3 `inferInputConfig` 参数同步修改 | ✅ |
| P1-4 | Step 3 职责过重 | §3.1 Step 3 改为 Tab 分栏（SQL 处理 / 输出配置）；§6.2 组件拆分为 `SqlEditorTab.vue` + `OutputConfigTab.vue`；§6.5 Step 3 布局图展示两个 Tab | ✅ |
| P1-5 | `infer_config(file_path)` 不通用 | §5.1 参数改为 `source: dict`；注释说明三种 source 结构（文件/数据库/API）；§4.3 示例同步修改 | ✅ |
| P1-6 | 缺少 AI 配置管理 | 新增 §7「AI 配置」：Key 管理（环境变量）、提供商可插拔（LlmBackend 接口）、数据发送策略（仅列名+3行样例）、无 AI 模式降级、用户确认机制 | ✅ |

### P2 问题

| # | v1.0 问题 | v1.1 修复 | 结果 |
|---|----------|----------|------|
| P2-1 | 缺少错误处理策略 | 新增 §8「错误处理」：三级分类（warning/error/fatal）、统一响应格式、前端错误组件 | ✅ |
| P2-2 | 缺少状态持久化 | 新增 §9「状态持久化」：localStorage + pinia-plugin-persistedstate（v0.1）、服务端草稿（v0.2） | ✅ |
| P2-3 | 缺少文件上传限制 | §5.2 新增文件上传约束表（50MB / .xlsx/.xls/.csv / v0.3+ 分片） | ✅ |
| P2-4 | 缺少部署方案 | 新增 §10「部署方案」：开发/单进程生产/Docker 三种模式，含 server.py 代码和 docker-compose.yml | ✅ |
| P2-5 | v0.1 目录含未实现文件 | §2.3 只列 v0.1 实际文件；新增注释「扩展文件在 §13 版本路线图中规划」 | ✅ |
| P2-6 | 缺少测试策略 | 新增 §11「测试策略」：测试矩阵 + 后端/前端示例代码 | ✅ |

### 结论

**v1.0 审核中提出的 15 个问题（3 P0 + 6 P1 + 6 P2）在 v1.1 中全部得到解决。** 附录 B 变更清单完整记录了每项修改的位置，便于追溯。

---

## 二、v1.1 新发现的问题

### P1 — 重要问题

#### P1-1: 文件上传端点缺失——`file_id` 的生成没有对应的 API

§5.2 API 表中有 `/api/wizard/init-scene`（接收 `file_ids: string[]`）和 `/api/preview/file`（接收 `File` 对象），但**没有文件上传端点**。

数据流是：
1. 用户在前端选择文件
2. 前端通过 `useFileUpload.upload(file)` 上传 → 获得服务器返回的 `file_id`
3. `file_id` 存入 WizardState 的 `uploadedFiles`
4. 后续 API 调用使用 `file_id` 引用

但步骤 2 对应的上传端点（如 `POST /api/files/upload`）在 API 表中不存在。`/api/preview/file` 是「上传并预览」，但它返回的是 `ColumnPreview`，不是 `file_id`。

**建议**：增加文件上传端点：

| 端点 | 方法 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| `/api/files/upload` | POST | `multipart/form-data` | `{ file_id: string, original_name: string }` | 上传文件到服务器临时目录 |

或者将 `/api/preview/file` 的响应体改为同时返回 `file_id` 和 `ColumnPreview`。

---

#### P1-2: §3.3 数据流中 `uploaded_files` 的结构与 §6.4 WizardState 不一致

§3.3 数据流图：

```
uploaded_files: [
  {file_id, name}
]
```

§6.4 WizardState：

```typescript
uploadedFiles: Record<string, UploadedFileMeta>  // fileId → meta
```

数据流图中 `uploaded_files` 是数组，WizardState 中是 Record（字典）。虽然语义等价，但作为接口定义应保持一致。

**建议**：§3.3 数据流图改为 Record 格式：

```
uploaded_files: {
  "file_abc": { name: "person.xlsx" },
  "file_def": { name: "attendance.xlsx" }
}
```

---

#### P1-3: §7.1 AI 后端目录结构与 §2.3 目录结构不一致

§7.1 提到：

> `services/ai/` 下按提供商分子类（`OpenAIBackend`、`AnthropicBackend`）

但 §2.3 目录结构中 `services/` 下只有：

```
services/
├── excel_reader.py
├── sql_generator.py
├── yaml_builder.py
└── template_builder.py
```

没有 `services/ai/` 目录。

**建议**：在 §2.3 目录结构中补充 `services/ai/` 目录：

```
services/
├── ai/
│   ├── __init__.py
│   ├── base.py              # LlmBackend 抽象基类
│   ├── openai_backend.py    # OpenAI 实现
│   └── anthropic_backend.py # Anthropic 实现
├── excel_reader.py
├── sql_generator.py
├── yaml_builder.py
└── template_builder.py
```

---

### P2 — 建议优化

#### P2-1: §5.2 API 表中 `/api/preview/file` 仍接收 `File` 对象，与「文件先上传」的设计矛盾

§5.2：

> `/api/preview/file` | POST | `{ file: File, sheet?: string }` | `ColumnPreview`

但 v1.1 的设计是「文件先上传到服务器，后续用 file_id 引用」。如果文件已经上传了，预览应该用 `file_id` 而不是重新上传文件。

**建议**：改为：

| 端点 | 请求体 | 说明 |
|------|--------|------|
| `/api/preview/file` | `{ file_id: string, sheet?: string }` | 根据已上传文件的 file_id 返回列预览 |

---

#### P2-2: §6.4 `AiSuggestion` 缺少 `rejected` 状态

§6.4 定义：

```typescript
interface AiSuggestion {
  content: string
  category: "scene" | "columns" | "sql" | "mapping"
  accepted: boolean
  timestamp: number
}
```

`accepted: boolean` 只能表示「已采纳」或「未采纳」，但 AI 建议有三种状态：
1. **待定**：刚生成，等待用户操作
2. **已采纳**：用户点击了「采纳」
3. **已拒绝**：用户点击了「重新生成」（旧建议被拒绝）

如果用户重新生成，旧建议的 `accepted` 应该是 `false`，但「未操作」和「已拒绝」无法区分。

**建议**：改为 `status: "pending" | "accepted" | "rejected"`。

---

#### P2-3: §8 错误处理缺少「文件格式不支持」的错误码

§8.2 后端统一错误响应格式示例是 `SQL_SYNTAX_ERROR`，但 §5.2 文件上传约束中提到「白名单格式 .xlsx/.xls/.csv」。如果用户上传了 .pdf 或 .docx，应该返回什么错误码？

**建议**：补充错误码表，至少包含：

| code | 含义 | recoverable |
|------|------|-------------|
| `FILE_TOO_LARGE` | 文件超过 50MB | true |
| `FILE_FORMAT_UNSUPPORTED` | 文件格式不在白名单中 | true |
| `SQL_SYNTAX_ERROR` | SQL 语法错误 | true |
| `AI_SERVICE_UNAVAILABLE` | AI 服务不可用 | true |
| `INTERNAL_ERROR` | 服务器内部错误 | false |

---

#### P2-4: §10.2 生产模式 `server.py` 的路由挂载顺序可能导致 API 路由被静态文件拦截

§10.2：

```python
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

FastAPI 的 `mount` 会匹配所有以 `/` 开头的路径。如果这行代码在 API 路由注册之后执行，API 路由优先级更高（FastAPI 按注册顺序匹配），没有问题。但如果 `mount` 在 API 路由之前执行，所有 `/api/*` 请求会被静态文件处理拦截。

当前代码注释 `# ... 注册 API 路由 ...` 在 `mount` 之前，所以顺序正确。但建议显式说明这个顺序的重要性。

**建议**：加注释 `# 注意：API 路由必须在 mount 之前注册，否则会被静态文件拦截`。

---

### P3 — 微小问题

#### P3-1: §6.4 `useFileUpload` 中 `removeFile` 和 `clearAll` 只管理前端状态，未调用后端清理

§6.3 `useFileUpload`：

```typescript
function removeFile(fileId: string): void
function clearAll(): void
```

这两个方法只从 `uploadedFiles` 数组中移除引用，但服务器上的临时文件不会被删除。长时间使用会积累大量临时文件。

**建议**：v0.1 可不处理（临时文件可由定时清理任务处理），但建议在 §9 或 §5 中加注说明临时文件的清理策略（如「服务器临时文件 24 小时后自动清理」）。

---

#### P3-2: §11 测试矩阵中「核心逻辑 100%」覆盖目标过高

§11.1：

> 后端单元 | 核心逻辑 100%

100% 覆盖率目标在实际项目中很难达到且维护成本高。建议改为更务实的「≥80%」。

---

## 三、总体评价

### 修复质量

v1.1 对 v1.0 的 15 个问题全部给出了实质性修复，且修复质量很高：
- P0-1/P0-2/P0-3：接口契约问题彻底解决，数据流图与 PipeForge 实际模型完全对齐
- P1-4：Step 3 Tab 分栏是比建议方案更好的设计（保持了 4 步向导的简洁性）
- P1-6：AI 配置章节非常详细，包括数据发送策略和用户确认机制——这超出了我的建议范围
- 新增的 §8/§9/§10/§11 四个章节补全了设计缺失

### 当前版本评估

**v1.1 已经非常接近可进入实现的状态。** 3 个 P1 问题都是细节层面的不一致（缺上传端点、数据流图格式、目录结构），不影响核心架构。

### 新问题优先级汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P1** | P1-1 | 缺少文件上传端点（`POST /api/files/upload`） | API 缺失 |
| **P1** | P1-2 | §3.3 uploaded_files 是数组，§6.4 是 Record，不一致 | 文档不一致 |
| **P1** | P1-3 | §7.1 提到 `services/ai/` 但 §2.3 目录结构中没有 | 目录不一致 |
| **P2** | P2-1 | `/api/preview/file` 仍接收 File 对象，应改为 file_id | API 设计 |
| **P2** | P2-2 | `AiSuggestion.accepted: boolean` 无法区分「待定」和「已拒绝」 | 类型设计 |
| **P2** | P2-3 | 缺少错误码表 | 规范缺失 |
| **P2** | P2-4 | 生产模式路由挂载顺序需显式说明 | 实现细节 |
| **P3** | P3-1 | 临时文件清理策略未说明 | 运维缺失 |
| **P3** | P3-2 | 「核心逻辑 100%」覆盖目标过高 | 目标设定 |

**建议修复 3 个 P1 后即可进入实现。** P2/P3 可在实现过程中逐步明确。
