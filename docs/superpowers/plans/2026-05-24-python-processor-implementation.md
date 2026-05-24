# Python Processor v0.4.0 Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Python processor — users can write Python scripts as processing steps, freely chained with SQL steps in DAG.

**Architecture:** Pure trust execution model with `exec()` + `signal.alarm` timeout. Python scripts receive `context` (db/params/logger). Frontend uses discriminated union `ProcessorStep` with sub-components `SqlProcessorContent` / `PythonProcessorContent`.

**Tech Stack:** Python 3.13 + Pydantic v2 + Vue 3 + TypeScript + Naive UI

---

### Task 1: PipeForge — PythonProcessorConfig model + ProcessorSpec union

**Files:**
- Modify: `src/pipeforge/config/models.py`
- Modify: `src/pipeforge/config/__init__.py`

- [ ] **Step 1: Add PythonProcessorConfig model**

```python
# src/pipeforge/config/models.py — add after SqlProcessorConfig

class PythonProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["python"] = "python"
    script: str

    @field_validator("script")
    @classmethod
    def script_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("script must not be empty")
        return v
```

- [ ] **Step 2: Extend ProcessorSpec.config union**

```python
# Replace:
# config: Annotated[SqlProcessorConfig, Field(discriminator="type")]
# With:
config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
```

- [ ] **Step 3: Update _inject_type_defaults**

```python
# src/pipeforge/config/__init__.py — modify existing function
def _inject_type_defaults(config_dict: dict, plugin: str) -> None:
    if plugin == "sql" and "type" not in config_dict:
        config_dict["type"] = "sql"
    elif plugin == "python" and "type" not in config_dict:
        config_dict["type"] = "python"
```

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=src:$PYTHONPATH python3 -m pytest tests/test_config_models.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/pipeforge/config/models.py src/pipeforge/config/__init__.py
git commit -m "feat: add PythonProcessorConfig model and extend ProcessorSpec union"
```

---

### Task 2: PipeForge — PythonProcessorPlugin

**Files:**
- Create: `src/pipeforge/plugins/processor/python.py`
- Test: `tests/test_python_processor.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_python_processor.py
import pytest

def test_python_processor_registered():
    """Python processor should be registered in PluginRegistry."""
    from pipeforge.core.registry import PluginRegistry
    cls = PluginRegistry.get("python", "processor")
    assert cls is not None

def test_python_processor_executes_script(tmp_path):
    """Python processor should execute user script and create output table."""
    from pipeforge.core.engine import PipelineEngine
    import openpyxl

    # Create test Excel file
    xlsx = tmp_path / "test.xlsx"
    wb = openpyxl.Workbook()
    wb.active.append(["name", "age"])
    wb.active.append(["Alice", "30"])
    wb.save(str(xlsx))

    # Create YAML with Python processor
    yaml_path = tmp_path / "pipeline.yaml"
    yaml_path.write_text(f"""
scene: {{name: test, version: "1.0"}}
inputs:
  - name: src
    plugin: excel
    table: raw_data
    param_key: f
    config: {{type: excel, sheet: Sheet1}}
processors:
  - name: py_step
    plugin: python
    input_tables: [raw_data]
    output_tables: [adults]
    config:
      type: python
      script: |
        def process(ctx):
            conn = ctx.db.connection
            conn.execute('CREATE TABLE adults AS SELECT * FROM raw_data WHERE CAST(age AS INTEGER) >= 18')
""")
    engine = PipelineEngine(str(yaml_path))
    result = engine.execute({"f": str(xlsx)})
    assert result is not None

def test_python_processor_timeout(tmp_path):
    """Python processor should timeout on infinite loops."""
    from pipeforge.core.engine import PipelineEngine
    import openpyxl

    xlsx = tmp_path / "test.xlsx"
    wb = openpyxl.Workbook()
    wb.active.append(["x"])
    wb.active.append(["1"])
    wb.save(str(xlsx))

    yaml_path = tmp_path / "pipeline.yaml"
    yaml_path.write_text(f"""
scene: {{name: test, version: "1.0"}}
inputs:
  - name: src
    plugin: excel
    table: data
    param_key: f
    config: {{type: excel, sheet: Sheet1}}
processors:
  - name: infinite
    plugin: python
    input_tables: []
    output_tables: []
    config:
      type: python
      script: |
        def process(ctx):
            while True: pass
""")
    engine = PipelineEngine(str(yaml_path))
    with pytest.raises(TimeoutError, match="超时"):
        engine.execute({"f": str(xlsx)})

