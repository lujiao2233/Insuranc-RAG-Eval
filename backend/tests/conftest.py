"""Pytest 配置 - 添加项目根目录到 Python 路径"""
import sys
from pathlib import Path

# 添加 backend 根目录到 Python 路径
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
