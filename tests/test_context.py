from pipeforge.core.context import Context, ExecutionResult, InputStats, Logger


class TestContext:
    def test_context_creation(self):
        ctx = Context(
            db=None,  # type: ignore
            params={"person_file": "/tmp/test.xlsx"},
            yaml_dir="/pipelines",
            scene_name="人员月报",
        )
        assert ctx.params["person_file"] == "/tmp/test.xlsx"
        assert ctx.yaml_dir == "/pipelines"
        assert ctx.scene_name == "人员月报"
        assert isinstance(ctx.result, ExecutionResult)
        assert isinstance(ctx.logger, Logger)

    def test_context_output_path_default(self):
        ctx = Context(
            db=None,  # type: ignore
            params={},
            yaml_dir="/pipelines",
            scene_name="人员月报",
        )
        assert ctx.output_path is None


class TestExecutionResult:
    def test_result_initial_state(self):
        result = ExecutionResult()
        assert result.inputs == {}
        assert result.processors == []
        assert result.output is None

    def test_result_record_input(self):
        result = ExecutionResult()
        result.inputs["person"] = InputStats(name="人员明细", rows_loaded=100, elapsed_ms=1500.0)
        assert result.inputs["person"].rows_loaded == 100


class TestLogger:
    def test_logger_info(self):
        logger = Logger()
        logger.info("hello")
        assert len(logger.messages) == 1
        assert logger.messages[0]["level"] == "INFO"

    def test_logger_error(self):
        logger = Logger()
        logger.error("fail")
        assert logger.messages[0]["level"] == "ERROR"

    def test_logger_verbose_flag_off(self):
        logger = Logger(verbose=False)
        logger.debug("hidden")
        assert len(logger.messages) == 0

    def test_logger_verbose_flag_on(self):
        logger = Logger(verbose=True)
        logger.debug("shown")
        assert len(logger.messages) == 1
