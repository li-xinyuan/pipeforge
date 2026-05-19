import os
import tempfile

from pipeforge.core.context import Logger


class TestLogger:
    def test_writes_to_file(self):
        log_dir = tempfile.mkdtemp()
        log = Logger(log_dir=log_dir)
        log.info("test message")
        log.info("another message")
        log.close()

        files = os.listdir(log_dir)
        assert len(files) == 1
        assert files[0].startswith("pipeforge_")
        assert files[0].endswith(".log")

        with open(os.path.join(log_dir, files[0]), "r") as f:
            content = f.read()
            assert "[INFO] test message" in content
            assert "[INFO] another message" in content

    def test_no_file_when_no_log_dir(self):
        log = Logger()
        log.info("stdout only")
        log.close()

    def test_multiple_executions_create_separate_files(self):
        log_dir = tempfile.mkdtemp()
        log1 = Logger(log_dir=log_dir)
        log1.info("run 1")
        log1.close()
        log2 = Logger(log_dir=log_dir)
        log2.info("run 2")
        log2.close()

        files = os.listdir(log_dir)
        assert len(files) == 2
