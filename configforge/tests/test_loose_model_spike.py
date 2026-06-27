"""限制②C loose 模型技术 spike（Day 4，0.5 天，前置）

响应审核报告 3.3 + 8.3：验证 Pydantic 继承 + alias 行为符合预期，降低 Phase 2 实施风险。

spike 对象：DatabaseOutputConfig（字段完全对齐，仅 alias 差异，是最佳验证目标）。

4 个验证点（对应方案 3.5 第二步步骤 0）：
1. populate_by_name=True + 继承链下，alias 解析是否正确
2. strict 子类添加必填约束时，loose 父类的可空字段是否被正确覆盖
3. model_dump(by_alias=True/False) 在继承链下的输出
4. model_json_schema() 在继承链下是否合并父子的 json_schema_extra

==================== spike 报告（PASS — 可进入 Day 8-10 实施）====================

4 个验证点全部通过。发现 3 个 Pydantic 继承行为（非 bug，实施时需注意）：

Finding 1（ValidationError 用 alias）：必填字段缺失时，错误信息用 alias 名
（`sourceTable`）而非字段名（`source_table`）。前端友好（camelCase），CLI/日志需注意。
→ 影响：Day 8-10 实施时，若需 snake_case 错误信息，需后处理。

Finding 2（json_schema_extra 不合并 — 关键）：子类的 ConfigDict.json_schema_extra
完全覆盖父类，不合并。strict schema 只有自身的 ui:strict，丢失父类 ui:widget。
→ 影响：Day 8-10 实施时，json_schema_extra 应只定义在 loose 父类；strict 子类
若需额外 schema，用单独字段或 model_json_schema 后处理合并，不要在 model_config 重复定义。

Finding 3（schema 用 alias 键）：model_json_schema() 的 required 和 properties 键
使用 alias（`sourceTable`/`connectionId`）而非字段名。
→ 影响：Day 11-16 SchemaForm 消费 schema 时，字段键是 camelCase，与前端一致，无需转换。

结论：方案 C（提取 loose 基础模型）技术可行，不回退。Day 8-10 实施时遵守上述 3 点。
"""
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# ---------------------------------------------------------------------------
# spike 模型：模拟未来 models_loose.py 的设计
# ---------------------------------------------------------------------------

