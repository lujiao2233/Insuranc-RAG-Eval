"""任务管理器模块
实现基于数据库的持久化任务队列和状态跟踪。
"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config.database import SessionLocal
from models.database import BackgroundTask
from utils.logger import get_logger

logger = get_logger("task_manager")


class TaskCancelledError(RuntimeError):
    """任务被用户取消。"""


class TaskManager:
    """数据库持久化任务管理器。"""

    def __init__(self, max_workers: int = 4, poll_interval: float = 1.0):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TaskWorker")
        self._active_task_ids = set()
        self._max_workers = max_workers
        self._poll_interval = poll_interval
        self._worker_id = f"worker-{uuid.uuid4().hex[:8]}"

    def start_workers(self) -> None:
        """启动轮询线程。"""
        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                return
            self._stop_event.clear()
            self._reset_running_tasks()
            self._worker_thread = threading.Thread(
                target=self._poll_loop,
                name="PersistentTaskPoller",
                daemon=True,
            )
            self._worker_thread.start()
        logger.info("持久化任务队列已启动")

    def stop_workers(self) -> None:
        """停止轮询线程。"""
        self._stop_event.set()
        worker = self._worker_thread
        if worker and worker.is_alive():
            worker.join(timeout=3)
        logger.info("持久化任务队列已停止")

    def create_task(
        self,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        max_attempts: int = 1,
    ) -> str:
        """创建持久化任务。"""
        task_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            task = BackgroundTask(
                id=task_id,
                task_type=task_type,
                status="pending",
                progress=0.0,
                message="",
                logs=[],
                result=None,
                error="",
                params=params or {},
                attempt_count=0,
                max_attempts=max(1, int(max_attempts or 1)),
            )
            db.add(task)
            db.commit()
            logger.info(f"创建任务: {task_id}, 类型: {task_type}")
            return task_id
        finally:
            db.close()

    def submit_task(
        self,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        max_attempts: int = 1,
    ) -> str:
        """创建并提交任务到持久化队列。"""
        task_id = self.create_task(task_type, params=params, max_attempts=max_attempts)
        self.update_status(task_id, "pending")
        return task_id

    def start_task(self, task_id: str) -> None:
        """兼容旧接口：将已创建任务加入持久化队列。"""
        logger.warning("start_task() 已进入兼容模式，建议改用 submit_task(): %s", task_id)
        self.update_status(task_id, "pending")

    def update_status(self, task_id: str, status: str) -> None:
        """更新任务状态。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            task.status = status
            if status == "running" and not task.started_at:
                task.started_at = datetime.now()
            if status in {"finished", "failed", "cancelled"}:
                task.finished_at = datetime.now()
            db.commit()
        finally:
            db.close()

    def update_progress(
        self,
        task_id: str,
        progress: float,
        message: Optional[str] = None,
        *,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
    ) -> None:
        """更新任务进度。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            task.progress = max(0.0, min(1.0, float(progress)))
            if message is not None:
                task.message = str(message)
            if current_step is not None:
                task.current_step = int(current_step)
            if total_steps is not None:
                task.total_steps = int(total_steps)
            db.commit()
        finally:
            db.close()

    def append_log(self, task_id: str, message: str) -> None:
        """追加任务日志。"""
        text = str(message or "").strip()
        if not text:
            return
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            logs = list(task.logs or [])
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
            task.logs = logs[-200:]
            db.commit()
        finally:
            db.close()

    def finish_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        *,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
    ) -> None:
        """标记任务完成。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            task.status = "finished"
            task.progress = 1.0
            task.result = result
            task.error = ""
            task.finished_at = datetime.now()
            if message is not None:
                task.message = str(message)
            if current_step is not None:
                task.current_step = int(current_step)
            if total_steps is not None:
                task.total_steps = int(total_steps)
            elif task.total_steps is not None and task.current_step is None:
                task.current_step = task.total_steps
            db.commit()
            logger.info(f"任务完成: {task_id}")
        finally:
            db.close()

    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            task.status = "failed"
            task.error = str(error or "")
            task.finished_at = datetime.now()
            db.commit()
            logger.error(f"任务失败: {task_id}, 错误: {error}")
        finally:
            db.close()

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务。

        pending 任务直接取消；running 任务标记为 cancelling，等待协作式退出。
        """
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                raise RuntimeError("任务不存在")
            if task.status in {"finished", "failed", "cancelled"}:
                raise RuntimeError("当前任务状态不支持取消")
            if task.status == "pending":
                task.status = "cancelled"
                task.message = "任务已取消"
                task.error = "任务已取消"
                task.finished_at = datetime.now()
            else:
                task.status = "cancelling"
                task.message = "任务取消中，等待安全退出"
            logs = list(task.logs or [])
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 用户请求取消任务")
            task.logs = logs[-200:]
            db.commit()
            return self._serialize_task(task)
        finally:
            db.close()

    def retry_task(self, task_id: str) -> Dict[str, Any]:
        """重试失败或已取消任务。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                raise RuntimeError("任务不存在")
            if task.status not in {"failed", "cancelled"}:
                raise RuntimeError("只有失败或已取消的任务才支持重试")

            from services.task_handlers import prepare_task_for_retry

            prepare_task_for_retry(task.task_type, task.params or {})
            logs = list(task.logs or [])
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 用户请求重试任务")
            task.status = "pending"
            task.progress = 0.0
            task.message = "任务已重新入队"
            task.error = ""
            task.result = None
            task.current_step = 0
            task.total_steps = None
            task.worker_id = None
            task.claimed_at = None
            task.started_at = None
            task.finished_at = None
            task.logs = logs[-200:]
            db.commit()
            return self._serialize_task(task)
        finally:
            db.close()

    def ensure_not_cancelled(self, task_id: str) -> None:
        """在长任务执行过程中检查是否收到取消请求。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                raise TaskCancelledError("任务不存在")
            if task.status in {"cancelling", "cancelled"}:
                raise TaskCancelledError("任务已取消")
        finally:
            db.close()

    def mark_cancelled(self, task_id: str, message: Optional[str] = None) -> None:
        """将任务标记为已取消。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return
            task.status = "cancelled"
            task.message = message or "任务已取消"
            task.error = message or "任务已取消"
            task.finished_at = datetime.now()
            db.commit()
        finally:
            db.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息。"""
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                return None
            return self._serialize_task(task)
        finally:
            db.close()

    def list_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取任务列表。"""
        db = SessionLocal()
        try:
            query = db.query(BackgroundTask)
            if task_type:
                query = query.filter(BackgroundTask.task_type == task_type)
            tasks = query.order_by(BackgroundTask.created_at.desc()).all()
            return [self._serialize_task(task) for task in tasks]
        finally:
            db.close()

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """清理旧任务。"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        db = SessionLocal()
        try:
            removed = db.query(BackgroundTask).filter(
                BackgroundTask.updated_at < cutoff,
                BackgroundTask.status.in_(["finished", "failed", "cancelled"]),
            ).delete(synchronize_session=False)
            db.commit()
            logger.info(f"清理了 {removed} 个旧任务")
            return int(removed or 0)
        finally:
            db.close()

    def _serialize_task(self, task: BackgroundTask) -> Dict[str, Any]:
        return {
            "id": task.id,
            "type": task.task_type,
            "status": task.status,
            "progress": float(task.progress or 0.0),
            "message": task.message or "",
            "logs": task.logs or [],
            "result": task.result,
            "error": task.error or "",
            "params": task.params or {},
            "current_step": task.current_step,
            "total_steps": task.total_steps,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
            "can_cancel": task.status in {"pending", "running", "cancelling"},
            "can_retry": task.status in {"failed", "cancelled"},
        }

    def _reset_running_tasks(self) -> None:
        db = SessionLocal()
        try:
            db.query(BackgroundTask).filter(
                BackgroundTask.status.in_(["running", "cancelling"])
            ).update(
                {
                    BackgroundTask.status: "pending",
                    BackgroundTask.worker_id: None,
                    BackgroundTask.claimed_at: None,
                    BackgroundTask.message: "服务重启后重新入队",
                },
                synchronize_session=False,
            )
            db.commit()
        finally:
            db.close()

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._dispatch_pending_tasks()
            except Exception as exc:
                logger.error(f"任务轮询失败: {exc}", exc_info=True)
            self._stop_event.wait(self._poll_interval)

    def _dispatch_pending_tasks(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                if len(self._active_task_ids) >= self._max_workers:
                    return

            task_id = self._claim_next_task()
            if not task_id:
                return

            with self._lock:
                self._active_task_ids.add(task_id)
            self._executor.submit(self._run_claimed_task, task_id)

    def _claim_next_task(self) -> Optional[str]:
        db = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(
                BackgroundTask.status == "pending"
            ).order_by(BackgroundTask.created_at.asc()).first()
            if not task:
                return None
            task.status = "running"
            task.worker_id = self._worker_id
            task.claimed_at = datetime.now()
            task.started_at = task.started_at or datetime.now()
            task.attempt_count = int(task.attempt_count or 0) + 1
            db.commit()
            return task.id
        finally:
            db.close()

    def _run_claimed_task(self, task_id: str) -> None:
        try:
            db = SessionLocal()
            try:
                task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if not task:
                    return
                task_type = task.task_type
                params = dict(task.params or {})
            finally:
                db.close()

            from services.task_handlers import run_task_handler

            run_task_handler(task_type, params, task_id)
        except TaskCancelledError as exc:
            self.mark_cancelled(task_id, str(exc))
            logger.info("任务已取消: %s", task_id)
        except Exception as exc:
            self.fail_task(task_id, str(exc))
            logger.error(f"执行任务失败: {task_id}, 错误: {exc}", exc_info=True)
        finally:
            with self._lock:
                self._active_task_ids.discard(task_id)


task_manager = TaskManager()
