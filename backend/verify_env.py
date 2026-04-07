"""环境准备验证脚本
验证MySQL数据库配置是否正确
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查必要的目录
    required_dirs = [
        "data",
        "data/uploads",
        "logs"
    ]
    
    for directory in required_dirs:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ 目录不存在: {directory}")
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 已创建目录: {directory}")
        else:
            print(f"✅ 目录存在: {directory}")
    
    # 检查配置文件
    config_file = Path(".env")
    if config_file.exists():
        print(f"✅ 配置文件存在: {config_file}")
        
        # 读取配置文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "mysql+pymysql" in content:
                print("✅ MySQL数据库配置正确")
            else:
                print("⚠️ 未检测到MySQL数据库配置")
    else:
        print(f"❌ 配置文件不存在: {config_file}")
        # 创建默认配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write("""# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/rag_evaluation

# API配置
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key-here-change-this-to-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1800

# 项目配置
PROJECT_NAME=RAG Evaluation System
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:3000,https://localhost,https://localhost:3006

# 评估配置
DEFAULT_EVALUATION_TIMEOUT=300
DEFAULT_MAX_WORKERS=4

# 文件上传配置
MAX_FILE_SIZE=50MB
ALLOWED_EXTENSIONS=.pdf,.docx,.xlsx
UPLOAD_DIR=data/uploads
""")
        print(f"✅ 已创建默认配置文件: {config_file}")
    
    # 检查依赖
    try:
        import pymysql
        print("✅ PyMySQL依赖已安装")
    except ImportError:
        print("❌ PyMySQL依赖未安装")
    
    try:
        import mysql.connector
        print("✅ MySQL Connector依赖已安装")
    except ImportError:
        print("❌ MySQL Connector依赖未安装")
    
    try:
        import sqlalchemy
        print("✅ SQLAlchemy依赖已安装")
    except ImportError:
        print("❌ SQLAlchemy依赖未安装")
    
    try:
        import fastapi
        print("✅ FastAPI依赖已安装")
    except ImportError:
        print("❌ FastAPI依赖未安装")
    
    # 检查数据库模型
    try:
        from models.database import User, Document, TestSet, Question, Evaluation, EvaluationResult, Configuration
        print("✅ 数据库模型导入成功")
    except Exception as e:
        print(f"❌ 数据库模型导入失败: {e}")
    
    # 检查Pydantic模型
    try:
        from schemas import User as UserSchema, Document as DocumentSchema
        print("✅ Pydantic模型导入成功")
    except Exception as e:
        print(f"❌ Pydantic模型导入失败: {e}")
    
    print("\n🎉 环境检查完成!")
    print("\n下一步操作:")
    print("1. 确保MySQL服务正在运行")
    print("2. 创建数据库: CREATE DATABASE rag_evaluation;")
    print("3. 运行数据库初始化: python init_db_mysql.py")
    print("4. 启动后端服务: uvicorn main:app --reload")

if __name__ == "__main__":
    check_environment()
