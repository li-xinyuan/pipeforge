# ConfigForge 用户功能与体验测试报告

**测试日期**: 2026-06-12  
**测试方法**: Playwright 浏览器自动化 + 单元测试  
**测试角色**: 模拟首次使用系统的新用户  

---

## 一、测试覆盖

### 测试路径矩阵

| # | 输入类型 | 处理类型 | 输出类型 | 结果 |
|---|---------|---------|---------|------|
| 1 | CSV | SQL | Excel | ✅ 通过 |
| 2 | CSV | SQL | CSV | ✅ 通过 |
| 3 | CSV | SQL | Database | ✅ 通过 |
| 4 | CSV | Python | Excel | ✅ 通过 |
| 5 | Database | SQL | Excel | ✅ 通过 |

### 功能测试

| 功能 | 结果 |
|------|------|
| 首页配置列表加载 | ✅ 通过 |
| GuidePanel 右侧提示 | ✅ 通过 |
| 返回上一步（清空当前步+保留上步） | ✅ 通过 |
| Step 1 场景名称填写 | ✅ 通过 |
| Step 2 CSV 文件上传 | ✅ 通过 |
| Step 2 Database 连接选择 | ✅ 通过 |
| Step 3 SQL 处理器 | ✅ 通过 |
| Step 3 Python 处理器 | ✅ 通过 |
| Step 4 输出类型选择 | ✅ 通过 |
| Step 4 数据源表选择 | ✅ 通过 |
| Step 4 列映射配置 | ✅ 通过 |
| Step 4 Database 输出配置 | ✅ 通过 |
| Step 5 YAML 预览 | ✅ 通过 |
| Step 5 运行预览（dry-run） | ✅ 通过 |
| Step 5 保存配置 | ✅ 通过 |

### 自动化测试汇总

| 测试套件 | 通过 | 失败 |
|----------|------|------|
| 后端 pipeforge 核心测试 | 168 | 0 |
| 后端 configforge API 测试 | 199 | 0 |
| 前端 TypeScript 编译 | 0 errors | - |
| 前端 vitest 单元测试 | 162 | 0 |
| E2E 浏览器功能测试 | 49 | 0 |
| **合计** | **578** | **0** |

---

## 二、发现并修复的 Bug

### Bug 1: Step 4 选择输出类型后 output 仍为 null（严重）

**现象**: 用户在 Step 4 点击 Excel/CSV/Database 卡片后，`store.output` 仍为 null，验证消息显示"请选择输出格式"，无法进入 Step 5。

**根因**: `switchOutputType()` 函数内部访问 `outputConfig.value.sourceTable`，但 `outputConfig` 是 `computed(() => store.output!.config)`。当 `store.output` 为 null 时（首次进入 Step 4），`store.output!.config` 抛出 TypeError，导致整个函数静默失败。

**修复**: 将 `outputConfig.value.sourceTable` 改为 `store.output?.config?.sourceTable || ''`，安全访问可选链。

**文件**: `configforge-web/src/components/step3/OutputConfigTab.vue`

### Bug 2: Database 输入源无法通过 Step 2（严重）

**现象**: 用户选择 Database 输入类型并填写连接和表名后，"下一步"按钮仍为禁用状态。

**根因**: `canProceed(2)` 检查 `!!inp.fileId`，但 Database 输入不需要上传文件，`fileId` 始终为空。

**修复**: `canProceed(2)` 中对 database 类型跳过 fileId 检查：`const hasFile = inp.plugin === 'database' || !!inp.fileId`。同步修复 `stepValidation(2)` 中的相同逻辑。

**文件**: `configforge-web/src/stores/wizard.ts`

### Bug 3: 首页配置列表不显示（中等）

**现象**: 首页"最近配置"列表为空，即使已有保存的配置。

**根因**: `listConfigs()` 使用 `(data || []).map()` 处理 API 返回，但 API 已改为分页格式 `{items, total, page}`，对象没有 `.map` 方法。

**修复**: `const items = Array.isArray(data) ? data : (data.items || [])`

**文件**: `configforge-web/src/composables/useConfigApi.ts`

### Bug 4: Step 4 不先显示输出类型选择器（中等）

**现象**: 进入 Step 4 时直接显示配置表单，跳过了输出类型选择步骤。

**根因**: `output` 默认值从 `null` 改为有初始值后，`showOutputTypeChoices` 初始化为 `false`。

**修复**: `showOutputTypeChoices` 默认为 `true`，通过 `watch` 监听 `store.output?.plugin` 有值时自动设为 `false`。

**文件**: `configforge-web/src/components/step3/OutputConfigTab.vue`

---

## 三、用户体验评估

### 优点

1. **GuidePanel 提示清晰** — 每步都有上下文感知的提示，首次用户能理解每步该做什么
2. **步骤锁定机制** — 未完成当前步骤时，后续步骤被锁定，防止用户跳过
3. **自动推断** — SQL 输出表名、列映射等有自动推断功能，减少手动输入
4. **返回上一步** — 正确清空当前步数据、保留上一步数据，行为符合预期
5. **多输出类型** — Excel/CSV/Database 三种输出类型均已可用

### 需改进

1. **NSelect 交互** — Naive UI 的下拉选择器在无障碍模式下操作困难，建议为关键 NSelect 添加 `data-testid` 属性方便测试
2. **Step 4 首次进入** — 选择输出类型后，sourceTable 和 columns 需要用户手动选择/添加，没有自动填充。建议选择输出类型后自动设置 sourceTable（如果只有一个选项）
3. **Database 输入连接管理** — 如果没有预配置的数据库连接，用户需要离开向导去设置页添加，体验不连贯
4. **Python 处理器模板** — 快速模板按钮提供了 4 个模板，但模板代码较长，对新手可能不够直观
5. **Step 5 数据预览** — dry-run 按钮存在但默认不执行，用户可能不知道需要点击

---

## 四、下一步建议

| 优先级 | 建议 | 说明 |
|--------|------|------|
| P0 | 选择输出类型后自动设置 sourceTable | 当只有一个可选表时自动选中 |
| P0 | 为 NSelect 添加 data-testid | 方便自动化测试 |
| P1 | Database 输入内联创建连接 | 不用离开向导即可添加新连接 |
| P1 | Step 5 自动执行 dry-run | 进入 Step 5 时自动触发预览 |
| P2 | 列映射自动推断优化 | 选择 sourceTable 后自动推断列映射 |
| P2 | Python 模板简化 | 提供更简洁的模板代码 |
