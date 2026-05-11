import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class TaskCancelledError(asyncio.CancelledError):
    """任务被取消时抛出"""
    pass


@dataclass
class TaskContext:
    """每个任务的独立上下文，不与其他任务共享"""
    task_id: int
    cancelled: bool = False
    chunk_size: Optional[int] = None
    chunk_size_en: Optional[int] = None
    progress_message: str = ""
    progress_value: float = 0.0
    start_time: float = 0.0
    elapsed: float = 0.0
    _progress_callback: Optional[Callable] = field(default=None, repr=False)

    def update_progress(self, message: str, progress: float = None):
        """更新进度并检查取消状态"""
        if self.cancelled:
            raise TaskCancelledError(f"任务 {self.task_id} 已取消")
        self.progress_message = message
        if progress is not None:
            self.progress_value = round(progress, 1)
        if self.start_time > 0:
            self.elapsed = round(time.time() - self.start_time, 1)
        if self._progress_callback:
            self._progress_callback(message, progress)
        logger.info(message)

    def check_cancelled(self):
        """检查任务是否已取消"""
        if self.cancelled:
            raise TaskCancelledError(f"任务 {self.task_id} 已取消")
