"""Tests for auto_diagnose service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from configforge.services.ai.auto_diagnose import _infer_step, auto_diagnose


class TestInferStep:
    def test_sql_error_infers_step_3(self):
        assert _infer_step("no such table: users", []) == 3

    def test_syntax_error_infers_step_3(self):
        assert _infer_step("SQL syntax error near SELECT", []) == 3

    def test_file_error_infers_step_2(self):
        assert _infer_step("file not found: data.xlsx", []) == 2

    def test_input_error_infers_step_2(self):
        assert _infer_step("输入源配置缺失", []) == 2

    def test_output_error_infers_step_4(self):
        assert _infer_step("output write permission denied", []) == 4

    def test_unknown_error_returns_0(self):
        assert _infer_step("something went wrong", []) == 0

    def test_suggestions_infers_step_3(self):
        assert _infer_step("error", ["检查 SQL 语法是否正确"]) == 3

    def test_suggestions_infers_step_2(self):
        assert _infer_step("error", ["检查输入源文件是否存在"]) == 2

    def test_suggestions_infers_step_4(self):
        assert _infer_step("error", ["检查输出列映射是否完整"]) == 4


class TestAutoDiagnose:
    @pytest.mark.asyncio
    async def test_returns_none_when_ai_disabled(self):
        mock_settings = MagicMock()
        mock_settings.enabled = False
        with patch("configforge.services.ai.auto_diagnose.load_settings", return_value=mock_settings):
            result = await auto_diagnose("yaml", "error msg")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_diagnosis_on_success(self):
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_backend = AsyncMock()
        mock_backend.generate.return_value = '{"cause": "表名不存在", "suggestions": ["检查表名拼写"], "severity": "error"}'
        mock_backend.close = AsyncMock()

        with patch("configforge.services.ai.auto_diagnose.load_settings", return_value=mock_settings), \
             patch("configforge.services.ai.auto_diagnose.create_backend", return_value=mock_backend):
            result = await auto_diagnose("yaml: test", "no such table: users")
            assert result is not None
            assert result["cause"] == "表名不存在"
            assert len(result["suggestions"]) == 1
            assert result["severity"] == "error"
            assert "step" in result

    @pytest.mark.asyncio
    async def test_returns_none_on_ai_failure(self):
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_backend = AsyncMock()
        mock_backend.generate.side_effect = Exception("AI service unavailable")
        mock_backend.close = AsyncMock()

        with patch("configforge.services.ai.auto_diagnose.load_settings", return_value=mock_settings), \
             patch("configforge.services.ai.auto_diagnose.create_backend", return_value=mock_backend):
            result = await auto_diagnose("yaml", "error msg")
            assert result is None

    @pytest.mark.asyncio
    async def test_defaults_missing_fields(self):
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_backend = AsyncMock()
        mock_backend.generate.return_value = '{"cause": "some error"}'
        mock_backend.close = AsyncMock()

        with patch("configforge.services.ai.auto_diagnose.load_settings", return_value=mock_settings), \
             patch("configforge.services.ai.auto_diagnose.create_backend", return_value=mock_backend):
            result = await auto_diagnose("yaml", "error msg")
            assert result is not None
            assert result["suggestions"] == []
            assert result["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_passes_context_to_prompt(self):
        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_backend = AsyncMock()
        mock_backend.generate.return_value = '{"cause": "test", "suggestions": [], "severity": "warning"}'
        mock_backend.close = AsyncMock()

        with patch("configforge.services.ai.auto_diagnose.load_settings", return_value=mock_settings), \
             patch("configforge.services.ai.auto_diagnose.create_backend", return_value=mock_backend), \
             patch("configforge.services.ai.auto_diagnose._cache_get", return_value=None), \
             patch("configforge.services.ai.auto_diagnose.build_prompt") as mock_build:
            mock_build.return_value = "test prompt"
            await auto_diagnose(
                "yaml", "error msg", scene_name="测试",
                inputs_summary=[{"name": "input1"}],
                processors_summary=[{"name": "proc1"}],
            )
            call_args = mock_build.call_args
            assert call_args[0][0] == "diagnose"
            context = call_args[0][1]
            assert context["yaml"] == "yaml"
            assert context["errorLog"] == "error msg"
