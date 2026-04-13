import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import engine
from sqlalchemy import text

def migrate():
    print("准备更新 api_usage_logs 表，增加 latency_ms 字段...")
    try:
        with engine.connect() as conn:
            # 检查列是否已经存在
            result = conn.execute(text("SHOW COLUMNS FROM api_usage_logs LIKE 'latency_ms'"))
            if result.fetchone():
                print("✅ 字段 latency_ms 已存在，无需更新。")
            else:
                # 增加新列
                conn.execute(text("ALTER TABLE api_usage_logs ADD COLUMN latency_ms INT DEFAULT 0 COMMENT '请求耗时(毫秒)' AFTER total_tokens"))
                conn.commit()
                print("✅ 字段 latency_ms 添加成功！")
    except Exception as e:
        print(f"❌ 更新表失败: {e}")

if __name__ == "__main__":
    migrate()