import ast
import multiprocessing
import sys
import threading

from pipeforge.config.models import PythonProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin

# Whitelist of safe builtins for user scripts
_SAFE_BUILTINS = {
    "len": len, "range": range, "str": str, "int": int, "float": float,
    "bool": bool, "list": list, "dict": dict, "tuple": tuple, "set": set,
    "frozenset": frozenset, "print": print, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "reversed": reversed, "sum": sum, "min": min, "max": max,
    "abs": abs, "round": round, "type": type, "isinstance": isinstance,
    "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
    "None": None, "True": True, "False": False,
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "IndexError": IndexError, "RuntimeError": RuntimeError,
    "StopIteration": StopIteration, "NotImplementedError": NotImplementedError,
    "AttributeError": AttributeError,
}

# AST node types that indicate dangerous operations
_FORBIDDEN_AST_NODES = (
    ast.Import, ast.ImportFrom,
)

_FORBIDDEN_NAMES = {
    "__import__", "eval", "exec", "compile", "open", "input",
    "globals", "locals", "dir", "vars", "breakpoint",
    "exit", "quit", "help", "copyright", "credits", "license",
    "memoryview", "bytearray", "bytes", "complex", "object",
    "classmethod", "staticmethod", "property", "super",
    "delattr", "execfile",
}


def _validate_script(script: str) -> None:
    """AST-level validation: reject dangerous constructs."""
    try:
        tree = ast.parse(script)
    except SyntaxError as e:
        raise ValueError(f"Python 脚本语法错误: {e}")

    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_AST_NODES):
            raise ValueError(
                f"Python 脚本不允许 import 语句（第 {node.lineno} 行）。"
                "仅可使用内置函数和 process(ctx) 接口。"
            )
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise ValueError(
                f"Python 脚本不允许使用 '{node.id}'（第 {node.lineno} 行）。"
            )
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError(
                f"Python 脚本不允许访问双下划线属性（第 {node.lineno} 行）。"
            )


@register_plugin("python", "processor")
class PythonProcessorPlugin(ProcessorPlugin):
    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls):
        return PythonProcessorConfig

    def execute(self, context, config: PythonProcessorConfig) -> None:
        # 1. AST validation
        _validate_script(config.script)

        # 2. Execute with builtins whitelist
        local_ns: dict = {}
        exec(config.script, {"__builtins__": _SAFE_BUILTINS}, local_ns)
        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        # 3. Timeout via signal (main thread only, Unix only)
        use_signal = (
            sys.platform != "win32"
            and threading.current_thread() is threading.main_thread()
        )
        if use_signal:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Python 脚本执行超时（{self.TIMEOUT_SECONDS}秒）")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.TIMEOUT_SECONDS)

        try:
            process_fn(context)
        finally:
            if use_signal:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            context.db.connection.commit()
            context.logger.info(f"Python processor '{self.label}': executed successfully")
