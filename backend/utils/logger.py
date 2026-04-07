"""日志工具
提供统一的日志配置和获取接口
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_loggers = {}
_log_dir = None


def setup_logger(
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True
) -> None:
    """设置日志配置
    
    Args:
        log_dir: 日志文件目录
        level: 日志级别
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
    """
    global _log_dir
    _log_dir = log_dir
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    if file_output and log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        log_file = log_path / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        Logger实例
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    
    return logger


class LoggerAdapter:
    """日志适配器，提供更便捷的日志方法"""
    
    def __init__(self, name: str):
        self._logger = get_logger(name)
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        self._logger.exception(msg, *args, **kwargs)


def get_logger_adapter(name: str) -> LoggerAdapter:
    """获取日志适配器
    
    Args:
        name: 日志名称
        
    Returns:
        LoggerAdapter实例
    """
    return LoggerAdapter(name)
