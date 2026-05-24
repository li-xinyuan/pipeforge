import ast

from configforge.generators.base import ConfigGenerator
from configforge.models.wizard import ProcessorConfig
from configforge.core.registry import GeneratorRegistry


@GeneratorRegistry.register("python", "processor")
class PythonProcessorGenerator(ConfigGenerator[ProcessorConfig]):
    def infer_config(self, context: dict) -> ProcessorConfig:
        return ProcessorConfig(plugin="python")

    def build_config(self, state) -> ProcessorConfig:
        return ProcessorConfig(plugin="python", script="")

    def validate_config(self, config: ProcessorConfig) -> list[str]:
        errors = []
        if not config.script or not config.script.strip():
            errors.append("Python 脚本不能为空")
            return errors
        try:
            tree = ast.parse(config.script)
            has_process = any(
                isinstance(node, ast.FunctionDef) and node.name == "process"
                for node in ast.walk(tree)
            )
            if not has_process:
                errors.append("Python 脚本必须定义 process(ctx) 函数")
        except SyntaxError as e:
            errors.append(f"Python 语法错误: {e}")
        return errors
