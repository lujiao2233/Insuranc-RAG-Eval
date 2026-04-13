import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine
from models.database import ApiUsageLog

def migrate():
    print("Creating ApiUsageLog table...")
    ApiUsageLog.__table__.create(bind=engine, checkfirst=True)
    print("Table created successfully.")

if __name__ == "__main__":
    migrate()