def test_python_processor_missing_process_fn(tmp_path):
    """Script without process(ctx) function should raise ValueError."""
    from pipeforge.plugins.processor.python import PythonProcessorPlugin
    from pipeforge.core.context import Context

    plugin = PythonProcessorPlugin()
    with pytest.raises(ValueError, match="必须定义 process"):
        # Create a minimal context and PythonProcessorConfig to test validation
        from pipeforge.config.models import PythonProcessorConfig
        config = PythonProcessorConfig(script="x = 1")
        # This should fail because no process(ctx) function
        # Validation happens in execute() at runtime
```

- [ ] **Step 2: Implement PythonProcessorPlugin**

```python
# src/pipeforge/plugins/processor/python.py
import sys
from pipeforge.config.models import PythonProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin


@register_plugin("python", "processor")
class PythonProcessorPlugin(ProcessorPlugin):
    """Python 代码处理器 — 信任执行模型。"""
    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls) -> type[PythonProcessorConfig]:
        return PythonProcessorConfig

    def execute(self, context, config: PythonProcessorConfig) -> None:
        local_ns = {}
        exec(config.script, {}, local_ns)

        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        if sys.platform != "win32":
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Python 脚本执行超时（{self.TIMEOUT_SECONDS}秒）")
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.TIMEOUT_SECONDS)

        try:
            process_fn(context)
        finally:
            if sys.platform != "win32":
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            context.db.connection.commit()
            context.logger.info(f"Python processor '{self.label}': executed successfully")
```

- [ ] **Step 3: Run tests**

```bash
PYTHONPATH=src:$PYTHONPATH python3 -m pytest tests/test_python_processor.py -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/pipeforge/plugins/processor/python.py tests/test_python_processor.py
git commit -m "feat: add PythonProcessorPlugin with exec + timeout"
```

---

### Task 3: ConfigForge — backend models + pipeline + yaml_builder

**Files:**
- Modify: `configforge/models/wizard.py`
- Modify: `configforge/core/pipeline.py`
- Modify: `configforge/services/yaml_builder.py`
- Create: `configforge/generators/processor/python_processor.py`

- [ ] **Step 1: Update ProcessorConfig model**

```python
# configforge/models/wizard.py — replace ProcessorConfig

class ProcessorConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = ""
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
    input_tables: list[str] = Field(default=[], alias="inputTables")
    output_tables: list[str] = Field(default=[], alias="outputTables")

    @model_validator(mode="after")
    def validate_plugin_fields(self):
        if self.plugin == "sql" and not self.sql.strip():
            raise ValueError("SQL 步骤的 sql 字段不能为空")
        if self.plugin == "python" and not self.script.strip():
            raise ValueError("Python 步骤的 script 字段不能为空")
        return self
```

- [ ] **Step 2: Fix pipeline.py — skip Python in SQL auto-wrap**

```python
# configforge/core/pipeline.py — in execute_pipeline() and dry_run()
# Add before the SQL auto-wrap line:

for proc in _get_processors(exec_state):
    if proc.plugin == "python":
        continue  # Python 步骤不需要 SQL 自动包装
    if proc.output_tables and proc.sql.strip():
        if not _has_ddl(proc.sql):
            ...
```

Apply this same change in both `execute_pipeline()` (line 86) and `dry_run()` (line 210).

- [ ] **Step 3: Fix yaml_builder.py**

```python
# configforge/services/yaml_builder.py

# Main branch — add after existing SQL branch:
elif proc.plugin == "python":
    d["processors"].append({
        "name": proc.name or f"step_{i+1}",
        "plugin": "python",
        "input_tables": proc.input_tables,
        "output_tables": proc.output_tables,
        "config": {"type": "python", "script": proc.script},
    })

