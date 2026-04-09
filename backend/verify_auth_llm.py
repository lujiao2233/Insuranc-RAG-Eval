"""系统验证脚本
验证认证系统和文档分析服务集成
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_imports():
    """检查所有模块导入"""
    print("=" * 50)
    print("1. 检查模块导入...")
    
    errors = []
    
    try:
        from config.settings import settings, SECRET_KEY, ALGORITHM
        print("  ✓ config.settings")
    except Exception as e:
        errors.append(f"config.settings: {e}")
        print(f"  ✗ config.settings: {e}")
    
    try:
        from config.database import engine, Base, get_db
        print("  ✓ config.database")
    except Exception as e:
        errors.append(f"config.database: {e}")
        print(f"  ✗ config.database: {e}")
    
    try:
        from models.database import User, Document, TestSet, Question, Evaluation
        print("  ✓ models.database")
    except Exception as e:
        errors.append(f"models.database: {e}")
        print(f"  ✗ models.database: {e}")
    
    try:
        from schemas import User, UserCreate, Token, Document
        print("  ✓ schemas")
    except Exception as e:
        errors.append(f"schemas: {e}")
        print(f"  ✗ schemas: {e}")
    
    try:
        from services.auth_service import (
            verify_password, get_password_hash, create_user,
            authenticate_user, create_access_token
        )
        print("  ✓ services.auth_service")
    except Exception as e:
        errors.append(f"services.auth_service: {e}")
        print(f"  ✗ services.auth_service: {e}")
    
    try:
        from services.document_processor import DocumentProcessor
        print("  ✓ services.document_processor (原项目代码)")
    except Exception as e:
        errors.append(f"services.document_processor: {e}")
        print(f"  ✗ services.document_processor: {e}")
    
    try:
        from services.metadata_extractor import MetadataExtractor
        print("  ✓ services.metadata_extractor (原项目代码)")
    except Exception as e:
        errors.append(f"services.metadata_extractor: {e}")
        print(f"  ✗ services.metadata_extractor: {e}")
    
    try:
        from services.chunking_service import ChunkingService
        print("  ✓ services.chunking_service (原项目代码)")
    except Exception as e:
        errors.append(f"services.chunking_service: {e}")
        print(f"  ✗ services.chunking_service: {e}")
    
    try:
        from services.document_analyzer import DocumentAnalyzer
        print("  ✓ services.document_analyzer")
    except Exception as e:
        errors.append(f"services.document_analyzer: {e}")
        print(f"  ✗ services.document_analyzer: {e}")
    
    try:
        from api.dependencies import get_current_user, get_current_active_user
        print("  ✓ api.dependencies")
    except Exception as e:
        errors.append(f"api.dependencies: {e}")
        print(f"  ✗ api.dependencies: {e}")
    
    try:
        from api.routers.auth import router as auth_router
        print("  ✓ api.routers.auth")
    except Exception as e:
        errors.append(f"api.routers.auth: {e}")
        print(f"  ✗ api.routers.auth: {e}")
    
    try:
        from api.routers.documents import router as documents_router
        print("  ✓ api.routers.documents")
    except Exception as e:
        errors.append(f"api.routers.documents: {e}")
        print(f"  ✗ api.routers.documents: {e}")
    
    try:
        from api.routers.analysis import router as analysis_router
        print("  ✓ api.routers.analysis")
    except Exception as e:
        errors.append(f"api.routers.analysis: {e}")
        print(f"  ✗ api.routers.analysis: {e}")
    
    try:
        from utils.logger import get_logger, setup_logger
        print("  ✓ utils.logger")
    except Exception as e:
        errors.append(f"utils.logger: {e}")
        print(f"  ✗ utils.logger: {e}")
    
    if errors:
        print(f"\n发现 {len(errors)} 个导入错误")
        return False
    
    print("\n所有模块导入成功!")
    return True


def check_auth_service():
    """检查认证服务"""
    print("\n" + "=" * 50)
    print("2. 检查认证服务...")
    
    try:
        from services.auth_service import (
            verify_password, get_password_hash, create_access_token
        )
        
        print("  测试密码哈希...")
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed), "密码验证失败"
        assert not verify_password("wrong_password", hashed), "错误密码验证通过"
        print("  ✓ 密码哈希和验证正常")
        
        print("  测试JWT令牌生成...")
        token = create_access_token(data={"sub": "testuser", "user_id": "123"})
        assert token, "令牌生成失败"
        print("  ✓ JWT令牌生成正常")
        
        print("\n认证服务检查通过!")
        return True
    except Exception as e:
        print(f"\n认证服务检查失败: {e}")
        return False


def check_document_processor():
    """检查文档处理器"""
    print("\n" + "=" * 50)
    print("3. 检查文档处理器（原项目代码）...")
    
    try:
        from services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        print("  检查支持的格式...")
        assert 'pdf' in processor.supported_formats
        assert 'docx' in processor.supported_formats
        assert 'xlsx' in processor.supported_formats
        print("  ✓ 支持PDF、DOCX、XLSX格式")
        
        print("  检查元数据提取器...")
        assert processor.metadata_extractor is not None
        print("  ✓ 元数据提取器已初始化")
        
        print("\n文档处理器检查通过!")
        return True
    except Exception as e:
        print(f"\n文档处理器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_chunking_service():
    """检查切片服务"""
    print("\n" + "=" * 50)
    print("4. 检查切片服务（原项目代码）...")
    
    try:
        from services.chunking_service import ChunkingService
        
        chunker = ChunkingService()
        
        print("  测试简单切片...")
        text = "这是第一行。\n" * 50
        # verify_auth_llm.py is a sync script, but chunk_document is async, we use chunk_by_semantic for sync test
        chunks = chunker.chunk_by_semantic(text, 100, 200)
        assert len(chunks) > 0, "切片失败"
        print(f"  ✓ 简单切片正常，生成 {len(chunks)} 个切片")
        
        print("  测试语义切片...")
        semantic_chunks = chunker.chunk_by_semantic(text, 50, 200)
        assert len(semantic_chunks) > 0, "语义切片失败"
        print(f"  ✓ 语义切片正常，生成 {len(semantic_chunks)} 个切片")
        
        print("\n切片服务检查通过!")
        return True
    except Exception as e:
        print(f"\n切片服务检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_document_analyzer():
    """检查文档分析器"""
    print("\n" + "=" * 50)
    print("5. 检查文档分析器...")
    
    try:
        from services.document_analyzer import DocumentAnalyzer
        
        print("  初始化文档分析器...")
        analyzer = DocumentAnalyzer(use_llm=False)
        print("  ✓ 文档分析器初始化成功（不使用LLM）")
        
        print("  检查组件...")
        assert analyzer.document_processor is not None
        assert analyzer.chunking_service is not None
        print("  ✓ 文档处理器和切片服务已集成")
        
        print("\n文档分析器检查通过!")
        return True
    except Exception as e:
        print(f"\n文档分析器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_models():
    """检查数据库模型"""
    print("\n" + "=" * 50)
    print("6. 检查数据库模型...")
    
    try:
        from models.database import User, Document, TestSet, Question, Evaluation, EvaluationResult, Configuration
        
        print("  检查User模型...")
        assert hasattr(User, '__tablename__')
        assert User.__tablename__ == 'users'
        print("  ✓ User模型正常")
        
        print("  检查Document模型...")
        assert hasattr(Document, '__tablename__')
        assert Document.__tablename__ == 'documents'
        assert hasattr(Document, 'is_analyzed')
        assert hasattr(Document, 'analyzed_at')
        print("  ✓ Document模型正常")
        
        print("\n数据库模型检查通过!")
        return True
    except Exception as e:
        print(f"\n数据库模型检查失败: {e}")
        return False


def check_schemas():
    """检查Pydantic模型"""
    print("\n" + "=" * 50)
    print("7. 检查Pydantic模型...")
    
    try:
        from schemas import UserCreate, User, Token, TokenData, Document
        
        print("  测试UserCreate模型...")
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        assert user_data.username == "testuser"
        print("  ✓ UserCreate模型正常")
        
        print("  测试Token模型...")
        token = Token(access_token="test_token", token_type="bearer")
        assert token.access_token == "test_token"
        print("  ✓ Token模型正常")
        
        print("\nPydantic模型检查通过!")
        return True
    except Exception as e:
        print(f"\nPydantic模型检查失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("RAG评估系统 - 认证和文档分析验证")
    print("=" * 50)
    
    results = {
        "模块导入": check_imports(),
        "认证服务": check_auth_service(),
        "文档处理器": check_document_processor(),
        "切片服务": check_chunking_service(),
        "文档分析器": check_document_analyzer(),
        "数据库模型": check_database_models(),
        "Pydantic模型": check_schemas()
    }
    
    print("\n" + "=" * 50)
    print("验证结果汇总:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("所有检查通过! 系统已准备就绪。")
        print("\n已迁移原项目代码:")
        print("  - document_processor.py: 文档处理（PDF/DOCX/XLSX）")
        print("  - metadata_extractor.py: LLM元数据提取")
        print("  - chunking_service.py: 智能切片服务")
    else:
        print("部分检查失败，请查看上述错误信息。")
    print("=" * 50)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
