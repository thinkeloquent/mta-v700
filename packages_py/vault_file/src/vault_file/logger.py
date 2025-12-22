"""
Vault File Logger
Provides standardized logging with multiple levels.
"""
import os
import sys
from typing import Literal, Any, Union

LogLevel = Literal['silent', 'error', 'warn', 'info', 'debug', 'trace']

class VaultFileLogger:
    def error(self, message: str, *args: Any) -> None: ...
    def warn(self, message: str, *args: Any) -> None: ...
    def info(self, message: str, *args: Any) -> None: ...
    def debug(self, message: str, *args: Any) -> None: ...
    def trace(self, message: str, *args: Any) -> None: ...

LOG_LEVELS = {
    'silent': 0,
    'error': 1,
    'warn': 2,
    'info': 3,
    'debug': 4,
    'trace': 5
}

_current_level: LogLevel = 'info'

# Detect initial log level from env
env_level = os.getenv('VAULT_FILE_LOG_LEVEL', '').lower()
if env_level in LOG_LEVELS:
    _current_level = env_level # type: ignore

PREFIX = os.getenv('VAULT_FILE_LOG_PREFIX', '[vault-file]')

def get_log_level() -> LogLevel:
    return _current_level

def set_log_level(level: LogLevel) -> None:
    global _current_level
    if level in LOG_LEVELS:
        _current_level = level

class ConsoleLogger(VaultFileLogger):
    def _should_log(self, level: LogLevel) -> bool:
        return LOG_LEVELS[level] <= LOG_LEVELS[_current_level]

    def _format(self, message: str) -> str:
        return f"{PREFIX} {message}"

    def error(self, message: str, *args: Any) -> None:
        if self._should_log('error'):
            print(self._format(message), *args, file=sys.stderr)

    def warn(self, message: str, *args: Any) -> None:
        if self._should_log('warn'):
            print(self._format(message), *args, file=sys.stderr)

    def info(self, message: str, *args: Any) -> None:
        if self._should_log('info'):
            print(self._format(message), *args, file=sys.stdout)

    def debug(self, message: str, *args: Any) -> None:
        if self._should_log('debug'):
            print(self._format(message), *args, file=sys.stdout)

    def trace(self, message: str, *args: Any) -> None:
        if self._should_log('trace'):
            print(self._format(message), *args, file=sys.stdout)

_logger_instance = ConsoleLogger()

def get_logger() -> VaultFileLogger:
    return _logger_instance
