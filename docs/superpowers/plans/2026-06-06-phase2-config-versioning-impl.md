# Phase 2: 配置版本管理 — 实施计划

> **Goal:** 配置保存时自动创建版本快照，支持查看版本历史、对比差异、回滚到历史版本。

**Architecture:** 文件系统版本目录 `{config_id}/v{n}.state.json`，每次保存递增版本号，回滚采用追加式（创建新版本 = 旧版本内容）。

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, deepdiff, Vue 3 + Naive UI, TypeScript

---

## 文件结构

| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `configforge/models/wizard.py` | ConfigMeta 增加字段，新增 ConfigVersionMeta |
| 修改 | `configforge/api/configs.py` | save_config 版本递增 + 历史目录，新 API 端点 |
| 修改 | `configforge-web/src/views/HomeView.vue` | 配置卡片增加"版本历史"入口 |
| 新增 | `configforge-web/src/components/config/ConfigVersionPanel.vue` | 版本历史面板 + 对比 + 回滚 |
| 新增 | `configforge/tests/api/test_config_versions.py` | API 测试 |
| 新增 | `configforge-web/tests/components/ConfigVersionPanel.test.ts` | 组件测试 |

---

## Task 1: 后端 — 数据模型更新

**File:** `configforge/models/wizard.py`

### Step 1: 更新 ConfigMeta

在 `ConfigMeta` 类中增加 `current_version`, `created_at` 字段：

```python
class ConfigMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    scene_name: str
    description: str = ""
    input_count: int = 0
    output_type: str = ""
    version: str = "1.0"           # user-facing scene version
    current_version: int = 1       # auto-incremented config version
    created_at: str = ""
    updated_at: str = ""
    inputs: list[ConfigInputMeta] = []
```

### Step 2: 新增 ConfigVersionMeta

在文件末尾添加：

```python
class ConfigVersionMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    scene_version: str = "1.0"
    change_summary: str = ""
    created_at: str = ""
    input_count: int = 0
    processor_count: int = 0
    output_type: str = ""
```

---

## Task 2: 后端 — save_config 版本递增

**File:** `configforge/api/configs.py`

### Step 1: 修改 save_config

在保存配置时，自动递增版本号并创建历史版本：

```python
@router.post("", response_model=SaveConfigResponse)
async def save_config(req: SaveConfigRequest):
    config_id = req.config_id or uuid.uuid4().hex

    state_dict = req.state.model_dump(by_alias=True)
    for inp in state_dict.get("inputs", []):
        inp["fileId"] = ""
    state_dict["uploaded_files"] = {}

    yaml_str = build_yaml(req.state)
    yaml_path = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
    state_path = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")

    # --- Version management ---
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    index = _load_index()
    existing = next((i for i, e in enumerate(index) if e.get("id") == config_id), None)

    if existing is not None:
        current_meta = index[existing]
        old_version = current_meta.get("current_version", 1)
        # Move current state to version history before overwriting
        os.makedirs(versions_dir, exist_ok=True)
        old_state = os.path.join(CONFIGS_DIR, f"{config_id}.state.json")
        old_yaml = os.path.join(CONFIGS_DIR, f"{config_id}.yaml")
        if os.path.exists(old_state):
            shutil.copy2(old_state, os.path.join(versions_dir, f"v{old_version}.state.json"))
        if os.path.exists(old_yaml):
            shutil.copy2(old_yaml, os.path.join(versions_dir, f"v{old_version}.yaml"))
        new_version = old_version + 1
    else:
        new_version = 1
        index.append({})

    # Write new current state
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state_dict, f, ensure_ascii=False, indent=2)
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # Update index metadata
    output_type = ""
    if req.state.output:
        output_type = req.state.output.plugin

    processor_count = len(req.state.processors)

    input_metas = [
        ConfigInputMeta(name=inp.name, param_key=inp.param_key, plugin=inp.plugin)
        for inp in req.state.inputs
    ]

    meta = ConfigMeta(
        id=config_id,
        scene_name=req.state.scene.name or "未命名配置",
        description=req.state.scene.description or "",
        input_count=len(req.state.inputs),
        output_type=output_type,
        version=req.state.scene.version or "1.0",
        current_version=new_version,
        created_at=existing_meta.get("created_at") if existing is not None else datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        inputs=input_metas,
    )

    if existing is not None:
        index[existing] = meta.model_dump()
    else:
        index[-1] = meta.model_dump()
    _save_index(index)

    return SaveConfigResponse(id=config_id)
```

