# 插件系统优化方案 v2.0 — 复审报告

> 复审日期：2026-06-27
> 被审核文档：`PLUGIN_OPTIMIZATION_PROPOSAL.md`（v2.0，修订日期 2026-06-27）
> 复审基线：`PLUGIN_PROPOSAL_REVIEW.md`（v1.0 审核报告）
> 复审结论：**通过，可进入实施** — 4 个建议项，无阻断性问题

---

## 一、v1.0 审核意见处理情况

v1.0 审核报告共提出 2 个需修正 + 5 个需补充 = 7 个行动项。v2.0 处理情况：

| # | v1.0 意见 | v2.0 处理 | 状态 |
|---|----------|----------|------|
| 1 | ijson 可选依赖处理策略未明确 | 3.4 第二阶段步骤 1：明确方案 A（提升为必需依赖 `ijson>=3.2`）和方案 B（抛 RuntimeError），推荐 A | ✅ 已处理 |
| 2 | `_USER_ERRORS` 已含 ValueError 的重复描述 | 3.4 第一阶段步骤 2：标注「ValueError 已在 _USER_ERRORS 中，无需重复添加」 | ✅ 已处理 |
| 3 | 工期上调 15-20% | 6.1 优先级矩阵：18-22 → 23-25 天；各阶段单独标注上调原因 | ✅ 已处理 |
| 4 | 实施顺序由并行改为串行 | 6.2 完全重写，4 周串行，附调整理由 | ✅ 已处理 |
| 5 | loose 模型技术 spike | 4.5 第二步步骤 0：0.5 天 spike，指定 DatabaseOutputConfig 为验证对象，4 个验证点 + fail 回退策略 | ✅ 已处理 |
| 6 | SchemaForm v-model 数据流设计 | 5.6 第一阶段步骤 2：完整设计（父组件窄化鉴别联合 → SchemaForm 接收 modelValue + emit 局部更新 → 父组件类型安全更新） | ✅ 已处理 |
| 7 | api_reader.py 现状 | 3.1 新增 reader 现状表 + 附录 A 补充 api_reader.py 详细信息 | ✅ 已处理 |

**追加处理**（超出 v1.0 审核要求）：
- 新增 6.4 节「Reader 驱动模型生成」轻量化备选方案（spike 失败时的回退路径）
- 新增 3 项风险评估（ijson / SchemaForm v-model / yaml_builder 简化）
- 8 节审核清单全部标注审核结论
- 附录 A 补充文件后缀强制改名代码行、`_USER_ERRORS` 现状、loose 模型目标位置

**结论**：v1.0 审核意见全部落地，无遗漏。

---

## 二、新增内容审查

### 2.1 6.4 节「Reader 驱动模型生成」备选方案

**评价**：✅ 设计合理

这个方案为 ③Phase 2 + ②loose 模型提供了清晰的回退路径：spike 通过 → 主方案（新增 loose JsonInputConfig 等），spike 失败 → 备选方案（Reader 驱动，跳过专属 config 类型）。决策树显式化降低了实施风险。

**优点**：
- 利用 reader 已有的列信息和样本行，减少 50% 模型定义
- 避免 pipeforge config 联合类型膨胀
- yaml_builder 改动更小（统一走 file 路径）

**注意**：备选方案的「类型安全性略降」是可接受的——json/xml/parquet 的配置字段非常少（json 仅 `flattenSeparator`，xml 仅 `rowElement`，parquet 无特殊字段），丢失专属类型的代价很低。

### 2.2 SchemaForm v-model 数据流设计（5.6 第一阶段步骤 2）

**评价**：✅ 设计清晰，架构合理

关键设计决策——「父组件负责鉴别联合窄化，SchemaForm 只接收 `Record<string, unknown>`」——将类型安全的边界放在正确的位置。SchemaForm 作为通用组件不感知业务类型，父组件保留 `wizard.ts` 判别联合的类型保护。

PoC 先用 csv（最简单配置类型）验证的策略也是务实的选择。

### 2.3 异步选项支持从 Phase 2 前移到 Phase 1（5.6 第一阶段步骤 5）

**评价**：✅ 必要性正确

原方案 Phase 2 迁移 excel 时才需要异步选项（sheet 从 fetchPreview 动态加载），但 Phase 1 不实现的话 Phase 2 会被阻塞。前移是正确的。

**⚠️ 关注点**：Phase 1 现在包含 5 个子任务，2 天完成偏紧（见第三节）。

---

## 三、剩余问题

### 🟡 R-01：实施排期 Day 编号与 Week 标签不一致（6.2 节）

当前排期：

```
Week 1: Day 1-3   (3 个工作日)
Week 2: Day 4-7   (4 个工作日)
Week 3: Day 8-12  (5 个工作日)
Week 4: Day 13-24 (12 个工作日 = 2.4 周)
```

Day 13-24 包含 ①迁移简单插件（4 天）+ ①迁移复杂插件（7 天）+ api 输入（1 天）= 12 个工作日，远超一个 Week 的容量。

**建议修正**：

```
Week 1: Day 1-3   — 止血 + 契约测试
Week 2: Day 4-7   — reader 适配器 + loose spike
Week 3: Day 8-12  — loose 模型实施 + 动态表单基础设施
Week 4: Day 13-16 — 迁移简单插件
Week 5: Day 17-23 — 迁移复杂插件
Week 6: Day 24    — api 输入或延后
```

或者改为仅使用 Day 编号（不标注 Week），避免歧义。

---

### 🟡 R-02：Phase 1 动态表单基础设施 2 天偏紧（5.6 节）

Phase 1 当前范围（2 天）：

