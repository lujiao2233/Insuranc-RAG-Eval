"""任务管理器模块
实现异步任务的管理功能，支持长时间运行任务的状态跟踪
"""
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor

from utils.logger import get_logger

logger = get_logger("task_manager")


class TaskManager:
    """任务管理器类
    
    提供异步任务的完整生命周期管理，包括创建、执行、状态更新和结果获取。
    
    任务状态：
        - pending: 待执行
        - running: 执行中
        - finished: 已完成
        - failed: 执行失败
    """
    
    def __init__(self, max_workers: int = 10):
        self._lock = threading.Lock()
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TaskManager")
    
    def create_task(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
        """创建新任务
        
        Args:
            task_type: 任务类型标识符
            params: 任务参数字典
            
        Returns:
            任务ID
        """
        task_id = uuid.uuid4().hex
        now = datetime.now().isoformat()
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "status": "pending",
                "progress": 0.0,
                "message": "",
                "logs": [],
                "result": None,
                "error": "",
                "params": params or {},
                "created_at": now,
                "updated_at": now,
            }
        logger.info(f"创建任务: {task_id}, 类型: {task_type}")
        return task_id
    
    def start_task(self, task_id: str, target: Callable, *args, **kwargs) -> None:
        """启动任务执行
        
        Args:
            task_id: 任务ID
            target: 目标函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        def runner():
            self.update_status(task_id, "running")
            try:
                target(*args, **kwargs)
            except Exception as e:
                self.fail_task(task_id, str(e))
                logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
        
        self._executor.submit(runner)
        logger.info(f"提交任务到线程池: {task_id}")
    
    def update_status(self, task_id: str, status: str) -> None:
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task["status"] = status
            task["updated_at"] = datetime.now().isoformat()
    
    def update_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> None:
        """更新任务进度"""
        progress = max(0.0, min(1.0, progress))
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task["progress"] = float(progress)
            if message is not None:
                task["message"] = str(message)
            task["updated_at"] = datetime.now().isoformat()
    
    def append_log(self, task_id: str, message: str) -> None:
        """追加任务日志"""
        text = str(message or "")
        if not text:
            return
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            logs = task.get("logs") or []
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
            if len(logs) > 200:
                logs = logs[-200:]
            task["logs"] = logs
            task["updated_at"] = datetime.now().isoformat()
    
    def finish_task(self, task_id: str, result: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> None:
        """标记任务完成"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task["status"] = "finished"
            task["progress"] = 1.0
            if result is not None:
                task["result"] = result
            if message is not None:
                task["message"] = str(message)
            task["updated_at"] = datetime.now().isoformat()
        logger.info(f"任务完成: {task_id}")
    
    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task["status"] = "failed"
            task["error"] = str(error or "")
            task["updated_at"] = datetime.now().isoformat()
        logger.error(f"任务失败: {task_id}, 错误: {error}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return dict(task)
    
    def list_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取任务列表"""
        with self._lock:
            tasks = list(self._tasks.values())
            if task_type:
                tasks = [t for t in tasks if t.get("type") == task_type]
            return [dict(t) for t in tasks]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """清理旧任务"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0
        with self._lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                try:
                    updated_at = datetime.fromisoformat(task.get("updated_at", ""))
                    if updated_at < cutoff and task.get("status") in ("finished", "failed"):
                        to_remove.append(task_id)
                except Exception:
                    pass
            for task_id in to_remove:
                del self._tasks[task_id]
                removed += 1
        logger.info(f"清理了 {removed} 个旧任务")
        return removed


task_manager = TaskManager()
