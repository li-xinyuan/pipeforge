import ast
import sys
import threading

from pipeforge.config.models import PythonProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin

# Whitelist of safe builtins for user scripts
_SAFE_BUILTINS = {
    "print": print, "len": len, "range": range,
    "int": int, "float": float, "str": str,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "bool": bool, "None": None, "True": True, "False": False,
    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
    "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "sorted": sorted, "reversed": reversed,
    "isinstance": isinstance, "type": type,
    "hasattr": hasattr, "getattr": getattr,
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "IndexError": IndexError, "RuntimeError": RuntimeError,
    "StopIteration": StopIteration, "NotImplementedError": NotImplementedError,
}

# Allowed AST node types (whitelist: only expressions, assignments, if/for/while, function defs, return)
_ALLOWED_AST_NODES = {
    # Root
    ast.Module,
    # Allowed statements
    ast.Expr, ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.If, ast.For, ast.While, ast.AsyncFor,
    ast.FunctionDef, ast.AsyncFunctionDef,
    ast.Return, ast.Pass, ast.Break, ast.Continue,
    # Expression sub-nodes
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Name, ast.Constant, ast.Attribute, ast.Subscript,
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.IfExp, ast.Lambda, ast.Starred, ast.Slice,
    ast.JoinedStr, ast.FormattedValue,
    ast.comprehension, ast.arguments, ast.arg,
    ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr,
    ast.keyword,  # keyword arguments in function calls
    # Name/subscription contexts
    ast.Load, ast.Store, ast.Del,
    # Operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor, ast.MatMult,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Invert, ast.Not, ast.UAdd, ast.USub,
}

# Add version-specific AST node types (older Python compat)
import warnings as _warnings

with _warnings.catch_warnings():
    _warnings.simplefilter("ignore", DeprecationWarning)
    for _node_name in ('Num', 'Str', 'Bytes', 'NameConstant', 'Index', 'ExtSlice', 'Ellipsis'):
        _node_cls = getattr(ast, _node_name, None)
        if _node_cls is not None:
            _ALLOWED_AST_NODES.add(_node_cls)

# Forbidden names (dangerous builtins/functions)
_FORBIDDEN_NAMES = {
    "__import__", "eval", "exec", "compile", "open",
    "globals", "locals", "vars", "dir",
    "breakpoint", "delattr",
}


def _validate_script(script: str) -> None:
    """AST-level validation: whitelist allowed nodes, reject dangerous constructs."""
    try:
        tree = ast.parse(script)
    except SyntaxError as e:
        raise ValueError(f"Python 脚本语法错误: {e}")

    for node in ast.walk(tree):
        # 1. Whitelist check: only allowed AST node types
        if type(node) not in _ALLOWED_AST_NODES:
            node_name = type(node).__name__
            raise ValueError(
                f"Python 脚本不允许使用 '{node_name}' 构造"
                f"（第 {getattr(node, 'lineno', '?')} 行）。"
                f"仅允许：表达式、赋值、if/for/while、函数定义、return。"
            )
        # 2. Forbidden names check
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise ValueError(
                f"Python 脚本不允许使用 '{node.id}'（第 {node.lineno} 行）。"
            )
        # 3. Dunder attribute access check (obj.__xxx__)
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError(
                f"Python 脚本不允许访问双下划线属性（第 {node.lineno} 行）。"
            )
        # 4. getattr with dunder string check: getattr(obj, "__xxx__")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "getattr":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    val = node.args[1].value
                    if isinstance(val, str) and val.startswith("__"):
                        raise ValueError(
                            f"Python 脚本不允许通过 getattr 访问双下划线属性"
                            f"（第 {node.lineno} 行）。"
                        )


@register_plugin("python", "processor")
class PythonProcessorPlugin(ProcessorPlugin):
    """Python processor plugin that executes user-defined process(ctx) functions.

    SECURITY WARNING: This plugin uses AST whitelisting and a restricted builtins
    dictionary to limit what user scripts can do, but this is NOT a full sandbox.
    Determined users can bypass these restrictions through various Python introspection
    techniques (e.g., accessing object.__subclasses__(), using type() to reconstruct
    dangerous objects, etc.). For production use with untrusted code, consider:
    1. Running in a container/VM with restricted permissions
    2. Using RestrictedPython for stricter compilation-time checks
    3. Using a separate process with resource limits (ulimit, cgroups)
    """
    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls):
        return PythonProcessorConfig

    @classmethod
    def _validate_code(cls, script: str) -> None:
        """Public API for code validation."""
        _validate_script(script)

    def execute(self, context, config: PythonProcessorConfig) -> None:
        # 1. AST validation
        _validate_script(config.script)

        # 2. Setup timeout (covers both exec and process_fn)
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
            # 3. Execute with builtins whitelist
            local_ns: dict = {}
            exec(config.script, {"__builtins__": _SAFE_BUILTINS}, local_ns)
            process_fn = local_ns.get("process")
            if not process_fn or not callable(process_fn):
                raise ValueError("Python 脚本必须定义 process(ctx) 函数")

            # 4. Call process function
            process_fn(context)
        finally:
            if use_signal:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            context.db.connection.commit()
            context.logger.info(f"Python processor '{self.label}': executed successfully")


# Alias for convenience
PythonProcessor = PythonProcessorPlugin
