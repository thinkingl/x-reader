import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database import Task, Chapter, Book, TaskStatus, VoicePreset, SystemConfig
from app.services.audio_converter import AudioConverter
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, max_workers: int = 1):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.converter: Optional[AudioConverter] = None
        self.futures: Dict[int, Future] = {}
        self.progress: Dict[int, Dict] = {}  # task_id -> {message, start_time}

    def set_converter(self, converter: AudioConverter):
        self.converter = converter

    def get_progress(self, task_id: int) -> Optional[Dict]:
        return self.progress.get(task_id)

    def _update_progress(self, task_id: int, message: str, progress: float = None):
        if task_id in self.progress:
            elapsed = time.time() - self.progress[task_id]["start_time"]
            self.progress[task_id]["message"] = message
            self.progress[task_id]["elapsed"] = round(elapsed, 1)
            if progress is not None:
                self.progress[task_id]["progress"] = round(progress, 1)

    def submit_task(self, task_id: int, db: Session):
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()

        self.progress[task_id] = {
            "message": "排队等待中...",
            "start_time": time.time(),
            "elapsed": 0,
            "progress": 0,
        }

        future = self.executor.submit(self._execute_task, task_id)
        self.futures[task_id] = future

    def _execute_task(self, task_id: int):
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return

            chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first()
            if not chapter:
                task.status = TaskStatus.FAILED
                task.error_message = "Chapter not found"
                db.commit()
                return

            # 删除旧的音频文件（如果存在）
            if chapter.audio_path and os.path.exists(chapter.audio_path):
                try:
                    os.remove(chapter.audio_path)
                    logger.info(f"已删除旧音频文件: {chapter.audio_path}")
                except Exception as e:
                    logger.warning(f"删除旧音频文件失败: {e}")

            # 更新章节状态为 converting
            chapter.status = "converting"
            db.commit()

            book = db.query(Book).filter(Book.id == task.book_id).first()
            voice_preset = None
            if task.voice_preset_id:
                voice_preset = db.query(VoicePreset).filter(VoicePreset.id == task.voice_preset_id).first()

            voice_mode = voice_preset.voice_mode if voice_preset else "auto"
            instruct = voice_preset.instruct if voice_preset else None
            ref_audio_path = voice_preset.ref_audio_path if voice_preset else None
            ref_text = voice_preset.ref_text if voice_preset else None
            language = voice_preset.language if voice_preset else None
            num_step = voice_preset.num_step if voice_preset else 32
            guidance_scale = voice_preset.guidance_scale if voice_preset else 2.0
            speed = voice_preset.speed if voice_preset else 1.0

            configs = {c.key: c.value for c in db.query(SystemConfig).all()}
            audio_dir = configs.get("audio_dir", "data/audio")
            audio_format = configs.get("audio_format", "wav")
            chunk_size = int(configs.get("chunk_size", "200"))

            # 文件名格式: {序号}_{标题}.{格式}，序号补零保证排序正确
            safe_title = "".join(c for c in chapter.title if c.isalnum() or c in " _-").strip()[:30] if chapter.title else ""
            filename = f"{chapter.chapter_number:03d}_{safe_title}.{audio_format}"
            output_path = os.path.join(audio_dir, str(book.id), filename)
            chapter_count = db.query(Chapter).filter(Chapter.book_id == book.id).count()

            metadata = {
                "title": chapter.title,
                "artist": book.author,
                "album": book.title,
                "genre": "有声书",
                "track_number": chapter.chapter_number,
                "total_tracks": chapter_count,
            }

            self._update_progress(task_id, f"正在转换: {chapter.title[:20]}...", 0)

            # Set progress callback
            def progress_cb(msg, progress=None):
                self._update_progress(task_id, msg, progress)

            self.converter.set_progress_callback(progress_cb)
            self.converter.chunk_size = chunk_size

            result = self.converter.convert_chapter(
                text=chapter.text_content,
                output_path=output_path,
                voice_mode=voice_mode,
                instruct=instruct,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
                language=language,
                num_step=num_step,
                guidance_scale=guidance_scale,
                speed=speed,
                metadata=metadata,
            )

            if os.path.exists(output_path):
                chapter.audio_path = output_path
                chapter.audio_duration = result["duration"]
                chapter.status = "completed"
                task.status = TaskStatus.COMPLETED
                task.finished_at = datetime.utcnow()
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "Audio file not generated"

            db.commit()

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.finished_at = datetime.utcnow()
                    db.commit()
            except:
                pass
        finally:
            db.close()
            if task_id in self.futures:
                del self.futures[task_id]
            if task_id in self.progress:
                del self.progress[task_id]

    def submit_book_tasks(self, book_id: int, voice_preset_id: Optional[int] = None):
        db = SessionLocal()
        try:
            chapters = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.status.in_(["pending", "failed"])
            ).order_by(Chapter.chapter_number).all()

            for chapter in chapters:
                existing_task = db.query(Task).filter(
                    Task.chapter_id == chapter.id,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                ).first()

                if existing_task:
                    continue

                chapter.status = "pending"
                task = Task(
                    book_id=book_id,
                    chapter_id=chapter.id,
                    voice_preset_id=voice_preset_id,
                    status=TaskStatus.PENDING,
                )
                db.add(task)
                db.commit()

                self.submit_task(task.id, db)

        finally:
            db.close()

    def shutdown(self):
        self.executor.shutdown(wait=False)
