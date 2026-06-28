# CCTEST 项目架构审查报告

**审查版本：** v0.8.1 | **审查时间：** 2026-06-27

---

## 架构全景

```
configforge-web (Vue3 + TS + Pinia)   ← 前端层
configforge (FastAPI + SQLAlchemy)     ← API / 编排层
pipeforge (Python 插件引擎)            ← 执行引擎层
```

三层解耦，底层引擎 YAML 驱动、插件化；中层 FastAPI 负责配置管理、AI 编排、执行调度；前端向导式生成配置。

---

## 优点

1. **插件架构设计优雅** — `base.py` 泛型 `Plugin[C]` 类型安全，新增插件只需实现两个方法
2. **存储层抽象到位** — Protocol + 环境变量切换后端（json/sqlite/pg），设计正确
3. **安全加固多层次** — 路径遍历拦截、API Key 脱敏、参数校验、超时保护
4. **SSE 执行进度设计合理** — `asyncio.to_thread` + 事件推送，复用成功/失败处理逻辑
5. **AI 服务 provider 抽象** — `LlmBackend(ABC)` + 工厂模式，懒 import 避免强依赖

---

## 问题（按严重程度）

### 🔴 严重

**1. Service 反向依赖 API 层**
- `services/execution_service.py:17-22` import 了 `api/executions` 的私有函数
- `services/notifier/dispatcher.py:11` 同样反向依赖 `api/notifications`
- 后果：service 无法独立测试，重构 API 层会静默断裂

**2. API 路由直接穿透到 Storage**
- `api/configs.py:33`、`api/connections.py:7` 等直接 import `configforge.storage`
- 正确路径应是 `api → service → storage`，现在部分绕过 service

**3. 强耦合 PipeForge 私有 API**
- `execution_service.py:442,453,481` 直接调用 `engine._execute_input()` 等私有方法
- 代价：PipeForge 任何重构会立即破坏 ConfigForge
- 根因：为了 SSE 实时进度，绕过了公共 API `engine.execute()`

### 🟠 中等

**4. 超长文件与上帝模块**
- `api/configs.py` 752 行（CRUD + 版本 + import/export 全在一个文件）
- `api/ai.py` 662 行（含 3 套规则引擎 + prompt 拼装）
- `services/execution_service.py` 565 行（`execute()` 与 `execute_with_progress()` 大量重复）

**5. ConfigStoreProtocol 半成品**
- Protocol 定义了但未使用，`api/configs.py` 仍直接引用 `services/config_store` 私有函数
- 切换存储后端时 config 行为仍依赖 JSON 文件实现细节

### 🟡 轻微

**6. 开发/生产行为不一致** — `server.py:166` CORS fallback 硬编码 localhost:5173-5175

**7. signal 超时不可移植** — `SIGALRM` 在 Windows 上报 AttributeError

**8. 通知去重在进程内** — `_last_trigger_times` 多 worker 部署时失效

**9. AI 调用无重试** — 只有超时，无 tenacity 重试；错误分类靠字符串匹配

---

## 改进建议

### P0（立即修复）
- 把 `_save_failed_execution` 等移到 service 层，解除 service→api 反向依赖
- 引入 `ConfigService` 等 service 类，解除 api→storage 穿透
- 在 `PipelineEngine` 新增公共 `execute_with_callback()` 或暴露 `_execute_*` 为公共 API

### P1（近期重构）
- 拆分 `api/configs.py` 为 service 方法
- 完成 `ConfigStoreProtocol` 落地
- 抽离 AI 规则引擎到 `services/ai/rules/`
- Windows 超时兼容（用 `threading.Timer` 替代 `SIGALRM`）

### P2（长期优化）
- AI 调用加 tenacity 重试
- 通知去重改用 Redis / 数据库
- 错误分类用 Enum 替代字符串匹配
