# Phase 3: 执行历史与结果管理 — 实施计划 (简版)

> **Goal:** 持久化执行记录，支持历史查看、输出下载、配置版本关联。

**Architecture:** 文件系统 `data/executions/{exec_id}/result.json + output file`，API 层在执行后保存记录而非清理。

---

## Tasks

| Task | 文件 | 内容 |
|------|------|------|
| 1 | `configforge/models/wizard.py` | ExecutionRecord 模型 |
| 2 | `configforge/core/pipeline.py` | execute_pipeline 返回 output_path + 保留文件（不再由 BackgroundTasks 清理） |
| 3 | `configforge/api/wizard.py` | api_execute 完成后保存 ExecutionRecord 到 data/executions/ |
| 4 | `configforge/api/configs.py` | execute_config 同上 |
| 5 | `configforge/api/executions.py` (新增) | 执行历史 CRUD API |
| 6 | `configforge/tests/api/test_executions.py` (新增) | API 测试 |
| 7 | `configforge-web/src/views/ExecutionHistoryView.vue` (新增) | 执行历史页面 |
| 8 | 路由注册 + 导航 | 新增 /history 路由 |

---

## Task 1: ExecutionRecord 模型

**File:** `configforge/models/wizard.py`，末尾添加：

```python
class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str  # 8-char hex
    config_id: str
    config_version: int | None = None
    scene_name: str
    status: Literal["success", "failed"] = "success"
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    inputs_summary: list[dict] = []
    processors_summary: list[dict] = []
    output_type: str = ""
    checks_summary: list[dict] = []
    error_message: str | None = None
    output_file_name: str | None = None
```

## Task 2: api_execute 保存执行记录

**File:** `configforge/api/wizard.py`，修改 `api_execute`：

```python
@router.post("/execute")
async def api_execute(req: GenerateRequest, background_tasks: BackgroundTasks):
    import time, uuid
    from configforge.models.wizard import ExecutionRecord

    exec_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC).isoformat()
    
    try:
        output_path = execute_pipeline(req.state)
        duration_ms = int((datetime.now(UTC) - datetime.fromisoformat(started_at)).total_seconds() * 1000)
        
        # Persist output file to executions dir
        exec_dir = os.path.join(DATA_DIR, "executions", exec_id)
        os.makedirs(exec_dir, exist_ok=True)
        filename = os.path.basename(output_path)
        output_dest = os.path.join(exec_dir, filename)
        shutil.move(output_path, output_dest)
        
        # Save execution record
        record = ExecutionRecord(
            id=exec_id, config_id="adhoc", scene_name=req.state.scene.name,
            status="success", started_at=started_at,
            finished_at=datetime.now(UTC).isoformat(), duration_ms=duration_ms,
            inputs_summary=[{"name": i.name, "plugin": i.plugin} for i in req.state.inputs],
            processors_summary=[{"plugin": p.plugin, "name": p.name} for p in req.state.processors],
            output_type=req.state.output.plugin if req.state.output else "",
            output_file_name=filename,
        )
        with open(os.path.join(exec_dir, "result.json"), "w") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)
        
        # Update index
        _update_exec_index(record)
        
        return FileResponse(output_dest, media_type=..., filename=filename)
    except Exception as e:
        # Save failed record
        duration_ms = int((datetime.now(UTC) - datetime.fromisoformat(started_at)).total_seconds() * 1000)
        exec_dir = os.path.join(DATA_DIR, "executions", exec_id)
        os.makedirs(exec_dir, exist_ok=True)
        record = ExecutionRecord(
            id=exec_id, config_id="adhoc", scene_name=req.state.scene.name,
            status="failed", started_at=started_at,
            finished_at=datetime.now(UTC).isoformat(), duration_ms=duration_ms,
            error_message=str(e),
        )
        with open(os.path.join(exec_dir, "result.json"), "w") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)
        _update_exec_index(record)
        raise
```

## Task 3: 执行历史 API

**File:** `configforge/api/executions.py`（新增），提供：
- `GET /api/executions` — 列表，支持 ?config_id= 过滤
- `GET /api/executions/{exec_id}` — 详情
- `GET /api/executions/{exec_id}/download` — 下载输出文件
- `DELETE /api/executions/{exec_id}` — 删除记录和文件

## Task 4: 前端执行历史页面

**File:** `configforge-web/src/views/ExecutionHistoryView.vue`（新增）

表格展示：时间、配置名、状态标签、耗时、操作（查看详情/下载/删除）

## Task 5: 注册路由

修改 router 配置，添加 `/history` → `ExecutionHistoryView`。在导航栏添加"执行历史"入口。

---

## 简化说明

为控制范围，Phase 3 做以下简化：
1. 只统计总 duration_ms，暂不做 per-processor 计时
2. 敏感信息脱敏简化为：连接字符串在 summary 中替换为 `"***"`
3. 前端只做列表+详情弹窗，不做复杂图表
