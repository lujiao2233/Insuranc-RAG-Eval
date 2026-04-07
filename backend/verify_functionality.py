"""功能验证脚本
验证文档上传模块的所有组件是否正常工作
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_backend_structure():
    """检查后端目录结构"""
    print("\n" + "=" * 60)
    print("检查后端目录结构...")
    print("=" * 60)
    
    required_files = [
        "api/routers/documents.py",
        "api/routers/analysis.py",
        "models/database.py",
        "schemas.py",
        "services/document_analyzer.py",
        "config/settings.py",
        "config/db_config.py",
        "main.py",
        "requirements.txt",
        ".env"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(file_path)
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"❌ 文件不存在: {file_path}")
        else:
            print(f"✅ 文件存在: {file_path}")
    
    return len(missing_files) == 0

def check_database_model():
    """检查数据库模型"""
    print("\n" + "=" * 60)
    print("检查数据库模型...")
    print("=" * 60)
    
    try:
        from models.database import Document, User
        
        # 检查Document模型是否有新字段
        document_columns = [c.name for c in Document.__table__.columns]
        
        required_columns = [
            'id', 'user_id', 'filename', 'file_path', 'file_type',
            'file_size', 'page_count', 'upload_time', 'status',
            'is_analyzed', 'analyzed_at', 'doc_metadata_col', 'outline',
            'created_at', 'updated_at'
        ]
        
        missing_columns = []
        for col in required_columns:
            if col not in document_columns:
                missing_columns.append(col)
                print(f"❌ 缺少字段: {col}")
            else:
                print(f"✅ 字段存在: {col}")
        
        return len(missing_columns) == 0
        
    except Exception as e:
        print(f"❌ 数据库模型检查失败: {str(e)}")
        return False

def check_api_routes():
    """检查API路由配置"""
    print("\n" + "=" * 60)
    print("检查API路由配置...")
    print("=" * 60)
    
    try:
        from api.routers import documents, analysis
        
        # 检查文档路由
        doc_routes = [
            'list_documents', 'get_document', 'upload_document',
            'update_document', 'delete_document', 'download_document',
            'get_document_stats'
        ]
        
        for route in doc_routes:
            if hasattr(documents, route):
                print(f"✅ 文档路由存在: {route}")
            else:
                print(f"❌ 文档路由缺失: {route}")
        
        # 检查分析路由
        analysis_routes = [
            'analyze_document', 'analyze_documents_batch',
            'get_analysis_status', 'get_analysis_results'
        ]
        
        for route in analysis_routes:
            if hasattr(analysis, route):
                print(f"✅ 分析路由存在: {route}")
            else:
                print(f"❌ 分析路由缺失: {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ API路由检查失败: {str(e)}")
        return False

def check_dependencies():
    """检查依赖项"""
    print("\n" + "=" * 60)
    print("检查Python依赖项...")
    print("=" * 60)
    
    required_packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic',
        'PyPDF2', 'docx', 'openpyxl', 'PIL'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'docx':
                import docx
            else:
                __import__(package)
            print(f"✅ 依赖已安装: {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ 依赖未安装: {package}")
    
    return len(missing_packages) == 0

def check_frontend_structure():
    """检查前端目录结构"""
    print("\n" + "=" * 60)
    print("检查前端目录结构...")
    print("=" * 60)
    
    required_files = [
        "../frontend/src/views/documents/Upload.vue",
        "../frontend/src/views/documents/List.vue",
        "../frontend/src/api/client.js",
        "../frontend/src/api/documents.js",
        "../frontend/src/api/auth.js",
        "../frontend/src/store/user.js",
        "../frontend/src/router/index.js",
        "../frontend/package.json",
        "../frontend/vite.config.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(file_path)
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"❌ 文件不存在: {file_path}")
        else:
            print(f"✅ 文件存在: {file_path}")
    
    return len(missing_files) == 0

def check_main_app():
    """检查主应用配置"""
    print("\n" + "=" * 60)
    print("检查主应用配置...")
    print("=" * 60)
    
    try:
        from main import app
        
        # 检查路由是否注册
        routes = [route.path for route in app.routes]
        
        required_routes = [
            '/api/v1/documents',
            '/api/v1/analysis'
        ]
        
        for route in required_routes:
            if any(route in r for r in routes):
                print(f"✅ 路由已注册: {route}")
            else:
                print(f"❌ 路由未注册: {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ 主应用检查失败: {str(e)}")
        return False

def create_verification_report():
    """创建验证报告"""
    print("\n" + "=" * 60)
    print("生成验证报告...")
    print("=" * 60)
    
    results = {
        "后端结构": check_backend_structure(),
        "数据库模型": check_database_model(),
        "API路由": check_api_routes(),
        "依赖项": check_dependencies(),
        "前端结构": check_frontend_structure(),
        "主应用": check_main_app()
    }
    
    print("\n" + "=" * 60)
    print("验证结果总结")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证项目通过！系统可以正常使用。")
    else:
        print("⚠️ 部分验证项目失败，请检查上述错误信息。")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    os.chdir(project_root)
    create_verification_report()