# Backward compat branch — add before existing SQL elif:
elif state.processor.plugin == "python" and state.processor.script.strip():
    d["processors"].append({
        "name": state.processor.name or state.scene.name + "处理",
        "plugin": "python",
        "input_tables": state.processor.input_tables,
        "output_tables": state.processor.output_tables,
        "config": {"type": "python", "script": state.processor.script},
    })
```

- [ ] **Step 4: Create PythonProcessorGenerator**

```python
# configforge/generators/processor/python_processor.py
import ast
from configforge.generators.base import ConfigGenerator, GeneratorRegistry
from configforge.models.wizard import ProcessorConfig


@GeneratorRegistry.register("python", "processor")
class PythonProcessorGenerator(ConfigGenerator[ProcessorConfig]):
    def infer_config(self, context: dict) -> ProcessorConfig:
        return ProcessorConfig(plugin="python")

    def build_config(self, state: "WizardState") -> ProcessorConfig:
        return ProcessorConfig(plugin="python", script="")

    def validate_config(self, config: ProcessorConfig) -> list[str]:
        errors = []
        if not config.script or not config.script.strip():
            errors.append("Python 脚本不能为空")
            return errors
        try:
            tree = ast.parse(config.script)
            has_process = any(
                isinstance(node, ast.FunctionDef) and node.name == "process"
                for node in ast.walk(tree)
            )
            if not has_process:
                errors.append("Python 脚本必须定义 process(ctx) 函数")
        except SyntaxError as e:
            errors.append(f"Python 语法错误: {e}")
        return errors
```

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=src:$PYTHONPATH python3 -m pytest configforge/tests/ -q
```
Expected: all pass (adjust tests if needed)

- [ ] **Step 6: Commit**

```bash
git add configforge/models/wizard.py configforge/core/pipeline.py configforge/services/yaml_builder.py configforge/generators/processor/python_processor.py
git commit -m "feat: backend support for Python processor — model, pipeline skip, yaml, generator"
```

---

### Task 4: Frontend — types + store

**Files:**
- Modify: `configforge-web/src/types/wizard.ts`
- Modify: `configforge-web/src/stores/wizard.ts`
- Modify: `configforge-web/src/utils/serialization.ts`

- [ ] **Step 1: ProcessorStep → discriminated union**

```typescript
// configforge-web/src/types/wizard.ts — replace ProcessorStep

export type ProcessorStep =
  | {
      name: string
      plugin: 'sql'
      sql: string
      inputTables: string[]
      outputTables: string[]
    }
  | {
      name: string
      plugin: 'python'
      script: string
      inputTables: string[]
      outputTables: string[]
    }
```

- [ ] **Step 2: Update serialization.ts**

```typescript
// configforge-web/src/utils/serialization.ts — in stateToSnakeCase
processors: state.processors.map((p) => {
  const base = {
    name: p.name,
    plugin: p.plugin,
    input_tables: p.inputTables,
    output_tables: p.outputTables,
  }
  if (p.plugin === 'python') {
    return { ...base, config: { type: 'python', script: p.script } }
  }
  return { ...base, config: { type: 'sql', sql: p.sql } }
}),
```

- [ ] **Step 3: Update wizard store — 6 sql references**

```typescript
// configforge-web/src/stores/wizard.ts

// addProcessor — add python support:
function addProcessor(plugin: 'sql' | 'python' = 'sql') {
  if (plugin === 'python') {
    processors.value.push({ name: '', plugin: 'python', script: '', inputTables: [], outputTables: [] })
  } else {
    processors.value.push({ name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: [] })
  }
}

// canProceed (line ~20):
if (currentStep.value === 3) {
  return processors.value.length > 0
    && processors.value.every(p => p.plugin === 'sql' ? p.sql.trim().length > 0 : p.script.trim().length > 0)
    && processors.value.every(p => p.outputTables.length > 0)
}

// stepValidation (line ~33):
processors.value.forEach((p, i) => {
  const codeEmpty = p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()
  if (codeEmpty) msgs.push(`步骤 ${i + 1}: 代码不能为空`)
  if (p.outputTables.length === 0) msgs.push(`步骤 ${i + 1}: 输出表名不能为空`)
})

// setProcessors (line ~75):
const valid = newProcessors.filter(p => p.plugin === 'sql' ? p.sql.trim() : p.script.trim())

// resetAll (line ~100):
processors.value = [{ name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: [] }]

// loadFromConfigState (line ~141):
sql: raw.config?.sql || raw.sql || '',
script: raw.config?.script || raw.script || '',
plugin: raw.plugin || 'sql',
```