---

## Task 3: 后端 — 版本列表 API

**File:** `configforge/api/configs.py`

```python
@router.get("/{config_id}/versions")
async def list_config_versions(config_id: str) -> list[ConfigVersionMeta]:
    _validate_config_id(config_id)
    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    if not os.path.isdir(versions_dir):
        return []

    versions = []
    for fname in sorted(os.listdir(versions_dir), key=lambda x: int(x.lstrip("v").split(".")[0])):
        if fname.endswith(".state.json"):
            v = int(fname.lstrip("v").split(".")[0])
            with open(os.path.join(versions_dir, fname), "r") as f:
                state = json.load(f)
            versions.append(ConfigVersionMeta(
                version=v,
                scene_version=state.get("scene", {}).get("version", "1.0"),
                created_at=state.get("_saved_at", ""),
                input_count=len(state.get("inputs", [])),
                processor_count=len(state.get("processors", [])),
                output_type=state.get("output", {}).get("plugin", ""),
            ))
    return versions
```

---

## Task 4: 后端 — 版本详情 + 对比 + 回滚 API

**File:** `configforge/api/configs.py`

### 4.1 获取版本 state JSON

```python
@router.get("/{config_id}/versions/{version}")
async def get_config_version(config_id: str, version: int):
    _validate_config_id(config_id)
    path = os.path.join(CONFIGS_DIR, config_id, f"v{version}.state.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Version not found")
    with open(path, "r") as f:
        return json.load(f)
```

### 4.2 版本对比

```python
@router.get("/{config_id}/diff")
async def diff_config_versions(config_id: str, v1: int, v2: int):
    _validate_config_id(config_id)
    from deepdiff import DeepDiff

    path1 = os.path.join(CONFIGS_DIR, config_id, f"v{v1}.state.json")
    path2 = os.path.join(CONFIGS_DIR, config_id, f"v{v2}.state.json")
    for p in [path1, path2]:
        if not os.path.exists(p):
            raise HTTPException(status_code=404, detail=f"Version not found: {p}")

    with open(path1) as f:
        s1 = json.load(f)
    with open(path2) as f:
        s2 = json.load(f)

    diff = DeepDiff(s1, s2, ignore_order=True, verbose_level=2)

    changes = []
    for change_type, items in diff.items():
        if isinstance(items, dict):
            for path, detail in items.items():
                changes.append({"type": change_type, "path": path, "detail": str(detail)})
        elif isinstance(items, (list, set)):
            for item in items:
                changes.append({"type": change_type, "detail": str(item)})

    return {"v1": v1, "v2": v2, "changes": changes}
```

### 4.3 回滚（追加式）

```python
@router.post("/{config_id}/versions/{version}/rollback")
async def rollback_config(config_id: str, version: int):
    _validate_config_id(config_id)
    target_path = os.path.join(CONFIGS_DIR, config_id, f"v{version}.state.json")
    target_yaml_path = os.path.join(CONFIGS_DIR, config_id, f"v{version}.yaml")
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Version not found")

    index = _load_index()
    existing = next((i for i, e in enumerate(index) if e.get("id") == config_id), None)
    if existing is None:
        raise HTTPException(status_code=404, detail="Config not found")

    with open(target_path) as f:
        state = json.load(f)

    meta = index[existing]
    old_version = meta.get("current_version", 1)
    new_version = old_version + 1

    versions_dir = os.path.join(CONFIGS_DIR, config_id)
    # Save old current as version history
    shutil.copy2(
        os.path.join(CONFIGS_DIR, f"{config_id}.state.json"),
        os.path.join(versions_dir, f"v{old_version}.state.json")
    )
    shutil.copy2(
        os.path.join(CONFIGS_DIR, f"{config_id}.yaml"),
        os.path.join(versions_dir, f"v{old_version}.yaml")
    )
    # Write target as new current
    shutil.copy2(target_path, os.path.join(CONFIGS_DIR, f"{config_id}.state.json"))
    if os.path.exists(target_yaml_path):
        shutil.copy2(target_yaml_path, os.path.join(CONFIGS_DIR, f"{config_id}.yaml"))

    meta["current_version"] = new_version
    meta["updated_at"] = datetime.now(UTC).isoformat()
    index[existing] = meta
    _save_index(index)

    return {"ok": True, "new_version": new_version, "rolled_back_from": f"v{version}"}
```

---

## Task 5: 后端 — API 测试

**File:** `configforge/tests/api/test_config_versions.py`

