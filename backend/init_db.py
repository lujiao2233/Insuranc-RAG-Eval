"""数据库初始化脚本
用于创建MySQL数据库表结构
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入数据库模型
from models.database import Base
from config.database import engine

def init_db():
    """初始化数据库表"""
    print("开始初始化数据库...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("数据库表创建成功!")
        
        # 验证表是否创建成功
        tables = Base.metadata.tables.keys()
        print(f"已创建的表: {list(tables)}")
        
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        return False
    
    print("数据库初始化完成!")
    return True

if __name__ == "__main__":
    init_db()