- [ ] **Step 4: Run tests**

```bash
cd configforge-web && npx vitest run tests/
```
Expected: TypeScript errors at unconverted `.sql` refs (will be fixed in Task 5)

- [ ] **Step 5: Commit**

```bash
git add configforge-web/src/types/wizard.ts configforge-web/src/stores/wizard.ts configforge-web/src/utils/serialization.ts
git commit -m "feat: frontend types and store for Python processor — discriminated union"
```

---

### Task 5: Frontend — UI components

**Files:**
- Create: `configforge-web/src/components/step3/PythonProcessorContent.vue`
- Modify: `configforge-web/src/components/step3/ProcessorCard.vue`
- Modify: `configforge-web/src/components/step3/SqlEditorTab.vue`
- Modify: `configforge-web/src/views/ConfigWizardView.vue`
- Modify: `configforge-web/src/components/step4/ExportActions.vue`
- Modify: `configforge-web/src/components/step3/OutputConfigTab.vue`
- Create: `configforge-web/src/components/step3/SqlProcessorContent.vue` (extract from ProcessorCard)

- [ ] **Step 1: Extract SqlProcessorContent from ProcessorCard**

Move the SQL-specific part of ProcessorCard (SQL editor, runQuery, etc.) into a new `SqlProcessorContent.vue` component. Pass `proc` and `index` as props. The component emits `update` events.

- [ ] **Step 2: Create PythonProcessorContent.vue**

```vue
<template>
  <div class="space-y-3">
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">
        <span class="text-red-500">*</span> Python 脚本
      </label>
      <NInput
        :value="proc.script"
        @update:value="(v: string) => $emit('update', { script: v })"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 20 }"
        placeholder="def process(ctx):&#10;    conn = ctx.db.connection&#10;    conn.execute('CREATE TABLE result AS ...')"
        class="font-mono text-sm"
      />
    </div>
    <div class="flex gap-2">
      <NButton size="tiny" type="info" :loading="dryRunRunning" :disabled="!proc.script.trim()" @click="runPreview">▶ 预览结果</NButton>
      <NButton size="tiny" :disabled="!aiConfigured" @click="$emit('ai-generate')">✨ AI 生成</NButton>
    </div>
    <p v-if="dryRunError" class="text-xs text-red-500">{{ dryRunError }}</p>
    <div v-if="dryRunResult && dryRunVisible" class="space-y-2 mt-2">
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">共 {{ dryRunResult.length }} 个表</span>
        <NButton text size="tiny" @click="dryRunVisible = false">收起</NButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi, useAiApi } from '../../composables/useWizardApi'
import ColumnPreview from '../step2/ColumnPreview.vue'

const props = defineProps<{ proc: { plugin: 'python'; script: string; inputTables: string[]; outputTables: string[] }; index: number }>()
const emit = defineEmits<{ update: [p: Partial<{ script: string }>]; 'ai-generate': [] }>()
const store = useWizardStore()
const { dryRun: runDryRunApi, error: wizardApiError } = useWizardApi()
const { getAiSettings } = useAiApi()

const dryRunRunning = ref(false)
const dryRunResult = ref<any[] | null>(null)
const dryRunError = ref('')
const dryRunVisible = ref(false)
const aiConfigured = ref(false)

async function runPreview() {
  dryRunError.value = ''
  dryRunResult.value = null
  dryRunRunning.value = true
  const result = await runDryRunApi(store.$state)
  if (result?.tables?.length) {
    const inputTables = new Set(store.inputs.map(inp => inp.table).filter(Boolean))
    dryRunResult.value = result.tables.filter((t: any) => !inputTables.has(t.table_name))
    dryRunVisible.value = true
  } else {
    const apiMsg = wizardApiError.value?.message || ''
    dryRunError.value = apiMsg ? `预览执行失败: ${apiMsg}` : '预览执行失败，请检查输入配置'
  }
  dryRunRunning.value = false
}

getAiSettings().then(s => { aiConfigured.value = !!(s?.api_key) })
</script>
```

