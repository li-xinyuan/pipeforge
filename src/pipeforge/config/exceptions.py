class ConfigError(Exception):
    """配置加载或校验阶段的错误。"""
    pass


class CheckpointError(Exception):
    """检查点验证失败。results 包含所有规则的执行结果。"""

    def __init__(self, results: list):
        self.results = results
        failed = [r for r in results if not r.passed and r.on_failure == "block"]
        msg = "; ".join(r.message for r in failed)
        super().__init__(f"检查点验证失败: {msg}")
