import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import engine
from models.database import ApiUsageLog

def migrate():
    print("准备在数据库中创建 api_usage_logs 表...")
    try:
        ApiUsageLog.__table__.create(bind=engine, checkfirst=True)
        print("✅ 表 api_usage_logs 创建成功或已存在！")
    except Exception as e:
        print(f"❌ 创建表失败: {e}")

if __name__ == "__main__":
    migrate()