- [ ] **Step 3: Update ProcessorCard — v-if branch**

Replace the SQL-specific content area with:
```vue
<SqlProcessorContent
  v-if="proc.plugin === 'sql'"
  :proc="proc"
  :index="index"
  @update="(p) => $emit('update', p)"
/>
<PythonProcessorContent
  v-else-if="proc.plugin === 'python'"
  :proc="proc"
  :index="index"
  @update="(p) => $emit('update', p)"
/>
```

Import `SqlProcessorContent` and `PythonProcessorContent`. The type tag in header changes dynamically: `<NTag :type="proc.plugin === 'sql' ? 'info' : 'warning'">{{ proc.plugin === 'sql' ? 'SQL' : 'Python' }}</NTag>`

- [ ] **Step 4: Update SqlEditorTab — add "+ Python 步骤"**

```vue
<NButton size="small" type="warning" dashed @click="addPythonProcessor">+ Python 步骤</NButton>
```

```typescript
function addPythonProcessor() {
  store.addProcessor('python')
  expandedIndex.value = store.processors.length - 1
}
```

- [ ] **Step 5: Fix ConfigWizardView — 5 sql references**

```typescript
// Line 113 — pulse CTA:
store.processors.some(p => (p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim()) || !p.outputTables.length)

// Line 122 — disabled:
store.processors.length > 0 && store.processors.every(p => (p.plugin === 'sql' ? p.sql.trim() && p.outputTables.length : p.script.trim() && p.outputTables.length))

// Line 123-124 — validation msg:
store.processors.some(p => p.plugin === 'sql' ? !p.sql.trim() : !p.script.trim())
  ? '请输入代码'
  : '请输入输出表名'

// Line 373 — AI context:
sql: p.plugin === 'sql' ? p.sql : p.script

// Line 552 — onOrchestrateConfirm:
plugin: (s.plugin || 'sql') as 'sql' | 'python',
...s.plugin === 'python' ? { script: s.script || '' } : { sql: s.sql || '' },
```

- [ ] **Step 6: Fix ExportActions — sql reference**

```typescript
// configforge-web/src/components/step4/ExportActions.vue ~line 101
processors: store.processors.map(p => ({
  plugin: p.plugin,
  ...(p.plugin === 'python' ? { script: p.script } : { sql: p.sql }),
  inputTables: p.inputTables,
  outputTables: p.outputTables,
  name: p.name,
})),
```

- [ ] **Step 7: Fix OutputConfigTab — 4 sql references**

```typescript
// Line 235: p.plugin === 'sql' ? p.sql : p.script
// Line 273: const p = store.processors[0]; (p.plugin === 'sql' ? p.sql.trim() : p.script.trim())
// Line 274: p.plugin === 'sql' ? p.sql : p.script
// Line 320: p.plugin === 'sql' ? p.sql : p.script
```

- [ ] **Step 8: Run tests + TypeScript check**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run tests/
```
Expected: 0 TS errors, all tests pass

- [ ] **Step 9: Commit**

```bash
git add configforge-web/src/components/step3/
git commit -m "feat: Python processor UI — card, editor, +Python button, all sql refs adapted"
```

---

### Task 6: Full regression + release

- [ ] **Step 1: Backend tests**

```bash
PYTHONPATH=src:$PYTHONPATH python3 -m pytest tests/ configforge/tests/ -q
```
Expected: all pass (257+ baseline)

- [ ] **Step 2: Frontend tests**

```bash
cd configforge-web && npx vitest run tests/
```
Expected: all pass

- [ ] **Step 3: TypeScript check**

```bash
cd configforge-web && npx vue-tsc --noEmit
```
Expected: 0 errors

- [ ] **Step 4: Manual smoke test**

- Create new config → Step 3 → click "+ Python 步骤"
- Write `def process(ctx): ctx.db.execute("CREATE TABLE result AS SELECT 1 AS n")`
- Set output_tables: `["result"]`
- Upload a file → click "预览结果" → verify no crash

- [ ] **Step 5: Tag release**

```bash
git tag -a v0.4.0 -m "v0.4.0 — Python processor support"
```
