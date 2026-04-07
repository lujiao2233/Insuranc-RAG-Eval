"""数据库连接测试脚本
用于验证MySQL数据库连接是否正常
"""
import asyncio
from sqlalchemy import text
from config.database import engine

async def test_db_connection():
    """测试数据库连接"""
    print("正在测试数据库连接...")
    
    try:
        # 创建异步连接
        async with engine.begin() as conn:
            # 执行一个简单的查询
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row:
                print("✅ 数据库连接测试成功!")
                print(f"测试结果: {row[0]}")
                return True
            else:
                print("❌ 数据库连接测试失败: 无法获取测试结果")
                return False
                
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {str(e)}")
        return False

def sync_test_db_connection():
    """同步方式测试数据库连接"""
    print("正在测试数据库连接...")
    
    try:
        # 创建同步连接
        with engine.connect() as conn:
            # 执行一个简单的查询
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row:
                print("✅ 数据库连接测试成功!")
                print(f"测试结果: {row[0]}")
                return True
            else:
                print("❌ 数据库连接测试失败: 无法获取测试结果")
                return False
                
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    
    # 添加项目根目录到Python路径
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # 从环境变量或配置文件加载数据库URL
    from config.database import settings
    print(f"数据库URL: {settings.DATABASE_URL}")
    
    # 运行同步测试
    success = sync_test_db_connection()
    
    if success:
        print("\n🎉 数据库配置完成!")
        print("下一步可以:")
        print("1. 运行 'python init_db.py' 创建数据库表")
        print("2. 启动后端服务 'uvicorn main:app --reload'")
    else:
        print("\n❌ 请检查数据库配置和连接设置")
        print("可能需要:")
        print("- 确保MySQL服务正在运行")
        print("- 检查数据库用户名和密码")
        print("- 确认数据库名称是否存在")