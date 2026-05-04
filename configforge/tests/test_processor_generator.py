import pytest
from configforge.generators.processor.sql_processor import SqlProcessorGenerator
from configforge.models.wizard import ProcessorConfig


def test_build_config():
    gen = SqlProcessorGenerator()
    state = {"sql": "SELECT * FROM person", "output_tables": ["monthly_report"]}
    config = gen.build_config(state)
    assert config.sql == "SELECT * FROM person"
    assert config.output_tables == ["monthly_report"]


def test_validate_sql_syntax_error():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="SELEC * FROM", output_tables=[]))
    assert len(errors) > 0


def test_validate_passing():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="SELECT 1", output_tables=["t1"]))
    assert len(errors) == 0


def test_validate_empty_sql():
    gen = SqlProcessorGenerator()
    errors = gen.validate_config(ProcessorConfig(sql="", output_tables=[]))
    assert len(errors) > 0
