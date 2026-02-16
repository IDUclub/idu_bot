from pathlib import Path
from collections import deque

from loguru import logger


class LogsService:

    def __init__(self, logs_file_path: Path):

        self.logs_file_path = logs_file_path

    def check_file(self):

        try:
            with open(self.logs_file_path, "r"):
                logger.info("Read logs file from path {}".format(self.logs_file_path))
                return
        except FileNotFoundError:
            logger.error("Logs file not found by path {}".format(self.logs_file_path))
            raise
        except PermissionError:
            logger.error("Logs file access is permitted for path {}".format(self.logs_file_path))
            raise
        except OSError as os_error:
            logger.error("Unexpected os error while trying to access logs file {}".format(self.logs_file_path))
            logger.exception(os_error)
            raise
        except Exception as e:
            logger.error("Unexpected exception while trying to access logs file {}".format(self.logs_file_path))
            logger.exception(e)
            raise

    def get_logs(self, length: int) -> list[str]:

        self.check_file()
        with open(self.logs_file_path, "r") as f:
            logger.info("Read logs file from path {}".format(self.logs_file_path))
            return list(deque(f, maxlen=length))