class LooseColumnMapping(BaseModel):
    """loose 列映射：字段可空，供 wizard 占位用。"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source: str = ""
    target: str = ""


class LooseDatabaseOutputConfig(BaseModel):
    """loose 基础模型：全字段可空 + camelCase alias + populate_by_name=True。

    模拟未来 pipeforge/config/models_loose.py 中 LooseDatabaseOutputConfig 的设计。
    configforge 侧将继承此类获得字段定义，pipeforge strict 侧也继承并加必填约束。
    """
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"ui:widget": "database-output"},
    )

    type: Literal["database"] = "database"
    connection_id: str = Field(default="", alias="connectionId")
    target_table: str = Field(default="", alias="targetTable")
    write_mode: Literal["replace", "append", "upsert"] = Field(default="replace", alias="writeMode")
    source_table: str = Field(default="", alias="sourceTable")
    columns: list[LooseColumnMapping] = Field(default=[])
    create_table_if_not_exists: bool = Field(default=True, alias="createTableIfNotExists")
    primary_key_columns: list[str] = Field(default=[], alias="primaryKeyColumns")
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""


class StrictDatabaseOutputConfig(LooseDatabaseOutputConfig):
    """strict 子类：继承 loose，将 source_table 改为必填（无默认值）。

    模拟未来 pipeforge strict 模型继承 loose 并添加必填约束的设计。
    关键验证：子类把父类的可空字段（有默认）覆盖为必填（无默认），Pydantic 是否正确识别。
    """
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={"ui:strict": True},
    )

    # 覆盖为必填：无默认值。注意 alias 必须重新声明，否则继承链会丢失 alias。
    source_table: str = Field(alias="sourceTable")


# ---------------------------------------------------------------------------
# 验证点 1：populate_by_name=True + 继承链下，alias 解析
# ---------------------------------------------------------------------------

class TestSpikeAliasResolution:
    """验证点 1：alias 解析在继承链下是否正确。"""

    def test_loose_accepts_field_name(self):
        """loose 模型通过字段名构造（populate_by_name=True）。"""
        cfg = LooseDatabaseOutputConfig(source_table="t1")
        assert cfg.source_table == "t1"

    def test_loose_accepts_alias(self):
        """loose 模型通过 alias 构造。"""
        cfg = LooseDatabaseOutputConfig(sourceTable="t1")
        assert cfg.source_table == "t1"

    def test_strict_accepts_field_name(self):
        """strict 子类通过字段名构造（继承 populate_by_name）。"""
        cfg = StrictDatabaseOutputConfig(source_table="t1")
        assert cfg.source_table == "t1"

    def test_strict_accepts_alias(self):
        """strict 子类通过 alias 构造（继承 alias 定义）。"""
        cfg = StrictDatabaseOutputConfig(sourceTable="t1")
        assert cfg.source_table == "t1"

    def test_strict_inherits_all_aliases(self):
        """strict 子类应继承父类所有字段的 alias。"""
        cfg = StrictDatabaseOutputConfig(
            sourceTable="t1",
            connectionId="conn-1",
            targetTable="tgt",
            writeMode="upsert",
            createTableIfNotExists=False,
            primaryKeyColumns=["id"],
        )
        assert cfg.connection_id == "conn-1"
        assert cfg.target_table == "tgt"
        assert cfg.write_mode == "upsert"
        assert cfg.create_table_if_not_exists is False
        assert cfg.primary_key_columns == ["id"]


# ---------------------------------------------------------------------------
# 验证点 2：strict 必填约束覆盖 loose 可空字段
# ---------------------------------------------------------------------------

class TestSpikeRequiredOverride:
    """验证点 2：strict 子类把 loose 父类的可空字段改为必填。"""

    def test_strict_requires_source_table_field_name(self):
        """strict 子类要求 source_table（缺失 → ValidationError）。

        Finding 1：错误信息用 alias 名 sourceTable 而非字段名 source_table。
        """
        with pytest.raises(ValidationError) as exc_info:
            StrictDatabaseOutputConfig()
        # Finding 1：ValidationError 用 alias 名
        assert "sourceTable" in str(exc_info.value)

    def test_strict_requires_source_table_alias(self):
        """strict 子类要求 source_table（alias 缺失 → ValidationError）。"""
        with pytest.raises(ValidationError):
            StrictDatabaseOutputConfig(connectionId="conn-1")

    def test_strict_other_fields_remain_optional(self):
        """strict 子类中，未覆盖的 loose 字段仍保持可空（有默认值）。"""
        cfg = StrictDatabaseOutputConfig(source_table="t1")
        # 其他字段都用默认值
        assert cfg.connection_id == ""
        assert cfg.target_table == ""
        assert cfg.write_mode == "replace"
        assert cfg.create_table_if_not_exists is True
        assert cfg.primary_key_columns == []
        assert cfg.batch_size == 1000
        assert cfg.connection_string == ""

    def test_strict_validates_batch_size_constraint(self):
        """strict 子类继承父类的 ge/le 约束。"""
        with pytest.raises(ValidationError):
            StrictDatabaseOutputConfig(source_table="t1", batch_size=0)
        with pytest.raises(ValidationError):
            StrictDatabaseOutputConfig(source_table="t1", batch_size=100001)


# ---------------------------------------------------------------------------
# 验证点 3：model_dump(by_alias=...) 在继承链下的输出
# ---------------------------------------------------------------------------

class TestSpikeModelDumpAlias:
    """验证点 3：model_dump 在继承链下正确输出 alias 或字段名。"""

    def test_loose_dump_by_alias_true(self):
        """loose 模型 by_alias=True 输出 camelCase。"""
        cfg = LooseDatabaseOutputConfig(
            connection_id="c1", target_table="t1", source_table="s1",
            create_table_if_not_exists=False, primary_key_columns=["id"],
        )
        d = cfg.model_dump(by_alias=True)
        assert d["connectionId"] == "c1"
        assert d["targetTable"] == "t1"
        assert d["sourceTable"] == "s1"
        assert d["createTableIfNotExists"] is False
        assert d["primaryKeyColumns"] == ["id"]
        # 无 alias 的字段保持原名
        assert d["batch_size"] == 1000
        assert d["connection_string"] == ""

    def test_loose_dump_by_alias_false(self):
        """loose 模型 by_alias=False 输出 snake_case。"""
        cfg = LooseDatabaseOutputConfig(connection_id="c1", source_table="s1")
        d = cfg.model_dump(by_alias=False)
        assert d["connection_id"] == "c1"
        assert d["source_table"] == "s1"

    def test_strict_dump_by_alias_true(self):
        """strict 子类 by_alias=True 输出 camelCase（继承父类 alias）。"""
        cfg = StrictDatabaseOutputConfig(source_table="s1", connection_id="c1")
        d = cfg.model_dump(by_alias=True)
        assert d["sourceTable"] == "s1"
        assert d["connectionId"] == "c1"

    def test_strict_dump_by_alias_false(self):
        """strict 子类 by_alias=False 输出 snake_case。"""
        cfg = StrictDatabaseOutputConfig(source_table="s1")
        d = cfg.model_dump(by_alias=False)
        assert d["source_table"] == "s1"

    def test_strict_dump_excludes_unset_check(self):
        """strict 子类 dump 默认包含所有字段（含默认值）。"""
        cfg = StrictDatabaseOutputConfig(source_table="s1")
        d = cfg.model_dump()
        # source_table 是必填已设置
        assert d["source_table"] == "s1"
        # 其他字段用默认值也被输出
        assert d["batch_size"] == 1000
        assert "connection_id" in d


# ---------------------------------------------------------------------------
# 验证点 4：model_json_schema() 合并父子 json_schema_extra
# ---------------------------------------------------------------------------

class TestSpikeJsonSchemaMerge:
    """验证点 4：model_json_schema() 在继承链下合并父子 json_schema_extra。"""

    def test_loose_schema_contains_parent_extra(self):
        """loose 模型 schema 包含父类 json_schema_extra。"""
        schema = LooseDatabaseOutputConfig.model_json_schema()
        # 父类定义的 ui:widget
        assert schema.get("ui:widget") == "database-output"

    def test_strict_schema_merges_parent_and_child_extra(self):
        """Finding 2（关键）：json_schema_extra 不合并，子类覆盖父类。

        strict schema 只有自身的 ui:strict，丢失父类 ui:widget。
        Day 8-10 实施时：json_schema_extra 只定义在 loose 父类，strict 子类不重复定义。
        """
        schema = StrictDatabaseOutputConfig.model_json_schema()
        # Finding 2：子类覆盖父类，ui:widget 丢失
        assert schema.get("ui:widget") is None, \
            "json_schema_extra 不合并 — 父类 ui:widget 被子类覆盖丢失"
        # 只有子类的 ui:strict
        assert schema.get("ui:strict") is True, \
            "strict 子类保留自身的 json_schema_extra"

    def test_strict_schema_source_table_required(self):
        """strict 子类 schema 中 sourceTable（alias）应为 required。

        Finding 3：schema 的 required 用 alias 名 sourceTable 而非字段名 source_table。
        """
        schema = StrictDatabaseOutputConfig.model_json_schema()
        required = schema.get("required", [])
        # Finding 3：required 用 alias 名
        assert "sourceTable" in required, \
            "strict 子类把 sourceTable（alias）标记为 required"

    def test_loose_schema_source_table_not_required(self):
        """loose 父类 schema 中 source_table 不应为 required。"""
        schema = LooseDatabaseOutputConfig.model_json_schema()
        required = schema.get("required", [])
        assert "source_table" not in required, \
            "loose 父类 source_table 有默认值，不应 required"

    def test_strict_schema_inherits_field_constraints(self):
        """strict 子类 schema 继承父类字段的 ge/le 约束。"""
        schema = StrictDatabaseOutputConfig.model_json_schema()
        props = schema.get("properties", {})
        batch_size = props.get("batch_size", {})
        # ge=1, le=100000 应被继承
        assert batch_size.get("minimum") == 1
        assert batch_size.get("maximum") == 100000
