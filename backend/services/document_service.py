"""文档服务
处理文档上传、处理、存储等业务逻辑，集成原始代码库中的高级功能
"""
import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from models.database import Document as DocumentModel
from schemas import DocumentCreate, DocumentUpdate
from services.document_processor import DocumentProcessor
from services.metadata_extractor import MetadataExtractor
from services.chunking_service import ChunkingService
from services.config_service import ConfigService
from utils.logger import get_logger

logger = get_logger("document_service")


class DocumentService:
    """文档服务类"""
    
    def __init__(self, upload_dir: str = "data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.document_processor = DocumentProcessor()
        self.metadata_extractor = MetadataExtractor()
        self.chunking_service = ChunkingService()

    @staticmethod
    def _normalize_page_count(value: Any) -> Optional[int]:
        """将页数字段规范化为正整数。"""
        if value is None:
            return None
        try:
            page_count = int(value)
        except (TypeError, ValueError):
            return None
        return page_count if page_count > 0 else None
    
    async def save_uploaded_file(self, file, filename: str) -> str:
        """保存上传的文件"""
        # 生成唯一文件名
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.upload_dir / unique_filename
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return str(file_path)
    
    async def create_document_record(self, document_data: DocumentCreate, file_path: str, user_id: str) -> DocumentModel:
        """创建文档记录"""
        # 这里应该连接数据库创建文档记录
        # 临时返回模拟对象
        document = DocumentModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            filename=document_data.filename,
            file_path=file_path,
            file_type=document_data.file_type,
            file_size=document_data.file_size,
            category=document_data.category,
            upload_time=datetime.utcnow(),
            created_at=datetime.utcnow(),
            is_processed=False,
            is_analyzed=False,
            metadata=None
        )
        return document
    
    async def process_document(self, document: DocumentModel) -> Dict[str, Any]:
        """处理文档，提取内容和元数据"""
        try:
            # 使用文档处理器处理文件
            processed_doc = self.document_processor.process_file(document.file_path)
            
            if processed_doc:
                # 提取智能元数据
                metadata = self.metadata_extractor.extract_intelligent_metadata(
                    processed_doc.content,
                    processed_doc.filename
                )
                
                # 使用智能切片服务
                chunks = self.chunking_service.process_document_content(
                    processed_doc.content,
                    metadata.get("outline", [])
                )
                
                # 更新文档元数据
                document_metadata = {
                    "content": processed_doc.content,
                    "text": processed_doc.content,
                    "outline": metadata.get("outline", []),
                    "metadata": metadata,
                    "chunks_count": len(chunks),
                    "processed_at": datetime.utcnow().isoformat()
                }
                
                return {
                    "success": True,
                    "metadata": document_metadata,
                    "chunks": chunks,
                    "message": "文档处理成功"
                }
            else:
                return {
                    "success": False,
                    "message": "文档处理失败"
                }
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            return {
                "success": False,
                "message": f"处理文档时出错: {str(e)}"
            }
    
    async def analyze_document(self, document: DocumentModel, db: Any = None) -> Dict[str, Any]:
        """执行文档分析的核心逻辑（提取 -> 提纲 -> 切片 -> 实体）"""
        from config.database import SessionLocal
        from models.database import DocumentChunk
        from services.llm_service import get_llm_service
        from services.question_generator import get_question_generator
        
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
            
        try:
            # 1. 文本提取
            processed_doc = self.document_processor.process_file(document.file_path)
            if not processed_doc or not processed_doc.get("text_content"):
                return {"success": False, "message": "文本提取失败或内容为空"}
            
            text_content = processed_doc["text_content"]
            processed_page_count = self._normalize_page_count(processed_doc.get("page_count"))
            
            # 获取LLM服务
            llm_service = get_llm_service(user_id=document.user_id, db=db)
            
            # 2. 智能提纲与实体提取
            analysis_result = await self.metadata_extractor.extract(text_content, llm=llm_service)
            if not analysis_result or not analysis_result.get("outline"):
                return {"success": False, "message": "智能提纲提取失败"}
            
            outline = analysis_result.get("outline", [])
            product_entities = analysis_result.get("product_entities", [])
            doc_type = analysis_result.get("doc_type", "其他")
            
            metadata_values = {k: v for k, v in analysis_result.items() if k not in ["outline", "product_entities"]}
            if processed_page_count:
                metadata_values.setdefault("page_count", processed_page_count)
            try:
                cs = ConfigService(db)
                short_merge_threshold = int(cs.get_config_value(str(document.user_id), "chunking.short_merge_threshold", "60"))
                max_chunk_chars = int(cs.get_config_value(str(document.user_id), "chunking.max_chunk_chars", "500"))
                metadata_values["_chunking_short_merge_threshold"] = max(20, short_merge_threshold)
                metadata_values["_chunking_max_chunk_chars"] = max(100, max_chunk_chars)
            except Exception as cfg_e:
                logger.warning(f"读取切片配置失败，使用默认值: {cfg_e}")
            
            document.outline = outline
            document.product_entities = product_entities
            document.doc_metadata_col = metadata_values
            if processed_page_count:
                document.page_count = processed_page_count
            document.file_type = doc_type if doc_type != "其他" else document.file_type
            
            # 3. 语义切片与向量化
            self.chunking_service.llm = llm_service
            chunks = await self.chunking_service.chunk_document(
                text_content, 
                outline, 
                analysis_result
            )
            
            # 获取向量
            generator = get_question_generator(user_id=document.user_id, db=db)
            all_vectors = []
            if chunks:
                try:
                    chunk_texts = [c["content"] for c in chunks]
                    batch_size = 10
                    for i in range(0, len(chunk_texts), batch_size):
                        batch = chunk_texts[i:i+batch_size]
                        vectors = await generator.get_embeddings(batch)
                        all_vectors.extend(vectors)
                except Exception as e:
                    logger.error(f"获取切片向量失败: {e}")
            
            # 清除旧切片
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
            
            # 将切片存入数据库
            for idx, chunk_data in enumerate(chunks):
                new_chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_data["content"],
                    md5=chunk_data["md5"],
                    sequence_number=chunk_data["sequence_number"],
                    start_char=chunk_data["start_char"],
                    end_char=chunk_data["end_char"],
                    chunk_metadata=chunk_data["metadata"],
                    entities=product_entities,
                    dense_vector=all_vectors[idx] if idx < len(all_vectors) else None
                )
                db.add(new_chunk)
            
            # 4. 更新文档状态
            document.is_analyzed = True
            document.status = 'active'
            document.analyzed_at = datetime.now()
            
            if own_db:
                db.commit()
                
            return {"success": True, "message": "文档分析完成", "chunks_count": len(chunks)}
            
        except Exception as e:
            if own_db:
                db.rollback()
            logger.error(f"分析失败: {str(e)}")
            return {"success": False, "message": f"分析失败: {str(e)}"}
        finally:
            if own_db:
                db.close()
    
    async def analyze_document_task(self, document_id: str, user_id: str, task_id: str):
        """后台异步分析任务：封装 analyze_document 并提供进度反馈"""
        from services.task_manager import task_manager
        from config.database import SessionLocal
        from models.database import Document as DocumentModel
        
        db = SessionLocal()
        document = None
        try:
            task_manager.update_progress(task_id, 0.1, "正在启动文档分析...")
            document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            if not document:
                task_manager.fail_task(task_id, "文档不存在")
                return

            # 直接调用核心分析逻辑
            task_manager.update_progress(task_id, 0.2, "正在提取文本并进行语义分析...")
            result = await self.analyze_document(document, db=db)
            
            if result["success"]:
                db.commit() # 关键：提交 analyze_document 中的更改
                task_manager.finish_task(task_id, message=f"分析完成，生成了 {result.get('chunks_count', 0)} 个切片")
            else:
                # 失败时必须落库失败状态，避免前端一直识别为 processing 导致无限轮询
                document.status = 'failed'
                document.is_analyzed = False
                db.commit()
                task_manager.fail_task(task_id, result["message"])

        except Exception as e:
            db.rollback()
            logger.error(f"分析任务失败: {str(e)}")
            try:
                if document is None:
                    document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
                if document:
                    document.status = 'failed'
                    document.is_analyzed = False
                    db.commit()
            except Exception as status_err:
                db.rollback()
                logger.error(f"写入文档失败状态时出错: {status_err}")
            task_manager.fail_task(task_id, f"分析失败: {str(e)}")
        finally:
            db.close()
    
    async def get_document(self, document_id: uuid.UUID) -> Optional[DocumentModel]:
        """获取文档信息"""
        # 这里应该从数据库查询文档
        pass
    
    async def update_document(self, document_id: uuid.UUID, update_data: DocumentUpdate) -> Optional[DocumentModel]:
        """更新文档信息"""
        # 这里应该更新数据库中的文档记录
        pass
    
    async def delete_document(self, document_id: uuid.UUID) -> bool:
        """删除文档"""
        # 这里应该删除数据库记录和文件
        pass
    
    async def list_documents(self, skip: int = 0, limit: int = 100) -> list:
        """获取文档列表"""
        # 这里应该从数据库查询文档列表
        pass
    
    async def get_document_content(self, document: DocumentModel) -> str:
        """获取文档内容"""
        if document.doc_metadata_col:
            try:
                metadata = document.doc_metadata_col
                if "content" in metadata:
                    return metadata["content"]
                elif "text" in metadata:
                    return metadata["text"]
            except Exception:
                pass
        
        # 如果元数据中没有内容，则从文件读取
        if document.file_path and os.path.exists(document.file_path):
            try:
                with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(10000)  # 限制读取大小
            except Exception as e:
                logger.error(f"读取文档内容失败: {str(e)}")
        
        return ""
