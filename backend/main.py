from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from config.settings import settings
from api.routers import documents, testsets, evaluations, auth, config, analysis, reports, usage
from config.database import engine
from models.database import Base
from services.task_manager import task_manager
from utils.logger import setup_logger

log_dir = os.path.join(os.path.dirname(__file__), "logs")
setup_logger(log_dir=log_dir, console_output=True, file_output=True)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库初始化完成")
        task_manager.start_workers()
        logger.info("持久化任务队列已启动")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise
    yield
    logger.info("关闭数据库连接...")
    task_manager.stop_workers()


app = FastAPI(
    title="RAG 评估系统 API",
    description="用于评估 RAG 系统性能的 API 接口",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(testsets.router, prefix="/api/v1/testsets", tags=["testsets"])
app.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])


@app.get("/")
def read_root():
    return {"message": "RAG 评估系统 API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