```python
"""Tests for config version management."""
import pytest
from fastapi.testclient import TestClient
import os
import json

from configforge.server import app
from configforge.api.configs import CONFIGS_DIR

client = TestClient(app)


@pytest.fixture
def clean_configs():
    # Clean up test config before/after
    yield
    for f in os.listdir(CONFIGS_DIR):
        path = os.path.join(CONFIGS_DIR, f)
        if os.path.isfile(path) and f.startswith("test_"):
            os.remove(path)


class TestConfigVersions:
    def test_first_save_creates_v1(self):
        resp = client.post("/api/configs", json={
            "state": {
                "currentStep": 1,
                "scene": {"name": "Test", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        assert resp.status_code == 200
        config_id = resp.json()["id"]

        # Verify version metadata
        index_resp = client.get("/api/configs")
        metas = [m for m in index_resp.json() if m["id"] == config_id]
        assert len(metas) == 1
        assert metas[0]["current_version"] == 1

    def test_second_save_creates_v2(self, clean_configs):
        # Create
        resp = client.post("/api/configs", json={
            "state": {
                "currentStep": 1,
                "scene": {"name": "Test V2", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Update (save again)
        resp2 = client.post("/api/configs", json={
            "configId": config_id,
            "state": {
                "currentStep": 2,
                "scene": {"name": "Test V2 Updated", "description": "changed", "version": "2.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        assert resp2.status_code == 200

        # Check versions
        versions = client.get(f"/api/configs/{config_id}/versions")
        assert versions.status_code == 200
        assert len(versions.json()) == 1  # v1 archived
        assert versions.json()[0]["version"] == 1

        # Check current
        state = client.get(f"/api/configs/{config_id}")
        assert state.json()["scene"]["name"] == "Test V2 Updated"
        assert state.json()["scene"]["description"] == "changed"

    def test_list_versions(self):
        resp = client.post("/api/configs", json={
            "state": {
                "currentStep": 1,
                "scene": {"name": "Versions Test", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Save 3 times
        for i in range(2, 5):
            client.post("/api/configs", json={
                "configId": config_id,
                "state": {
                    "currentStep": 1,
                    "scene": {"name": f"V{i}", "description": "", "version": "1.0"},
                    "inputs": [],
                    "processors": [],
                    "output": None,
                }
            })

        versions = client.get(f"/api/configs/{config_id}/versions")
        assert versions.status_code == 200
        # Should have v1, v2, v3 in history (current is v4)
        version_list = versions.json()
        assert len(version_list) == 3
        assert [v["version"] for v in version_list] == [1, 2, 3]

    def test_get_version_detail(self):
        resp = client.post("/api/configs", json={
            "state": {
                "currentStep": 1,
                "scene": {"name": "Detail Test", "description": "", "version": "1.0"},
                "inputs": [{"name": "test", "plugin": "excel", "table": "data", "paramKey": "f1", "config": {"type": "excel", "sheet": "Sheet1"}}],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Get current + verify it exists
        current = client.get(f"/api/configs/{config_id}")
        assert current.json()["scene"]["name"] == "Detail Test"

    def test_rollback(self):
        resp = client.post("/api/configs", json={
            "state": {
                "currentStep": 1,
                "scene": {"name": "Original", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Save update
        client.post("/api/configs", json={
            "configId": config_id,
            "state": {
                "currentStep": 1,
                "scene": {"name": "Modified", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })

        # Rollback to v1
        rollback = client.post(f"/api/configs/{config_id}/versions/1/rollback")
        assert rollback.status_code == 200
        assert rollback.json()["new_version"] == 3
```

---

## Task 6: 前端 — ConfigVersionPanel 组件

**File:** `configforge-web/src/components/config/ConfigVersionPanel.vue`

A panel that:
1. Shows version list with version number, scene version, timestamp
2. Click a version to see its state (opens in modal or expands)
3. Select two versions and click "对比"
4. "回滚到此版本" button with confirmation dialog

---

## 任务清单

| Task | 内容 |
|------|------|
| 1 | 数据模型更新 (ConfigMeta + ConfigVersionMeta) |
| 2 | save_config 版本递增逻辑 |
| 3 | 版本列表 API |
| 4 | 版本详情 + 对比 + 回滚 API |
| 5 | API 测试 |
| 6 | 前端版本面板组件 |
| 7 | 全量回归 |

**注意：Tasks 5+6 需要 `deepdiff` 依赖。在开始前运行 `pip3 install deepdiff`。**
