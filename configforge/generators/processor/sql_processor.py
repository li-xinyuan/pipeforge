import sqlite3
from configforge.generators.base import ConfigGenerator
from configforge.models.wizard import ProcessorConfig
from configforge.core.registry import GeneratorRegistry


@GeneratorRegistry.register("sql", "processor")
class SqlProcessorGenerator(ConfigGenerator[ProcessorConfig]):
    @classmethod
    def config_model(cls):
        return ProcessorConfig

    def infer_config(self, source: dict) -> ProcessorConfig:
        return ProcessorConfig(sql="", output_tables=[])

    def build_config(self, wizard_state: dict) -> ProcessorConfig:
        return ProcessorConfig(
            sql=wizard_state.get("sql", ""),
            output_tables=wizard_state.get("output_tables", []),
        )

    def validate_config(self, config: ProcessorConfig) -> list[str]:
        errors = []
        if not config.sql or not config.sql.strip():
            errors.append("SQL must not be empty")
            return errors
        try:
            conn = sqlite3.connect(":memory:")
            conn.executescript(config.sql)
            conn.close()
        except sqlite3.Error as e:
            errors.append(f"SQL syntax error: {e}")
        return errors
