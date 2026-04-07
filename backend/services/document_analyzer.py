"""文档分析器服务
整合文档处理、元数据提取和切片功能
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from utils.logger import get_logger
from services.document_processor import DocumentProcessor
from services.metadata_extractor import MetadataExtractor
from services.chunking_service import ChunkingService

logger = get_logger("document_analyzer")


class DocumentAnalyzer:
    """文档分析器类
    
    整合文档处理、元数据提取和智能切片功能。
    提供完整的文档分析流水线。
    """
    
    def __init__(self, use_llm: bool = True):
        """初始化文档分析器
        
        Args:
            use_llm: 是否使用LLM进行元数据提取
        """
        self.document_processor = DocumentProcessor()
        self.chunking_service = ChunkingService()
        
        if use_llm:
            # 检查是否配置了API密钥
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
            if api_key:
                self.metadata_extractor = MetadataExtractor()
            else:
                logger.warning("未配置LLM API密钥，文档分析器将不使用LLM功能")
                self.metadata_extractor = None
        else:
            self.metadata_extractor = None
    
    async def analyze_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """分析文档
        
        完整的文档分析流程：文本提取 -> 元数据提取 -> 提纲生成
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            包含元数据、大纲和切片的字典，失败返回None
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None
            
            # 检查是否配置了LLM API密钥
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
            if not api_key:
                logger.error("未配置LLM API密钥，无法进行文档分析")
                raise ValueError("未配置LLM API密钥，无法进行文档分析")
            
            logger.info(f"开始分析文档: {path.name}")
            
            result = self.document_processor.process_file(str(path))
            
            if not result:
                return None
            
            text_content = result.get("text_content", "")
            metadata = result.get("metadata", {})
            outline = result.get("outline", [])
            
            # 使用LLM进行智能元数据提取和提纲生成
            if self.metadata_extractor:
                logger.info(f"开始使用LLM分析文档: {path.name}")
                # 使用异步提取
                llm_result = await self.metadata_extractor.extract(text_content)
                
                # 合并LLM提取的元数据
                if llm_result:
                    metadata.update(llm_result.get("metadata_values", {}))
                    
                    # 如果LLM生成了提纲，则使用LLM的提纲
                    llm_outline = llm_result.get("outline", [])
                    if llm_outline:
                        outline = llm_outline
            
            chunks = await self.chunking_service.chunk_document(
                text=text_content,
                outline=outline,
                doc_metadata=metadata
            )
            
            logger.info(f"文档分析完成: {path.name}, 切片数: {len(chunks)}")
            
            return {
                "filename": result.get("filename"),
                "file_path": result.get("file_path"),
                "file_type": result.get("file_type"),
                "file_size": result.get("file_size"),
                "page_count": result.get("page_count"),
                "text_content": text_content[:5000],
                "metadata": metadata,
                "outline": outline,
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"文档分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_text(self, file_path: str) -> Optional[str]:
        """仅提取文档文本内容
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            文档文本内容，失败返回None
        """
        return self.document_processor.read_document_content(file_path)
    
    def get_preview(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """获取文档预览信息
        
        Args:
            file_path: 文档文件路径
            file_type: 文档类型（pdf/docx/xlsx）
            
        Returns:
            文档预览信息字典
        """
        return self.document_processor.get_document_preview(file_path, file_type)
    
    async def chunk_text(
        self, 
        text: str, 
        outline: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """对文本进行切片
        
        Args:
            text: 待切片文本
            outline: 文档提纲（可选）
            metadata: 文档元数据（可选）
            
        Returns:
            切片列表
        """
        if outline:
            return await self.chunking_service.chunk_document(
                text=text,
                outline=outline,
                doc_metadata=metadata or {}
            )
        else:
            return self.chunking_service.chunk_by_semantic(
                text=text,
                metadata=metadata
            )
