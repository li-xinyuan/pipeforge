# ConfigForge Demo 页面审核

> 审核文件: demo/configforge-demo.html  
> 对照基线: ConfigForge 设计文档 v1.3  
> 审核日期: 2026-05-03

---

## 一、与设计文档的符合度

### ✅ 做得好的部分

| 设计要求 | Demo 实现 | 评价 |
|---------|----------|------|
| 4 步向导 | Step 1-4 完整展示 | ✅ 完全一致 |
| StepIndicator 组件 | 圆点+连线+状态（done/current/未开始） | ✅ 还原度高 |
| Step 1 场景信息 | 名称/描述/版本 | ✅ |
| Step 2 输入源卡片 | Excel/CSV 不同配置 + 列预览 + 类型选择器 | ✅ 超出预期（展示了 CSV） |
| Step 3 处理器 + 输出配置 | 处理器类型选择 + SQL 编辑器 + 输出类型选择 + 列映射 | ✅ |
| Step 4 YAML 预览 + 导出 | 语法高亮 + 复制/下载/打包 | ✅ |
| AI 建议面板 | 蓝色渐变面板 + 采纳/重新生成 | ✅ |
| 插件矩阵 | Excel/CSV 可选，Database/PDF/PPT/API 标 future | ✅ 版本号与设计一致 |
| YAML 输出格式 | snake_case、columns 在 output.config 下、config 嵌套 | ✅ 与 PipeForge 一致 |
| 列映射 source→target | 表格形式，箭头指向 | ✅ |
| 文件名模板 `{{date:%Y%m%d}}` | 输入框默认值 | ✅ |
| CSV 输出提示「无模板和列映射概念」 | 不同输出类型的配置差异通过提示文字解释 | ✅ UX 细节好 |

---

## 二、需要修正的问题

### P1 — 重要问题

#### P1-1: Step 3 没有使用 Tab 分栏

设计文档 §6.5 Step 3 明确是 **Tab 分栏**：

```
[SQL 处理]  [输出配置]          ← Tab 切换
```

Demo 的 Step 3 把处理器和输出配置**纵向堆叠**在一个卡片里（处理器类型选择 → SQL 编辑器 → 分隔线 → 输出类型选择 → 输出配置），没有 Tab 切换。这导致 Step 3 页面非常长，用户需要大量滚动。

页面已有 `.tab-bar` 和 `.tab-item` 的 CSS 样式，只需在 HTML 中使用即可。

**建议**：改为 Tab 切换，与设计文档一致。

---

#### P1-2: Step 3 缺少 `output_tables` 和 `source_table` 字段

设计文档中 Processor 配置需要 `output_tables`（声明创建的表名），Output 配置需要 `source_table`（指定从哪个表读取数据）。Demo 中这两个字段都没有。

Step 4 的 YAML 预览中有 `output_tables: [monthly_report]`，但 Step 3 的表单中没有让用户填写的地方。`source_table` 在 YAML 预览中也没有出现（设计文档中 `ExcelOutputConfig` 有 `source_table` 字段）。

**建议**：
- Processor 配置增加 `output_tables` 字段（可多值，逗号分隔或标签式输入）
- Output 配置增加 `source_table` 下拉选择（从 `output_tables` 中选择）

---

#### P1-3: Step 3 输出配置缺少 `template` 和 `output_dir` 字段

设计文档 `ExcelOutputConfig` 包含：
- `template`: 模板文件路径
- `output_dir`: 输出目录（默认 `./output/`）
- `sheet`: 目标 Sheet 名称
- `filename`: 文件名模板
- `source_table`: 源表名
- `columns`: 列映射

Demo 中只有 `sheet`、`filename`、`columns`，缺少 `template`、`output_dir`、`source_table`。

Step 4 YAML 预览中有 `template: templates/monthly_report_template.xlsx`，但 Step 3 没有输入项。

**建议**：补充 `template`（模板文件选择/上传）和 `source_table`（下拉选择）。`output_dir` 可以用默认值隐藏，或作为高级选项展示。

---

#### P1-4: Step 2 的「添加输入源」交互流程不清晰

当前 Step 2 底部有：
1. 类型选择器（Excel/CSV/Database/...）
2. 「+ 添加输入源」按钮
3. 选中类型的配置字段预览

问题：
- 类型选择器和「配置字段预览」的关系不明确——用户会困惑「选了类型后点添加，还是先填配置再点添加？」
- 「配置字段预览」看起来像是正在编辑新输入源的表单，但它和上方已有的 3 个 source card 视觉上没有关联
- 点击「+ 添加输入源」按钮后应该发生什么？弹出类型选择？还是直接用当前选中的类型创建一个空卡片？

