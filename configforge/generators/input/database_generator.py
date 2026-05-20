from ..base import ConfigGenerator
from ...models.wizard import DatabaseInputConfig
from ...core.registry import GeneratorRegistry


@GeneratorRegistry.register("database", "input")
class DatabaseInputGenerator(ConfigGenerator[DatabaseInputConfig]):
    """Database input generator for ConfigForge wizard."""

    @classmethod
    def config_model(cls) -> type[DatabaseInputConfig]:
        return DatabaseInputConfig

    def infer_config(self, source: dict) -> DatabaseInputConfig:
        return DatabaseInputConfig(
            query_type=source.get("query_type", "table"),
            tables=source.get("tables", []),
            sql=source.get("sql", ""),
        )

    def build_config(self, wizard_state: dict) -> DatabaseInputConfig:
        return DatabaseInputConfig(
            connection_id=wizard_state.get("connection_id", ""),
            db_type=wizard_state.get("db_type", ""),
            query_type=wizard_state.get("query_type", "table"),
            tables=wizard_state.get("tables", []),
            sql=wizard_state.get("sql", ""),
        )

    def validate_config(self, config: DatabaseInputConfig) -> list[str]:
        errors = []
        if not config.connection_id:
            errors.append("Connection is required")
        has_tables = len(config.tables) > 0
        has_sql = bool(config.sql.strip())
        if has_tables and has_sql:
            errors.append("tables and sql are mutually exclusive")
        if not has_tables and not has_sql:
            errors.append("Either tables or sql must be provided")
        return errors
