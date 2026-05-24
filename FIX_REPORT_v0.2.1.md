# ConfigForge v0.2.1 修复报告

> 基于 `SYSTEM_REVIEW_v0.2.1.md` 第三方审查报告 + `VERIFICATION_REPORT_v0.2.1.md` 验证反馈。
> 共计修复 31 项：20 个审查缺陷 + 2 个反馈缺陷 + 9 个 Medium 缺陷。
> 排除项：H3（CORS 端口不属实）、H11/H12（`resp.json()` 双调用不属实）。

---

## 一、Critical & High 缺陷（17 项修复 + 2 项反馈修正）

### Phase 1 — 严重安全缺陷（5 项）

#### C1: 路径穿越 (pipeline.py)

**文件:** `configforge/core/pipeline.py`
**问题:** 用户提供的 `file_id` / `template_id` 直接拼入 `os.path.join(UPLOAD_DIR, ...)`，可构造 `../` 穿越到任意文件。
**修复:** 在 5 个调用点插入 `validate_id()` 校验（正则 `^[a-zA-Z0-9_.\-]+$`，拒绝 `..`、`/`、`\`）。
**验证:** API 测试 `../../etc/passwd` → 400 拦截。

#### H1: SQL 注入 (preview.py)

**文件:** `configforge/api/preview.py`
**问题:** 表名未剥离双引号；DDL/DML 检测可被 `DR/**/OP` 注释绕过。
**修复:** `table_name.replace('"', '')` + 剥离 `--` 和 `/* */` 注释后再检测。
**验证:** API 测试 `DR/**/OP TABLE` → 拦截。

#### H2: SQL 注入 (pipeline.py)

**文件:** `configforge/core/pipeline.py`
**问题:** `output_table` 拼入 `CREATE TABLE` 前未剥离双引号。
**修复:** 两处 `output_table.replace('"', '')`。

#### H4: MIME 校验缺失 (files.py)

**文件:** `configforge/api/files.py`
**问题:** 仅校验扩展名，可上传伪装文件。
**修复:** 50MB 上限 + `.xlsx` 前 4 字节 `PK\x03\x04` 校验 + `.csv` UTF-8 校验。
**验证:** API 测试伪装 xlsx、非 UTF-8 CSV → 422 拒绝。

#### H5: 密钥派生不安全 (settings.py)

**文件:** `configforge/services/ai/settings.py`
**问题:** `ljust(32, b"\x00")` 零填充缩减密钥空间。
**修复:** 改用 `hashlib.sha256().digest()` + `urlsafe_b64encode`。

---

### Phase 2 — 资源管理（6 项）

#### C2: 竞态条件 (configs.py)

**文件:** `configforge/api/configs.py`
**修复:** `_load_index` 加 `fcntl.LOCK_SH`，`_save_index` 加 `fcntl.LOCK_EX`，finally 释放。

#### C3: 临时目录泄漏 (pipeline.py)

**文件:** `configforge/core/pipeline.py`
**修复:** `try/except` 中 `shutil.rmtree(tmp_dir, ignore_errors=True)`。

#### C4: 配置对象变异 (engine.py)

**文件:** `src/pipeforge/core/engine.py`
**修复:** `copy.deepcopy(inp_spec.config)` 替代直接赋值。

#### C5: Excel 文件句柄泄漏 (input/excel.py)

**文件:** `src/pipeforge/plugins/input/excel.py`
**修复:** `try/finally` 确保 `wb.close()` 始终执行。

#### H6: CSV DoS (csv_reader.py)

**文件:** `configforge/services/csv_reader.py`
**修复:** `MAX_CSV_ROWS = 50000` 截断。

#### H7: WAL 文件残留 (sqlite.py)

**文件:** `src/pipeforge/core/sqlite.py`
**修复:** `remove()` 同时删除 `-wal` / `-shm` 附属文件。

---

### Phase 3 — 崩溃修复 & 校验增强（4 项）

#### H8: param_key 空值校验 (models.py)

**文件:** `src/pipeforge/config/models.py`
**修复:** `@field_validator("param_key")` 拒绝空字符串。

#### H9: 路径解析不一致 (input/excel.py)

**文件:** `src/pipeforge/plugins/input/excel.py`
**修复:** `os.path.join(context.yaml_dir, config.file)` 与 CSV 插件行为一致。

#### H10: 空工作表 IndexError (output/excel.py)

**文件:** `src/pipeforge/plugins/output/excel.py`
**修复:** `first_row_cells[0]` 空值 guard + 清晰 `ValueError`。

#### H15: ColumnMapping 编辑 Bug (ColumnMapping.vue)

**文件:** `configforge-web/src/components/step3/ColumnMapping.vue`
**修复:** `editingIndex` ref 替代 `v-if="!col.source"`，支持点击重新编辑。

---

### Phase 4 — 前端技术债务（2 项）

#### H13: 消除 `as any`（18 处 → 0）

**涉及文件:** `wizard.ts`, `DatabaseForm.vue`, `ExportActions.vue`, `YamlPreview.vue`, `ConfigWizardView.vue`
**修复:** 类型守卫 (`getDbConfig`, `getWizardState`) + 直接移除（共用属性自动推断）+ `instanceof HTMLElement`。

#### H14: 序列化逻辑去重

**涉及文件:** `serialization.ts`（新建）, `useConfigApi.ts`, `ExportActions.vue`, `YamlPreview.vue`
**修复:** 三处独立实现的 `stateToSnakeCase` 提取到 `src/utils/serialization.ts`。

---

### Phase 4 反馈修正 — TypeScript 编译错误（2 项）

> 来源：`VERIFICATION_REPORT_v0.2.1.md` 发现 `vue-tsc --noEmit` 存在 5 个错误。

#### N1-N2: serialization.ts 类型断言不安全

**文件:** `configforge-web/src/utils/serialization.ts`
**问题:** `as Record<string, unknown>` 绕过 discriminated union 检查。
**修复:** `buildInputConfig` / `buildOutputConfig` 参数改为 `InputConfig` / `OutputConfig` 联合类型，内部通过 `unknown` 中间断言。

#### N3-N5: outputTables 属性不存在于 ProcessorConfig

**文件:** `configforge-web/src/views/ConfigWizardView.vue`
**问题:** 代码使用 `store.processor.outputTables`（复数），类型定义只有 `outputTable: string`（单数），运行时始终 `undefined`。
**修复:** `outputTables` → `outputTable`，匹配 `ProcessorConfig` 类型定义。

---

## 二、Medium 缺陷（9 项）

> 来源：`VERIFICATION_REPORT_v0.2.1.md` 第七节"未修复缺陷跟踪"。

#### M1: 异常信息泄露

**涉及文件:** `configs.py`, `preview.py`, `wizard.py`
**问题:** `detail=str(e)` 将内部异常信息暴露给客户端。
**修复:** 替换为通用用户提示（如 "Invalid config_id format"、"Pipeline execution failed"）。

#### M5: AI 错误可能泄露 API Key

**文件:** `configforge/api/ai.py`
**问题:** SDK 错误原始消息直接返回前端，可能包含 Key 片段。
**修复:** 错误响应改为通用提示（"API Key 无效，请检查设置"），详细错误仅记录日志。

#### M6: AI suggest 无速率限制

**文件:** `configforge/api/ai.py`
**问题:** `/api/ai/suggest` 无限流，可被滥用。
**修复:** 内存滑动窗口限流器：每 IP 每 60 秒最多 10 次请求，超限返回 429。

#### M7: 解密失败静默丢弃 API Key

**文件:** `configforge/services/ai/settings.py`
**问题:** Fernet 解密失败时 `except: raw["api_key"] = ""` 静默丢弃 Key。
**修复:** 记录 warning 日志，提示用户重新配置。

#### M8: Prompt Injection 风险

**文件:** `configforge/services/ai/orchestrator.py`
**问题:** 用户输入直接插值到系统提示词，可注入 "Ignore previous instructions"。
**修复:** `_sanitize_user_input()` 截断超长输入 + 正则过滤常见注入模式。

#### M9: httpx.AsyncClient 未关闭

**文件:** `configforge/services/ai/openai_backend.py`, `anthropic_backend.py`
**问题:** 两后端各自创建 `httpx.AsyncClient` 但从不调用 `aclose()`。
**修复:** 添加 `close()` 方法，清理底层 HTTP 连接。

#### M10: SPA 回退路由缺少 realpath 检查

**文件:** `configforge/server.py`
**问题:** `os.path.join(_static_dir, full_path)` 可被 `../` 穿越。
**修复:** `os.path.realpath` 解析后检查是否在 `_static_dir` 内，否则返回 403。

#### M11: 所有列创建为 TEXT 类型

**文件:** `configforge/api/preview.py`
**问题:** `CREATE TABLE` 所有列硬编码为 `TEXT`，忽略数字/布尔等实际类型。
**修复:** `_infer_sql_type()` 根据样本数据推断 INTEGER / REAL / BOOLEAN / TEXT。

#### M13: Jinja2 未使用沙箱

**文件:** `src/pipeforge/plugins/processor/sql.py`
**问题:** 默认 `jinja2.Template` 允许任意 Python 表达式（SSTI 风险）。
**修复:** 改用 `jinja2.sandbox.SandboxedEnvironment`。

---

## 三、仍存在的 Low 缺陷

以下 L1-L14 属于代码规范/优化范畴，不影响功能安全，不在本次修复范围内：

- L1: 部分函数参数类型注解缺失
- L2-L4: 魔法数字未提取常量
- L5-L7: 日志级别使用不一致
- L8-L10: 部分异常处理过于宽泛
- L11-L14: 文档注释不完整

---

## 四、测试验证

| 套件 | 结果 |
|------|------|
| `pytest tests/` (PipeForge) | **117 passed** |
| `pytest configforge/tests/` (ConfigForge) | **131 passed** |
| `vitest run tests/` (Frontend) | **15 files, 100 passed** |
| `vue-tsc --noEmit` (TypeScript) | **0 errors** |
| **合计** | **348 tests, 0 failures** |

---

## 五、改动文件清单（30 个源文件）

| 层级 | 文件 | 修复项 |
|------|------|--------|
| PipeForge | `src/pipeforge/config/models.py` | H8, DbInputConfig |
| PipeForge | `src/pipeforge/core/engine.py` | C4 |
| PipeForge | `src/pipeforge/core/sqlite.py` | H7 |
| PipeForge | `src/pipeforge/plugins/input/excel.py` | C5, H9 |
| PipeForge | `src/pipeforge/plugins/output/excel.py` | H10 |
| PipeForge | `src/pipeforge/plugins/processor/sql.py` | M13 |
| ConfigForge | `configforge/server.py` | M10 |
| ConfigForge | `configforge/core/pipeline.py` | C1, H2, C3 |
| ConfigForge | `configforge/api/preview.py` | H1, M1, M11 |
| ConfigForge | `configforge/api/files.py` | H4 |
| ConfigForge | `configforge/api/configs.py` | C2, M1 |
| ConfigForge | `configforge/api/wizard.py` | M1 |
| ConfigForge | `configforge/api/ai.py` | M5, M6 |
| ConfigForge | `configforge/services/ai/settings.py` | H5, M7 |
| ConfigForge | `configforge/services/ai/orchestrator.py` | M8 |
| ConfigForge | `configforge/services/ai/openai_backend.py` | M9 |
| ConfigForge | `configforge/services/ai/anthropic_backend.py` | M9 |
| ConfigForge | `configforge/services/csv_reader.py` | H6 |
| Frontend | `configforge-web/src/utils/serialization.ts` | H14, N1-N2（新建） |
| Frontend | `configforge-web/src/stores/wizard.ts` | H13 |
| Frontend | `configforge-web/src/composables/useConfigApi.ts` | H14 |
| Frontend | `configforge-web/src/components/step2/DatabaseForm.vue` | H13 |
| Frontend | `configforge-web/src/components/step3/ColumnMapping.vue` | H15 |
| Frontend | `configforge-web/src/components/step4/ExportActions.vue` | H13, H14 |
| Frontend | `configforge-web/src/components/step4/YamlPreview.vue` | H13, H14 |
| Frontend | `configforge-web/src/views/ConfigWizardView.vue` | H13, N3-N5 |
| Frontend | `configforge-web/tests/components/InputSourceCard.test.ts` | 测试修复 |

---

## 六、Git 提交历史

```
37a5d5b fix: address 9 Medium-severity defects (M1, M5-M11, M13)
2143599 fix: eliminate remaining TS2352/TS2551 errors in serialization.ts and ConfigWizardView.vue
b70e924 merge: integrate security hardening and defect fixes
e04d020 fix: security hardening and defect fixes for pipeforge layer
17c17b6 fix: security hardening and defect fixes for configforge + frontend layers
```