**建议**：改为更清晰的交互：
1. 点击「+ 添加输入源」→ 弹出类型选择弹窗/下拉
2. 选择类型后 → 在列表中新增一个空的 source card
3. 用户在 source card 内填写配置

---

#### P1-5: Step 2 的「配置字段预览」区域与已有 source card 功能重复

Step 2 下方有一个 `#inputConfigPreview` 区域，展示「选中类型的配置字段预览」。但上方已经有 3 个完整的 source card（人员明细/考勤数据/部门信息），每个都有完整的配置表单。

这个预览区域的作用不明确。如果是「添加新输入源时的编辑区」，那它应该和「添加」按钮联动；如果是「展示不同类型的配置差异」，那它和已有 card 重复了。

**建议**：移除 `#inputConfigPreview` 区域，改为点击「添加输入源」后直接在列表中新增空卡片。

---

### P2 — 建议优化

#### P2-1: Step 4 YAML 预览中 `scene.description` 缺失

Step 1 填了「场景描述」，但 Step 4 的 YAML 预览中没有 `description` 字段：

```yaml
scene:
  name: 月度人员考勤报表
  version: "1.0"
  # 缺少 description
```

对照 PipeForge 的 `SceneMeta` 模型，`description` 是必填字段。

**建议**：YAML 预览补充 `description: 汇总人员明细和考勤数据，生成月度统计报表`。

---

#### P2-2: CSV 输入源在 Step 2 展示但 v0.1 不支持

设计文档 §4.1 明确 v0.1 只支持 Excel 输入。Demo 中展示了 CSV 输入源（部门信息），虽然展示了扩展能力，但可能误导实现者以为 v0.1 需要支持 CSV。

**建议**：保留 CSV 展示（demo 目的是展示完整愿景），但加一个视觉提示（如 `tag-amber` 标签「v0.3」）表明这是未来功能。

---

#### P2-3: Step 4 缺少「刷新预览」按钮

设计文档 §6.5 Step 4 有 `[🔄 刷新预览]` 按钮。Demo 只有「复制」和「下载」，没有刷新。

**建议**：补充「刷新预览」按钮。

---

#### P2-4: StepIndicator 点击回退交互未实现

设计文档 §6.6：

> 点击已完成步骤 → 跳转到该步骤（不丢失后续步骤的数据）

Demo 的 `goToStep()` 函数只处理了视觉状态（done/current），StepIndicator 上的圆点有 `cursor: pointer` 但没有绑定点击事件。

**建议**：给 `.step-dot` 绑定 click 事件，允许点击已完成步骤回退。

---

### P3 — 微小问题

#### P3-1: Step 2 的 AI 建议面板位置偏底

设计文档 §6.5 Step 2 布局中，AI 建议面板在输入源列表下方。Demo 中也在列表下方，但它在「添加输入源」区域和「配置字段预览」之后，位置偏底。建议移到输入源列表和添加按钮之间。

#### P3-2: Step 1 的「版本」字段宽度写死了 `style="width: 100px"`

在 `form-row` 的两列布局中，右列被限制为 100px，导致右侧大量留白。建议去掉行内宽度，让两列自然分配。

---

## 三、问题汇总

| 优先级 | 编号 | 问题 | 类型 |
|--------|------|------|------|
| **P1** | P1-1 | Step 3 没有使用 Tab 分栏，与设计文档不符 | 布局不符 |
| **P1** | P1-2 | Step 3 缺少 output_tables / source_table 字段 | 配置缺失 |
| **P1** | P1-3 | Step 3 输出配置缺少 template / output_dir | 配置缺失 |
| **P1** | P1-4 | Step 2 添加输入源的交互流程不清晰 | UX 问题 |
| **P1** | P1-5 | Step 2 配置字段预览区与已有 source card 重复 | 冗余 |
| **P2** | P2-1 | YAML 预览缺少 scene.description | 数据不完整 |
| **P2** | P2-2 | CSV 输入源缺少 v0.3 标签 | 可能误导 |
| **P2** | P2-3 | Step 4 缺少刷新预览按钮 | 与设计不符 |
| **P2** | P2-4 | StepIndicator 点击回退未实现 | 交互缺失 |
| **P3** | P3-1 | AI 面板位置偏底 | 布局优化 |
| **P3** | P3-2 | 版本字段宽度写死 | 样式问题 |

**建议优先修复 5 个 P1 问题**，它们涉及核心交互流程和配置完整性。P2/P3 可在后续迭代中优化。
