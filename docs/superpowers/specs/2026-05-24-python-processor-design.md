# ConfigForge Python 处理器 v0.4.0 设计

> 日期: 2026-05-24
> 当前基线: v0.3.1（SQL 多步管道 + AI 编排）

---

## 一、目标

新增 Python Processor，用户可编写 Python 脚本作为处理步骤，与 SQL 步骤在 DAG 中自由串联。

---

## 二、执行模型

**方案 C — 信任执行**：Python 代码在引擎同进程中直接执行，与当前 Jinja2 模板执行方式一致。适用场景为内部工具，用户为可信团队成员。

---

## 三、ctx API

```python
def process(ctx):
    # ctx.db — SQLite 连接
    rows = ctx.db.query('SELECT * FROM person')
    ctx.db.execute('CREATE TABLE result AS ...')

    # ctx.params — 运行时参数
    threshold = ctx.params.get('min_age', 18)

    # ctx.logger — 日志
    ctx.logger.info(f'处理了 {len(rows)} 行')
```

---

## 四、前端 UI

- Python 卡片与 SQL 卡片样式一致（类型标签颜色区分：SQL 蓝色、Python 橙色）
- 代码编辑器用 `<NInput type="textarea">`，与 SQL 编辑器一致
- 后续按需升级为 Monaco Editor
- Step 3 按钮栏新增"+ Python 步骤"按钮

---

## 五、YAML 模型

```yaml
processors:
  - name: 数据清洗
    plugin: python
    input_tables: [person]
    output_tables: [adults]
    config:
      type: python
      script: |
        def process(ctx):
            ctx.db.execute('CREATE TABLE adults AS SELECT * FROM person WHERE age >= 18')
```

**PipeForge 模型**：新增 `PythonProcessorConfig`，`ProcessorSpec.config` 的 discriminated union 加入此类型。

---

## 六、改动清单

| 层 | 文件 | 改动 |
|-----|------|------|
| PipeForge | `src/pipeforge/config/models.py` | 新增 `PythonProcessorConfig`，扩展 `ProcessorSpec.config` union |
| PipeForge | `src/pipeforge/plugins/processor/python.py` | **新建** Python Processor 插件 |
| ConfigForge | `configforge/models/wizard.py` | 前端 `ProcessorConfig` 支持 `plugin: "python"` |
| ConfigForge | `configforge/services/yaml_builder.py` | YAML 序列化 Python 步骤 |
| Frontend | `configforge-web/src/types/wizard.ts` | `ProcessorStep.plugin` 扩展 `"python"` |
| Frontend | `configforge-web/src/stores/wizard.ts` | `addProcessor` 支持 python 类型 |
| Frontend | `configforge-web/src/components/step3/ProcessorCard.vue` | Python 卡片 UI |
| Frontend | `configforge-web/src/components/step3/SqlEditorTab.vue` | 新增"+ Python 步骤"按钮 |

---

## 七、非目标

- 沙箱/安全隔离（采用信任模型）
- Monaco Editor 代码编辑器
- AI 编排生成 Python 步骤
- Python 步骤中网络请求/文件系统访问（ctx 只暴露 db/params/logger）

---

## 八、验证策略

- PipeForge：Python 插件注册、config 模型校验、管道执行
- ConfigForge：YAML 序列化 Python 步骤、前后端 camelCase 兼容
- Frontend：Python 卡片渲染、与 SQL 步骤混合链
- 全量回归：现有 257 backend + 113 frontend tests
