"""版本管理 — 唯一版本源"""
import os

_VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')

def get_version() -> str:
    """从 VERSION 文件读取当前版本号"""
    try:
        with open(_VERSION_FILE, 'r') as f:
            return f.read().strip()
    except:
        return '0.0.0'

__version__ = get_version()
