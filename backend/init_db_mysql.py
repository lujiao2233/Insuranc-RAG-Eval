"""MySQL数据库初始化脚本
用于创建数据库表结构
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def init_db():
    """初始化数据库表"""
    print("🚀 开始初始化MySQL数据库...")
    
    try:
        # 导入数据库模型和配置
        from models.database import Base
        from config.db_config import engine
        
        print("✅ 数据库配置加载成功")
        
        # 创建所有表
        print("🔧 正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功!")
        
        # 验证表是否创建成功
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 已创建的表: {tables}")
        
        print("\n🎉 数据库初始化完成!")
        print("\n💡 提示:")
        print("   - 确保MySQL服务正在运行")
        print("   - 数据库连接URL可在.backend/.env中修改")
        print("   - 接下来可以启动后端服务: uvicorn main:app --reload")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        print("\n🔧 解决方案:")
        print("   1. 确保MySQL服务正在运行")
        print("   2. 检查数据库连接配置")
        print("   3. 确保数据库用户有创建表的权限")
        print("   4. 确保数据库'rag_evaluation'已存在")
        return False

if __name__ == "__main__":
    init_db()