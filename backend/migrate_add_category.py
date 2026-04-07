"""数据库迁移脚本
用于向现有数据库表添加分类字段
"""
import sys
from pathlib import Path
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def migrate_add_category_field():
    """添加文档分类字段到数据库"""
    print("🚀 开始数据库迁移：添加文档分类字段...")
    
    try:
        from sqlalchemy import create_engine, text
        from config.settings import settings
        
        # 创建数据库引擎
        engine = create_engine(settings.DATABASE_URL)
        
        # 检查字段是否存在
        with engine.connect() as conn:
            # 检查documents表中是否已有category字段
            result = conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'documents' 
                AND COLUMN_NAME = 'category'
            """))
            
            if result.fetchone():
                print("✅ category字段已存在，无需迁移")
                return True
            
            print("🔍 category字段不存在，正在添加...")
            
            # 添加category字段
            alter_sql = """
                ALTER TABLE documents 
                ADD COLUMN category VARCHAR(100) DEFAULT '未分类' COMMENT '文档分类'
            """
            conn.execute(text(alter_sql))
            conn.commit()
            
            print("✅ category字段添加成功!")
            
            # 验证字段是否添加成功
            result = conn.execute(text("""
                SELECT COLUMN_NAME, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'documents' 
                AND COLUMN_NAME = 'category'
            """))
            
            column_info = result.fetchone()
            if column_info:
                print(f"✅ 验证成功: 字段 {column_info[0]}, 默认值: {column_info[1]}, 注释: {column_info[2]}")
            else:
                print("❌ 验证失败: 无法找到新增的字段")
                return False
                
        print("\n🎉 数据库迁移完成!")
        print("\n💡 提示:")
        print("   - 新上传的文档将默认分类为'未分类'")
        print("   - 可以通过API或管理界面更新现有文档的分类")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库迁移失败: {str(e)}")
        print("\n🔧 解决方案:")
        print("   1. 确保MySQL服务正在运行")
        print("   2. 检查数据库连接配置")
        print("   3. 确保数据库用户有ALTER TABLE权限")
        return False

if __name__ == "__main__":
    migrate_add_category_field()