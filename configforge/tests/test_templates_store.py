"""Tests for TemplateStore and ensure_builtin_templates."""

import json

import pytest

from configforge.services import template_store
from configforge.services.template_store import TemplateStore, ensure_builtin_templates


@pytest.fixture(autouse=True)
def _use_tmp_data_dir(tmp_path, monkeypatch):
    """Redirect template store to a temp directory for each test."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    store_path = str(data_dir / "templates.json")
    monkeypatch.setattr(template_store, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(template_store, "STORE_PATH", store_path)
    template_store._cache.invalidate("templates")


# ---------------------------------------------------------------------------
# TestListTemplates
# ---------------------------------------------------------------------------

class TestListTemplates:
    def test_empty_store(self):
        """Listing templates on an empty store should return an empty list."""
        result = TemplateStore.list_templates()
        assert result == []

    def test_after_create(self):
        """After creating a template, list_templates should include it."""
        TemplateStore.create_template(
            name="My Template",
            description="desc",
            category="general",
            tags=["test"],
            config_state={"inputs": [], "processors": []},
        )
        result = TemplateStore.list_templates()
        assert len(result) == 1
        assert result[0]["name"] == "My Template"

    def test_category_filter(self):
        """Filtering by category should return only matching templates."""
        TemplateStore.create_template(
            name="Sales Report",
            description="desc",
            category="sales",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        TemplateStore.create_template(
            name="HR Report",
            description="desc",
            category="hr",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        result = TemplateStore.list_templates(category="sales")
        assert len(result) == 1
        assert result[0]["category"] == "sales"

    def test_search_filter(self):
        """Search should match name, description, and tags (case-insensitive)."""
        TemplateStore.create_template(
            name="Revenue Analyzer",
            description="Analyzes revenue streams",
            category="finance",
            tags=["quarterly"],
            config_state={"inputs": [], "processors": []},
        )
        TemplateStore.create_template(
            name="Headcount Report",
            description="Monthly headcount",
            category="hr",
            tags=["monthly"],
            config_state={"inputs": [], "processors": []},
        )
        # Match by name
        assert len(TemplateStore.list_templates(search="revenue")) == 1
        # Match by description
        assert len(TemplateStore.list_templates(search="revenue streams")) == 1
        # Match by tag
        assert len(TemplateStore.list_templates(search="quarterly")) == 1
        # No match
        assert len(TemplateStore.list_templates(search="nonexistent")) == 0

    def test_sort_order_official_first(self):
        """Official templates should appear before non-official ones."""
        TemplateStore.create_template(
            name="Community Template",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
            is_official=False,
        )
        TemplateStore.create_template(
            name="Official Template",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
            is_official=True,
        )
        result = TemplateStore.list_templates()
        assert result[0]["is_official"] is True
        assert result[1]["is_official"] is False

    def test_sort_order_by_usage_count(self):
        """Within the same official status, templates should sort by usage_count descending."""
        t1 = TemplateStore.create_template(
            name="Low Usage",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        t2 = TemplateStore.create_template(
            name="High Usage",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        # Increment usage for t2 three times
        TemplateStore.increment_usage(t2["id"])
        TemplateStore.increment_usage(t2["id"])
        TemplateStore.increment_usage(t2["id"])
        # Increment usage for t1 once
        TemplateStore.increment_usage(t1["id"])

        result = TemplateStore.list_templates()
        assert result[0]["name"] == "High Usage"
        assert result[1]["name"] == "Low Usage"


# ---------------------------------------------------------------------------
# TestGetTemplate
# ---------------------------------------------------------------------------

class TestGetTemplate:
    def test_existing_template(self):
        """get_template should return the template dict for an existing ID."""
        created = TemplateStore.create_template(
            name="Fetchable",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        result = TemplateStore.get_template(created["id"])
        assert result is not None
        assert result["name"] == "Fetchable"

    def test_non_existing_returns_none(self):
        """get_template should return None for a non-existing ID."""
        result = TemplateStore.get_template("nonexistent-id")
        assert result is None


# ---------------------------------------------------------------------------
# TestCreateTemplate
# ---------------------------------------------------------------------------

class TestCreateTemplate:
    def test_creates_with_correct_fields(self):
        """create_template should store all provided fields correctly."""
        entry = TemplateStore.create_template(
            name="Test Template",
            description="A test template",
            category="finance",
            tags=["finance", "report"],
            config_state={"inputs": [], "processors": []},
            author="tester",
            is_official=True,
        )
        assert entry["name"] == "Test Template"
        assert entry["description"] == "A test template"
        assert entry["category"] == "finance"
        assert entry["tags"] == ["finance", "report"]
        assert entry["author"] == "tester"
        assert entry["is_official"] is True
        assert entry["version"] == "1.0"
        assert entry["usage_count"] == 0

    def test_auto_generates_id(self):
        """create_template should auto-generate a unique ID."""
        entry = TemplateStore.create_template(
            name="Template A",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        assert "id" in entry
        assert len(entry["id"]) == 12

        entry2 = TemplateStore.create_template(
            name="Template B",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        assert entry["id"] != entry2["id"]

    def test_sets_timestamps(self):
        """create_template should set created_at and updated_at."""
        entry = TemplateStore.create_template(
            name="Timestamped",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        assert entry["created_at"]
        assert entry["updated_at"]
        assert entry["created_at"] == entry["updated_at"]

    def test_extracts_requirements(self):
        """create_template should extract requirements from config_state."""
        entry = TemplateStore.create_template(
            name="DB Template",
            description="desc",
            category="general",
            tags=[],
            config_state={
                "inputs": [{"plugin": "database", "name": "db_in"}],
                "processors": [],
            },
        )
        req_types = [r["type"] for r in entry["requirements"]]
        assert "database" in req_types


# ---------------------------------------------------------------------------
# TestUpdateTemplate
# ---------------------------------------------------------------------------

class TestUpdateTemplate:
    def test_updates_allowed_fields(self):
        """update_template should update only allowed fields."""
        entry = TemplateStore.create_template(
            name="Original",
            description="original desc",
            category="general",
            tags=["v1"],
            config_state={"inputs": [], "processors": []},
            author="author1",
        )
        updated = TemplateStore.update_template(
            entry["id"],
            name="Updated",
            description="updated desc",
            category="finance",
            tags=["v2"],
            author="author2",
            version="2.0",
        )
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["description"] == "updated desc"
        assert updated["category"] == "finance"
        assert updated["tags"] == ["v2"]
        assert updated["author"] == "author2"
        assert updated["version"] == "2.0"

    def test_returns_none_for_non_existing(self):
        """update_template should return None for a non-existing template."""
        result = TemplateStore.update_template("nonexistent-id", name="New Name")
        assert result is None

    def test_re_extracts_requirements_when_config_state_changes(self):
        """update_template should re-extract requirements when config_state is updated."""
        entry = TemplateStore.create_template(
            name="Simple",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        assert entry["requirements"] == []

        updated = TemplateStore.update_template(
            entry["id"],
            config_state={
                "inputs": [{"plugin": "database", "name": "db_in"}],
                "processors": [],
            },
        )
        req_types = [r["type"] for r in updated["requirements"]]
        assert "database" in req_types

    def test_updates_updated_at(self):
        """update_template should update the updated_at timestamp."""
        entry = TemplateStore.create_template(
            name="Timestamped",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        original_updated_at = entry["updated_at"]

        updated = TemplateStore.update_template(entry["id"], name="New Name")
        assert updated["updated_at"] != original_updated_at


# ---------------------------------------------------------------------------
# TestDeleteTemplate
# ---------------------------------------------------------------------------

class TestDeleteTemplate:
    def test_deletes_existing(self):
        """delete_template should remove the template and return True."""
        entry = TemplateStore.create_template(
            name="To Delete",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        result = TemplateStore.delete_template(entry["id"])
        assert result is True
        assert TemplateStore.get_template(entry["id"]) is None

    def test_returns_false_for_non_existing(self):
        """delete_template should return False for a non-existing template."""
        result = TemplateStore.delete_template("nonexistent-id")
        assert result is False


# ---------------------------------------------------------------------------
# TestIncrementUsage
# ---------------------------------------------------------------------------

class TestIncrementUsage:
    def test_increments_usage_count(self):
        """increment_usage should increase usage_count by 1."""
        entry = TemplateStore.create_template(
            name="Used Template",
            description="desc",
            category="general",
            tags=[],
            config_state={"inputs": [], "processors": []},
        )
        assert entry["usage_count"] == 0

        TemplateStore.increment_usage(entry["id"])
        result = TemplateStore.get_template(entry["id"])
        assert result["usage_count"] == 1

        TemplateStore.increment_usage(entry["id"])
        result = TemplateStore.get_template(entry["id"])
        assert result["usage_count"] == 2

    def test_no_error_for_non_existing(self):
        """increment_usage should not raise an error for a non-existing template."""
        TemplateStore.increment_usage("nonexistent-id")  # should not raise


# ---------------------------------------------------------------------------
# TestExtractRequirements
# ---------------------------------------------------------------------------

class TestExtractRequirements:
    def test_database_requirement(self):
        """Should return a database requirement when a plugin=database input exists."""
        config = {
            "inputs": [{"plugin": "database", "name": "db_in"}],
            "processors": [],
        }
        reqs = TemplateStore.extract_requirements(config)
        types = [r.type for r in reqs]
        assert "database" in types

    def test_ai_requirement_from_name(self):
        """Should return an AI requirement when a processor name contains 'ai'."""
        config = {
            "inputs": [],
            "processors": [{"name": "ai_classifier"}],
        }
        reqs = TemplateStore.extract_requirements(config)
        types = [r.type for r in reqs]
        assert "ai" in types

    def test_ai_requirement_from_sql(self):
        """Should return an AI requirement when a processor sql contains 'ai'."""
        config = {
            "inputs": [],
            "processors": [{"name": "proc", "sql": "CALL ai_predict()"}],
        }
        reqs = TemplateStore.extract_requirements(config)
        types = [r.type for r in reqs]
        assert "ai" in types

    def test_ai_requirement_from_script(self):
        """Should return an AI requirement when a processor script contains 'ai'."""
        config = {
            "inputs": [],
            "processors": [{"name": "proc", "script": "import ai_lib"}],
        }
        reqs = TemplateStore.extract_requirements(config)
        types = [r.type for r in reqs]
        assert "ai" in types

    def test_input_format_requirement(self):
        """Should return an input_format requirement for non-database plugins."""
        config = {
            "inputs": [{"plugin": "excel", "name": "sheet1"}],
            "processors": [],
        }
        reqs = TemplateStore.extract_requirements(config)
        types = [r.type for r in reqs]
        assert "input_format" in types
        fmt_req = next(r for r in reqs if r.type == "input_format")
        assert "excel" in fmt_req.description

    def test_no_requirements_for_empty_config(self):
        """Should return no requirements for an empty config_state."""
        config = {"inputs": [], "processors": []}
        reqs = TemplateStore.extract_requirements(config)
        assert reqs == []


# ---------------------------------------------------------------------------
# TestEnsureBuiltinTemplates
# ---------------------------------------------------------------------------

class TestEnsureBuiltinTemplates:
    def test_loads_from_templates_dir(self, tmp_path, monkeypatch):
        """Should load templates from TEMPLATES_DIR when it exists."""
        templates_dir = tmp_path / "builtin_templates"
        templates_dir.mkdir()
        builtin = {
            "id": "builtin-001",
            "name": "Built-in Report",
            "description": "A built-in template",
            "category": "sales",
            "tags": ["builtin"],
            "config_state": {"inputs": [], "processors": []},
            "author": "ConfigForge",
        }
        (templates_dir / "builtin_001.json").write_text(
            json.dumps(builtin), encoding="utf-8"
        )
        monkeypatch.setattr(template_store, "TEMPLATES_DIR", str(templates_dir))

        ensure_builtin_templates()

        result = TemplateStore.get_template("builtin-001")
        assert result is not None
        assert result["name"] == "Built-in Report"
        assert result["is_official"] is True

    def test_skips_if_templates_dir_does_not_exist(self, tmp_path, monkeypatch):
        """Should skip loading when TEMPLATES_DIR doesn't exist."""
        monkeypatch.setattr(
            template_store, "TEMPLATES_DIR", str(tmp_path / "nonexistent_dir")
        )
        # Should not raise
        ensure_builtin_templates()
        assert TemplateStore.list_templates() == []

    def test_skips_templates_that_already_exist_by_id(self, tmp_path, monkeypatch):
        """Should skip built-in templates whose ID already exists in the store."""
        templates_dir = tmp_path / "builtin_templates"
        templates_dir.mkdir()
        builtin = {
            "id": "builtin-002",
            "name": "Existing Built-in",
            "description": "Already loaded",
            "category": "general",
            "tags": [],
            "config_state": {"inputs": [], "processors": []},
            "author": "ConfigForge",
        }
        (templates_dir / "builtin_002.json").write_text(
            json.dumps(builtin), encoding="utf-8"
        )
        monkeypatch.setattr(template_store, "TEMPLATES_DIR", str(templates_dir))

        # Load once
        ensure_builtin_templates()
        first = TemplateStore.get_template("builtin-002")
        assert first is not None

        # Load again — should not duplicate
        ensure_builtin_templates()
        result = TemplateStore.list_templates()
        ids = [t["id"] for t in result]
        assert ids.count("builtin-002") == 1
