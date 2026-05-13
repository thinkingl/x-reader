import os
import logging
import time
import asyncio
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.database import Task, Chapter, Book, TaskStatus, VoicePreset, SystemConfig
from app.services.audio_converter import AudioConverter
from app.services.task_context import TaskContext, TaskCancelledError
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self, max_workers: int = 1):
        self.max_workers = max_workers
        self.converter: Optional[AudioConverter] = None
        self.tasks: Dict[int, asyncio.Task] = {}
        self.contexts: Dict[int, TaskContext] = {}
        self.semaphore: Optional[asyncio.Semaphore] = None
        self.gpu_lock: Optional[asyncio.Lock] = None
        self._running = False

    async def start(self):
        """在事件循环中初始化"""
        self.semaphore = asyncio.Semaphore(self.max_workers)
        self.gpu_lock = asyncio.Lock()
        self._running = True

    def set_converter(self, converter: AudioConverter):
        self.converter = converter

    def configure_online_tts(self):
        """从数据库配置在线 TTS"""
        if not self.converter:
            return

        db = SessionLocal()
        try:
            configs = {c.key: c.value for c in db.query(SystemConfig).all()}
            tts_mode = configs.get("tts_mode", "online_first")
            mimo_api_key = configs.get("mimo_api_key", "")
            mimo_base_url = configs.get("mimo_base_url", "https://token-plan-cn.xiaomimimo.com/v1")
            online_chunk_size = int(configs.get("online_chunk_size", "800"))
            tts_timeout = int(configs.get("tts_timeout", "120"))

            self.converter.configure_online_tts(
                tts_mode=tts_mode,
                api_key=mimo_api_key,
                online_chunk_size=online_chunk_size,
                base_url=mimo_base_url,
                tts_timeout=tts_timeout,
            )
        finally:
            db.close()

    def get_progress(self, task_id: int) -> Optional[Dict]:
        ctx = self.contexts.get(task_id)
        if ctx:
            return {
                "message": ctx.progress_message,
                "elapsed": ctx.elapsed,
                "progress": ctx.progress_value,
            }
        return None

    def cancel_task(self, task_id: int):
        """取消正在运行或排队的任务"""
        ctx = self.contexts.get(task_id)
        if ctx:
            ctx.cancelled = True
        task = self.tasks.get(task_id)
        if task and not task.done():
            task.cancel()

    def set_concurrency(self, new_workers: int):
        """动态调整并发数"""
        self.max_workers = new_workers
        self.semaphore = asyncio.Semaphore(new_workers)
        logger.info(f"并发数已更新为: {new_workers}")

    async def submit_task(self, task_id: int, db: Session):
        """提交任务（非阻塞）"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.QUEUED

        chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first()
        if chapter:
            chapter.status = "queued"

        db.commit()

        ctx = TaskContext(
            task_id=task_id,
            start_time=time.time(),
        )
        self.contexts[task_id] = ctx

        asyncio_task = asyncio.create_task(self._execute_task(task_id, ctx))
        self.tasks[task_id] = asyncio_task

    async def _execute_task(self, task_id: int, ctx: TaskContext):
        """异步执行任务"""
        async with self.semaphore:
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                db.commit()

                ctx.progress_message = "开始转换..."

                chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first()
                if not chapter:
                    task.status = TaskStatus.FAILED
                    task.error_message = "Chapter not found"
                    db.commit()
                    return

                # 删除旧的音频文件
                if chapter.audio_path and os.path.exists(chapter.audio_path):
                    try:
                        os.remove(chapter.audio_path)
                    except Exception as e:
                        logger.warning(f"删除旧音频文件失败: {e}")

                chapter.status = "converting"
                db.commit()

                book = db.query(Book).filter(Book.id == task.book_id).first()
                configs = {c.key: c.value for c in db.query(SystemConfig).all()}
                audio_dir = configs.get("audio_dir", "data/audio")
                audio_format = configs.get("audio_format", "wav")
                audio_bitrate = configs.get("audio_bitrate", "64k")

                # 同步格式配置到 converter（实时生效）
                self.converter.audio_format = audio_format
                self.converter.audio_bitrate = audio_bitrate

                # 解析预设参数
                import json
                preset_params = None
                voice_preset = None
                if task.voice_preset_id:
                    voice_preset = db.query(VoicePreset).filter(VoicePreset.id == task.voice_preset_id).first()

                chapter.voice_preset_name = voice_preset.name if voice_preset else None
                db.commit()

                if voice_preset:
                    preset_params = {
                        "engine": voice_preset.engine or "local_omnivoice",
                        "voice_mode": voice_preset.voice_mode or "auto",
                    }
                    if voice_preset.params:
                        try:
                            preset_params.update(json.loads(voice_preset.params))
                        except Exception:
                            pass
                    if voice_preset.instruct:
                        preset_params.setdefault("instruct", voice_preset.instruct)
                    if voice_preset.ref_audio_path:
                        preset_params.setdefault("ref_audio_path", voice_preset.ref_audio_path)
                    if voice_preset.ref_text:
                        preset_params.setdefault("ref_text", voice_preset.ref_text)
                    preset_params.setdefault("num_step", voice_preset.num_step or 32)
                    preset_params.setdefault("guidance_scale", voice_preset.guidance_scale or 2.0)
                    preset_params.setdefault("speed", voice_preset.speed or 1.0)
                    if voice_preset.language:
                        preset_params.setdefault("language", voice_preset.language)

                # 根据引擎选择分段大小
                engine = (preset_params or {}).get("engine", "local_omnivoice")
                if engine == "online_mimo":
                    chunk_size = int(configs.get("online_chunk_size", "2000"))
                    chunk_size_en = int(configs.get("online_chunk_size_en", "400"))
                    if configs.get("mimo_api_key") and not self.converter.mimo_client:
                        from app.services.mimo_tts import MiMoTTSClient
                        self.converter.mimo_client = MiMoTTSClient(
                            api_key=configs["mimo_api_key"],
                            base_url=configs.get("mimo_base_url"),
                        )
                else:
                    chunk_size = int(configs.get("local_chunk_size", "200"))
                    chunk_size_en = int(configs.get("local_chunk_size_en", "120"))

                # 设置 per-task 的分段大小
                ctx.chunk_size = chunk_size
                ctx.chunk_size_en = chunk_size_en

                # 生成文件路径
                safe_title = "".join(c for c in chapter.title if c.isalnum() or c in " _-").strip()[:30] if chapter.title else ""
                safe_title = safe_title.replace("/", "").replace("\\", "")
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

                def progress_cb(msg, progress=None):
                    ctx.update_progress(msg, progress)

                max_retries = int(configs.get("max_retries", "3"))
                last_error = None
                result = None
                for attempt in range(max_retries):
                    ctx.check_cancelled()

                    try:
                        # GPU 任务需要互斥锁，在线 TTS 不需要
                        if engine == "online_mimo":
                            result = await self._run_with_ctx(
                                task_id, chapter.text_content, output_path,
                                preset_params, metadata, progress_cb, ctx
                            )
                        else:
                            async with self.gpu_lock:
                                result = await self._run_with_ctx(
                                    task_id, chapter.text_content, output_path,
                                    preset_params, metadata, progress_cb, ctx
                                )
                        break
                    except TaskCancelledError:
                        raise
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            wait_time = attempt + 1
                            logger.warning(
                                f"Task {task_id} attempt {attempt + 1}/{max_retries} failed: {e}. "
                                f"Retrying in {wait_time}s..."
                            )
                            ctx.progress_message = f"第 {attempt + 1} 次尝试失败，{wait_time}s 后重试..."
                            ctx.progress_value = 0
                            await asyncio.sleep(wait_time)
                        else:
                            raise

                if result is None:
                    raise last_error or Exception("Conversion failed after retries")

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

            except TaskCancelledError:
                logger.info(f"Task {task_id} cancelled")
                try:
                    from app.services.checkpoint import delete as cp_delete
                    cp_delete(task_id)
                except Exception:
                    pass
                try:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task.status = TaskStatus.CANCELLED
                        task.finished_at = datetime.utcnow()
                    chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first() if task else None
                    if chapter and chapter.status == "converting":
                        chapter.status = "pending"
                    db.commit()
                except Exception as cleanup_err:
                    logger.error(f"Task {task_id} cleanup failed: {cleanup_err}")
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                try:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task:
                        task.status = TaskStatus.FAILED
                        task.error_message = str(e)
                        task.finished_at = datetime.utcnow()
                    chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first() if task else None
                    if chapter and chapter.status == "converting":
                        chapter.status = "pending"
                    db.commit()
                except Exception as cleanup_err:
                    logger.error(f"Task {task_id} cleanup failed: {cleanup_err}")
            finally:
                db.close()
                self.tasks.pop(task_id, None)
                self.contexts.pop(task_id, None)

    async def _run_with_ctx(self, task_id, text, output_path, preset, metadata, progress_cb, ctx):
        """在线程池中执行同步的 converter 调用"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.converter.convert_chapter_with_checkpoint(
                task_id=task_id,
                text=text,
                output_path=output_path,
                preset=preset,
                metadata=metadata,
                progress_callback=progress_cb,
                ctx=ctx,
            )
        )

    async def submit_book_tasks(self, book_id: int, voice_preset_id: Optional[int] = None):
        db = SessionLocal()
        try:
            chapters = db.query(Chapter).filter(
                Chapter.book_id == book_id,
                Chapter.status.in_(["pending", "failed"])
            ).order_by(Chapter.chapter_number).all()

            for chapter in chapters:
                existing_task = db.query(Task).filter(
                    Task.chapter_id == chapter.id,
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING])
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

                await self.submit_task(task.id, db)
        finally:
            db.close()

    async def shutdown(self):
        """优雅关闭：取消所有任务"""
        self._running = False
        for task_id, task in list(self.tasks.items()):
            ctx = self.contexts.get(task_id)
            if ctx:
                ctx.cancelled = True
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