| 子任务 | 预估耗时 |
|--------|---------|
| 1. usePluginSchema composable | 0.25 天 |
| 2. SchemaForm 组件（含 v-model 鉴别联合设计） | 0.75 天 |
| 3. widgetRegistry | 0.25 天 |
| 4. 默认值从 schema 派生 | 0.25 天 |
| 5. **异步选项支持（新增）** | 0.5 天 |

合计约 2 天，但没有任何缓冲。SchemaForm 的 v-model 双向绑定设计是**整个动态表单方案中最关键的技术决策**，如果在 Phase 1 没有充分验证，会导致 Phase 2/3 大量返工。

**建议**：Phase 1 调整为 2.5 天，或用「Day 11-12 + 半天缓冲」的方式在 Week 3 排期中给予弹性。最坏情况下，异步选项支持（子任务 5）可以回退到 Phase 2 第一天做——excel 迁移是 Phase 2 的第一步，有 4 天时间可消化。

---

### 🟡 R-03：`x-ui-actions` 扩展字段未定义（5.6 节 Phase 3 步骤 2）

第 500-502 行提到：

> SQL 模板变量、dry-run 集成需通过 `x-ui-actions` 扩展字段表达

但 `x-ui-actions` 未在 5.5 节「方案 C 的具体设计」中与 `x-ui-widget`、`x-ui-visible`、`x-ui-options-from` 一起定义。读者无法理解 `x-ui-actions` 的语义和用法。

**建议**：在 5.5 节补充 `x-ui-actions` 的定义，例如：

```
操作扩展（x-ui-actions）：
  "dry-run" → 渲染「试运行」按钮，触发 onDryRun 回调
  "template-insert" → 渲染「插入模板变量」下拉，触发 onInsertTemplate 回调
```

---

### 🟡 R-04：文件后缀修复描述可更精确（3.4 节 Phase 2 步骤 5）

v2.0 描述为：
> `dst_name = inp.file_id + (".xlsx" if inp.plugin == "excel" else ".csv")`

实际代码（pipeline.py:248-256，已核查）为：

```python
ext = os.path.splitext(inp.file_id)[1].lower()
if ext in (".xlsx", ".xls", ".csv"):
    dst_name = inp.file_id           # 已知后缀 → 保留
else:
    dst_name = inp.file_id + (".xlsx" if inp.plugin == "excel" else ".csv")  # 未知后缀 → 追加
```

差异不影响修复方案的正确性，但修复描述可以更精确。建议修订为：

> 现状：仅 `.xlsx`/`.xls`/`.csv` 后缀被识别保留，json/xml/parquet 文件落入 else 分支被追加 `.csv`
> 修复：在 `ext in (...)` 识别列表中增加 `.json`、`.xml`、`.parquet`

---

## 四、交叉验证

### 4.1 工作量一致性检查

| 出处 | ③B+D | ②E | ③C | ①Phase1 | ①Phase2 | ①Phase3 | ②loose | 合计 |
|------|------|-----|-----|---------|---------|---------|---------|------|
| 6.1 矩阵 | 1 | 1.5 | 4-5 | 2 | 4 | 7-8 | 3.5 | 23-25 |
| 6.2 排期 | Day 1 | Day 2-3 | Day 5-7 | Day 11-12 | Day 13-16 | Day 17-23 | Day 4(0.5)+8-10(3) | — |

6.2 排期的 Day 计数与 6.1 矩阵一致 ✅

### 4.2 依赖顺序一致性检查

6.3 节声明的依赖关系：
- ③和②必须同步 → Week 1 Day 1-3 ✅
- ①依赖②的 loose 模型但有过渡策略 → Week 3 Day 11-12 用 strict schema 过渡 ✅
- ③的 reader 适配器复用②的 loose 模型 → Week 2 Day 4 spike 在 Week 3 loose 实施之前 ✅

依赖链无循环，过渡策略可行。

### 4.3 风险覆盖率

v2.0 风险矩阵（第 7 节）共 11 项风险，覆盖了：
- 技术风险：reader 内存、Pydantic alias、SchemaForm v-model、yaml_builder 简化、loose alias CLI 影响、ijson 依赖
- 安全风险：api SSRF
- 流程风险：契约测试 CI 成本、_USER_ERRORS 重复（已消除）

覆盖率较 v1.0 显著提升，无遗漏。

---

## 五、复审结论

**v2.0 方案质量**：较 v1.0 有显著提升。v1.0 审核意见全部落地，追加的备选方案和风险项增强了方案的鲁棒性。SchemaForm v-model 数据流设计是新增内容中最有价值的部分——它解决了动态表单方案中最容易被低估的技术难点。

**剩余问题**：4 个建议项，均为非阻断性：

| 编号 | 类型 | 问题 | 建议 |
|------|------|------|------|
| R-01 | 排期 | Day 编号与 Week 标签不一致（Week 4 含 12 天） | 拆分为 Week 4-6，或去掉 Week 标签仅用 Day |
| R-02 | 工期 | Phase 1 动态表单基础设施 2 天偏紧 | 调整为 2.5 天，或异步选项支持回退到 Phase 2 |
| R-03 | 完整性 | `x-ui-actions` 扩展字段未定义 | 在 5.5 节补充定义 |
| R-04 | 精度 | 文件后缀修复描述简化过度 | 补充 extension guard clause 的描述 |

**最终结论**：✅ **通过，可进入实施**。4 个建议项不阻塞开工，可在实施过程中逐步修正。

---

*复审基于 v2.0 文档 + pipeline.py:248-256 代码核查 + api_reader.py 存在性确认。*
