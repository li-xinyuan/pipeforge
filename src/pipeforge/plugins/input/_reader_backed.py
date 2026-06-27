"""限制③C：Reader-backed 输入插件通用基类。

封装「读取文件 → 全量加载到 SQLite」的通用流程，子类只需提供 _read_rows 钩子。
私有模块（_ 前缀），不自动注册；由 json.py/xml.py/parquet.py 继承并注册。
"""
import os

from pipeforge.plugins.base import InputPlugin


class ReaderBackedInputPlugin(InputPlugin):
    """通用 reader-backed 输入插件基类。

    子类实现 _read_rows(filepath, config) -> (columns, row_iterator)。
    execute 负责文件路径解析、建表、流式插入。
    """

    def execute(self, context, config) -> None:
        filepath = os.path.join(context.yaml_dir, config.file)
        columns, rows = self._read_rows(filepath, config)

        if not columns:
            raise ValueError(f"File is empty: {config.file}")

        context.db.create_table(self.table_name, columns)
        with context.db.transaction():
            for row in rows:
                context.db.insert_row(self.table_name, tuple(str(v) for v in row))

        context.logger.info(
            f"Input '{self.label}': loaded data into table '{self.table_name}' "
            f"({len(columns)} columns)"
        )

    def _read_rows(self, filepath: str, config) -> tuple[list[str], "object"]:
        """子类实现：读取文件返回 (columns, row_iterator)。"""
        raise NotImplementedError
