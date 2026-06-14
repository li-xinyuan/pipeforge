# ConfigForge AI 顾问模式 — 设计方案

> 版本: v1.0
> 日期: 2026-06-14
> 状态: 待审核

---

## 一、设计目标

将 AI 从「主动介入」模式调整为「顾问」模式——AI 退后一步，只在用户明确求助时才出手，但出手就要精准有用。

**核心原则：**

1. **被动调用** — AI 不自动分析、不主动弹提示，所有 AI 调用由用户点击触发
2. **精准输出** — 每次 AI 调用有明确的输入和期望输出格式，不泛泛而谈
3. **统一视觉** — 所有 AI 入口使用统一的视觉语言（✨ 图标 + 渐变虚线边框），用户一看就知道这里可以借助 AI
4. **GuidePanel 导航** — 右侧 GuidePanel 只做固定提示，告诉用户当前该做什么、左侧哪里有 AI 功能可用

---

## 二、AI 触发点总览

### 2.1 保留的现有 AI 功能（3 处）

| 步骤 | 位置 | 按钮 | 后端 API | 说明 |
|------|------|------|---------|------|
| Step 2 | `InputSourceCard.vue` | ✨ AI 分析此文件 | `askSuggestion('columns')` | 分析列结构、推荐表名、参数键、列类型 |
| Step 3 | `SqlProcessorContent.vue` | ✨ AI 生成 SQL | `askSuggestion('sql')` | 自然语言 → SQLite SQL |
| Step 4 | `OutputConfigTab.vue` | ✨ AI 推断列映射 | `askSuggestion('mapping')` | 源列 → 目标列自动映射 |

### 2.2 新增的 AI 功能（1 处）

| 步骤 | 位置 | 按钮 | 后端 API | 说明 |
|------|------|------|---------|------|
| Step 5 | `ConfigWizardView.vue` | ✨ AI 预检配置 | `askSuggestion('diagnose')` | 执行前检查配置完整性、列映射、SQL 语法 |

### 2.3 移除的 AI 行为

| 原行为 | 原因 |
|--------|------|
| GuidePanel 中的 `ai_analyze_step3` 按钮 | 与左侧已有的「AI 生成 SQL」功能重复 |
| GuidePanel 中的 `analyze_columns` 按钮 | 与左侧「AI 分析此文件」功能重复 |
| GuidePanel 中的 `suggest_checkpoints` | 打断流程连续性 |
| 进入步骤时自动调用 AI | 用户未请求，体验突兀 |

---

## 三、统一 AI 视觉规范

### 3.1 设计语言

| 属性 | 规范 |
|------|------|
| 图标 | ✨（sparkles emoji），始终在按钮文字左侧 |
| 背景 | `linear-gradient(135deg, rgba(13,148,136,0.06), rgba(13,148,136,0.12))` |
| 边框 | `1.5px dashed rgba(13,148,136,0.35)` |
| 暗色模式边框 | `1.5px dashed rgba(94,234,212,0.35)` |
| 圆角 | `8px` |
| 文字 | `font-weight: 600 · color: #0d9488 (暗色: #5eead4) · font-size: 12px` |
| Hover | 背景色透明度 +0.05 · 边框色 +0.15 · transform: scale(1.02) |
| 点击 | transform: scale(0.97) |
| Loading | 按钮内文字变为「AI 思考中...」+ ✨ 图标旋转动画 |

### 3.2 CSS 实现

