"""PipeForge 数据读取器（流式全量读取）。

限制③C reader 适配器：为 json/xml/parquet 输入插件提供全量读取接口。
readers 是纯数据工具层，不依赖 configforge，供 pipeforge.plugins.input 使用。
"""
