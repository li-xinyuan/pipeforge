import sys

from pipeforge.config.models import PythonProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin


@register_plugin("python", "processor")
class PythonProcessorPlugin(ProcessorPlugin):
    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls):
        return PythonProcessorConfig

    def execute(self, context, config: PythonProcessorConfig) -> None:
        local_ns = {}
        exec(config.script, {"__builtins__": __builtins__}, local_ns)
        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        if sys.platform != "win32":
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Python 脚本执行超时（{self.TIMEOUT_SECONDS}秒）")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.TIMEOUT_SECONDS)

        try:
            process_fn(context)
        finally:
            if sys.platform != "win32":
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            context.db.connection.commit()
            context.logger.info(f"Python processor '{self.label}': executed successfully")