```css
.ai-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1.5px dashed rgba(13,148,136,0.35);
  background: linear-gradient(135deg, rgba(13,148,136,0.06), rgba(13,148,136,0.12));
  color: #0d9488;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ai-trigger-btn:hover {
  background: linear-gradient(135deg, rgba(13,148,136,0.10), rgba(13,148,136,0.16));
  border-color: rgba(13,148,136,0.50);
  transform: scale(1.02);
}

.ai-trigger-btn:active { transform: scale(0.97); }

.ai-trigger-btn.loading .ai-icon {
  animation: ai-spin 1s linear infinite;
}

@keyframes ai-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## 四、GuidePanel 各步骤固定文案

GuidePanel 不再包含 AI 按钮。每步的固定文案改为「指路」风格：

### Step 1 — 场景信息
```
💡 请在左侧填写场景名称和描述
描述中说明：数据来源、处理方式、输出格式
完成后点击下方「下一步」继续
```

### Step 2 — 输入源
```
💡 请选择输入源类型并上传文件
上传后可使用文件卡片上的 ✨ AI 分析此文件 功能
让 AI 帮你分析列结构、推荐表名和参数键
```

### Step 3 — 处理步骤
```
💡 请选择处理方式（SQL 或 Python）
创建处理器后，可在编辑器中点击 ✨ AI 生成 SQL
用自然语言描述需求，AI 将生成对应代码
```

### Step 4 — 输出配置
```
💡 请选择输出格式并配置文件
列映射未完成时，可点击 ✨ AI 推断列映射
AI 将根据处理步骤的输出列自动完成映射
```

### Step 5 — 导出执行
```
💡 配置已完成，请预览 YAML 并导出
建议点击 ✨ AI 预检配置 检查完整性
确认无误后下载 YAML 或执行流水线
```

---

## 五、各 AI 功能的输入输出规范

### 5.1 Step 2：AI 分析此文件

**输入**（发给后端）：
```json
{
  "category": "columns",
  "context": {
    "columns": ["序号", "日期", "姓名", "城市", "金额"],
    "sampleRows": [["1", "2024-01", "张三", "北京", "1500"], ...],
    "scene_name": "订单城市统计",
    "scene_description": "..."
  }
}
```

**期望输出**：
```json
{
  "columnTypes": { "序号": "number", "日期": "date", "姓名": "string", "城市": "string", "金额": "number" },
  "tableName": "订单数据",
  "paramKey": "order_file",
  "analysis": "该文件包含订单记录，共 5 列。'城市'列可用于 GROUP BY 分组统计，'金额'列可用于 SUM 聚合。符合场景'订单城市统计'的需求。",
  "missingColumns": ["用户ID"]  // 场景需要但文件缺少的列
}
```

### 5.2 Step 3：AI 生成 SQL

**输入**：
```json
{
  "category": "sql",
  "context": {
    "naturalLanguage": "按城市统计订单数和总金额",
    "tables": [{ "name": "订单数据", "columns": ["序号", "日期", "城市", "金额"] }],
    "scene_name": "订单城市统计"
  }
}
```

**期望输出**：
```json
{
  "sql": "SELECT 城市, COUNT(*) AS 订单数, SUM(金额) AS 总金额 FROM 订单数据 GROUP BY 城市",
  "explanation": "按城市分组，使用 COUNT 统计订单数，SUM 汇总金额"
}
```

### 5.3 Step 4：AI 推断列映射

**输入**：
```json
{
  "category": "mapping",
  "context": {
    "sourceColumns": ["城市", "订单数", "总金额"],
    "targetColumns": ["city", "order_count", "total_amount"]
  }
}
```

**期望输出**：
```json
{
  "mappings": [
    { "source": "城市", "target": "city" },
    { "source": "订单数", "target": "order_count" },
    { "source": "总金额", "target": "total_amount" }
  ]
}
```

### 5.4 Step 5：AI 预检配置（新增）

**输入**：
```json
{
  "category": "diagnose",
  "context": {
    "yaml": "...",          // 完整的 YAML 配置
    "scene_name": "...",
    "inputs": [...],
    "processors": [...],
    "output": {...}
  }
}
```

**期望输出**：
```json
{
  "issues": [
    { "severity": "warning", "step": 4, "message": "列映射中 '城市' 未映射到任何目标列" },
    { "severity": "info", "step": 3, "message": "SQL 中没有使用 WHERE 过滤，会处理全部数据" }
  ],
  "summary": "配置基本完整，1 个警告，1 个提示。可安全执行。"
}
```

---

## 六、实施要点

### 6.1 前端改动

| 文件 | 改动 |
|------|------|
| `style.css` | 新增 `.ai-trigger-btn` 全局样式 |
| `InputSourceCard.vue` | 现有 AI 按钮改用 `.ai-trigger-btn` 样式 |
| `SqlProcessorContent.vue` | 现有 AI 按钮改用 `.ai-trigger-btn` 样式 |
| `OutputConfigTab.vue` | 现有 AI 按钮改用 `.ai-trigger-btn` 样式 |
| `GuidePanel.vue` | 各步骤文案改为「指路」风格，移除所有 AI 按钮 |
| `ConfigWizardView.vue` | Step 5 新增「AI 预检配置」按钮 |

### 6.2 后端改动

| 文件 | 改动 |
|------|------|
| `orchestrator.py` | columns/sql/mapping 三个 category 的 prompt 模板优化，增加场景上下文 |
| `orchestrator.py` | diagnose category 输出格式标准化 |

### 6.3 不涉及改动

现有 AI 调用逻辑（`useAiApi.askSuggestion`、`AiColumnAnalysisModal`、`AiColumnConfirmModal`）保持不变，仅视觉样式统一。

---

## 七、与现有代码的关系

```
改动前：
  GuidePanel 有 AI 按钮 → 触发 triggerStepGuide → 调 AI → 循环/重复
  左侧表单有 AI 按钮 → 各自独立样式

改动后：
  GuidePanel 只有固定文案 → 引导用户去左侧用 AI
  左侧表单 AI 按钮 → 统一 ✨ 虚线渐变样式
  Step 5 新增 AI 预检 → 统一样式
```

---

## 八、成功标准

1. 所有 AI 入口视觉统一（✨ + 渐变 + 虚线）
2. 用户一眼能区分「普通功能」和「AI 辅助功能」
3. GuidePanel 文案指路清晰，用户知道去哪里找 AI
4. AI 输出精准、结构化、可操作
5. 不会出现 AI 主动打断用户流程的情况
