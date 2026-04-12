from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import zipfile
import io
import logging
from pathlib import Path
from datetime import datetime

from app.database import get_db, init_db
from app.models.database import Book, Chapter, Task, VoicePreset, SystemConfig, TaskStatus
from app.schemas import (
    BookCreate, BookResponse, BookList,
    ChapterResponse, ChapterUpdate,
    TaskCreate, TaskResponse, TaskList,
    VoicePresetCreate, VoicePresetUpdate, VoicePresetResponse, VoicePresetList,
    ConfigUpdate, ConfigResponse,
    AuthStatusResponse, AuthChallengeResponse, AuthVerifyRequest,
    AuthEnableRequest, AuthDisableRequest, AuthResponse,
)
from app.services.ebook_parser import get_parser
from app.services.audio_converter import AudioConverter
from app.services.task_queue import TaskQueue
from app.services.auth import AuthManager, verify_jwt_token

logger = logging.getLogger(__name__)

app = FastAPI(title="x-reader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

task_queue = TaskQueue(max_workers=1)
_global_auth_manager: Optional[AuthManager] = None

LOCAL_MODEL_PATH = "/home/x/code/OmniVoice/models/OmniVoice"
LOCAL_ASR_MODEL_PATH = "/home/x/code/OmniVoice/models/whisper-large-v3-turbo"


def get_auth_manager(db: Session = Depends(get_db)) -> AuthManager:
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = AuthManager(db)
    else:
        _global_auth_manager.db = db
    return _global_auth_manager


def require_auth(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    from sqlalchemy.exc import OperationalError, ProgrammingError
    try:
        am = get_auth_manager(db)
        if not am.is_auth_enabled():
            return True

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="未授权访问")

        token = authorization[7:]
        if not verify_jwt_token(token):
            raise HTTPException(status_code=401, detail="Token 无效或已过期")

        return True
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError):
        # If database table doesn't exist yet, allow access
        return True
    except Exception as e:
        # Log unexpected errors but allow access
        logger.warning(f"Auth check failed: {e}")
        return True


@app.on_event("startup")
def startup():
    init_db()
    # Read config from database
    db = next(get_db())

    # Reset stuck tasks from previous session
    stuck_tasks = db.query(Task).filter(Task.status == TaskStatus.RUNNING).all()
    for task in stuck_tasks:
        task.status = TaskStatus.FAILED
        task.error_message = "后端重启，任务中断"
        task.finished_at = datetime.utcnow()
        # Reset corresponding chapter status
        chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first()
        if chapter and chapter.status == "converting":
            chapter.status = "pending"
    if stuck_tasks:
        db.commit()
        logger.info(f"已重置 {len(stuck_tasks)} 个中断的任务")

    # Also reset any chapters stuck in converting status
    stuck_chapters = db.query(Chapter).filter(Chapter.status == "converting").all()
    for chapter in stuck_chapters:
        chapter.status = "pending"
    if stuck_chapters:
        db.commit()
        logger.info(f"已重置 {len(stuck_chapters)} 个中断的章节")

    configs = {c.key: c.value for c in db.query(SystemConfig).all()}
    db.close()

    model_path = configs.get("model_path", LOCAL_MODEL_PATH)
    device = configs.get("device", "auto")
    precision = configs.get("precision", "float16")
    asr_model_path = configs.get("asr_model_path", LOCAL_ASR_MODEL_PATH)

    converter = AudioConverter(
        model_path=model_path,
        device=device,
        precision=precision,
        asr_model_path=asr_model_path,
    )
    task_queue.set_converter(converter)


@app.on_event("shutdown")
def shutdown():
    task_queue.shutdown()


# Auth endpoints
@app.get("/api/auth/status", response_model=AuthStatusResponse)
def get_auth_status(db: Session = Depends(get_db)):
    am = get_auth_manager(db)
    return am.get_auth_status()


@app.post("/api/auth/challenge", response_model=AuthChallengeResponse)
def create_auth_challenge(db: Session = Depends(get_db)):
    am = get_auth_manager(db)
    return am.create_challenge()


@app.post("/api/auth/verify", response_model=AuthResponse)
def verify_auth(data: AuthVerifyRequest, db: Session = Depends(get_db)):
    am = get_auth_manager(db)
    return am.verify_login(data.response, data.timestamp)


@app.post("/api/auth/enable", response_model=AuthResponse)
def enable_auth(data: AuthEnableRequest, db: Session = Depends(get_db)):
    am = get_auth_manager(db)
    if am.is_auth_enabled():
        return {"success": False, "message": "认证已启用"}
    return am.enable_auth(data.key_hash, data.key_salt)


@app.post("/api/auth/disable", response_model=AuthResponse)
def disable_auth(data: AuthDisableRequest, db: Session = Depends(get_db)):
    am = get_auth_manager(db)
    return am.disable_auth(data.response, data.timestamp)


@app.get("/api/books", response_model=BookList)
def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    query = db.query(Book)
    if search:
        query = query.filter(Book.title.contains(search) | Book.author.contains(search))
    total = query.count()
    books = query.order_by(Book.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return BookList(items=books, total=total)


@app.post("/api/books/upload", response_model=BookResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".epub", ".pdf", ".txt"]:
        raise HTTPException(400, "Unsupported file format")

    configs = {c.key: c.value for c in db.query(SystemConfig).all()}
    book_dir = configs.get("book_dir", "data/books")

    book_id = db.query(Book).count() + 1
    file_path = os.path.join(book_dir, str(book_id), file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parser = get_parser(file_path)
        result = parser.parse()
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(400, f"Failed to parse ebook: {str(e)}")

    book = Book(
        title=title or result["title"],
        author=author or result["author"],
        format=result["format"],
        file_path=file_path,
        chapter_count=len(result["chapters"]),
        status="parsed",
        publish_year=None,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    for ch_data in result["chapters"]:
        chapter = Chapter(
            book_id=book.id,
            chapter_number=ch_data["chapter_number"],
            title=ch_data["title"],
            text_content=ch_data["text_content"],
            word_count=ch_data["word_count"],
        )
        db.add(chapter)
    db.commit()

    return book


@app.get("/api/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@app.delete("/api/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Book not found")

    configs = {c.key: c.value for c in db.query(SystemConfig).all()}
    book_dir = configs.get("book_dir", "data/books")
    audio_dir = configs.get("audio_dir", "data/audio")

    db.query(Chapter).filter(Chapter.book_id == book_id).delete()
    db.query(Task).filter(Task.book_id == book_id).delete()
    db.delete(book)
    db.commit()

    book_path = os.path.join(book_dir, str(book_id))
    audio_path = os.path.join(audio_dir, str(book_id))
    if os.path.exists(book_path):
        shutil.rmtree(book_path)
    if os.path.exists(audio_path):
        shutil.rmtree(audio_path)

    return {"message": "Book deleted"}


@app.get("/api/books/{book_id}/chapters", response_model=List[ChapterResponse])
def list_chapters(book_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    chapters = db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.chapter_number).all()
    return chapters


@app.get("/api/chapters/{chapter_id}", response_model=ChapterResponse)
def get_chapter(chapter_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    return chapter


@app.patch("/api/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(chapter_id: int, data: ChapterUpdate, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    if data.title is not None:
        chapter.title = data.title
    db.commit()
    db.refresh(chapter)
    return chapter


@app.post("/api/tasks", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    book = db.query(Book).filter(Book.id == data.book_id).first()
    if not book:
        raise HTTPException(404, "Book not found")

    chapters = db.query(Chapter).filter(Chapter.book_id == data.book_id).all()
    if data.chapter_ids:
        chapters = [c for c in chapters if c.id in data.chapter_ids]

    if not chapters:
        raise HTTPException(400, "No chapters to process")

    for chapter in chapters:
        task = Task(
            book_id=data.book_id,
            chapter_id=chapter.id,
            voice_preset_id=data.voice_preset_id,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_queue.submit_task(task.id, db)

    return task


@app.get("/api/tasks", response_model=TaskList)
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    book_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if book_id:
        query = query.filter(Task.book_id == book_id)
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return TaskList(items=tasks, total=total)


@app.post("/api/tasks/{task_id}/retry", response_model=TaskResponse)
def retry_task(task_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status not in [TaskStatus.FAILED, TaskStatus.SKIPPED]:
        raise HTTPException(400, "Can only retry failed or skipped tasks")

    chapter = db.query(Chapter).filter(Chapter.id == task.chapter_id).first()
    if chapter:
        chapter.status = "pending"

    task.status = TaskStatus.PENDING
    task.error_message = None
    task.started_at = None
    task.finished_at = None
    db.commit()

    task_queue.submit_task(task.id, db)
    return task


@app.delete("/api/tasks/{task_id}")
def cancel_task(task_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(400, "Cannot cancel running task")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}


@app.get("/api/tasks/{task_id}/progress")
def get_task_progress(task_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")

    progress = task_queue.get_progress(task_id)
    if progress:
        return {
            "task_id": task_id,
            "status": task.status.value,
            "message": progress.get("message", ""),
            "elapsed": progress.get("elapsed", 0),
            "progress": progress.get("progress", 0),
        }

    # Return status from DB if no in-memory progress
    return {
        "task_id": task_id,
        "status": task.status.value,
        "message": task.status.value,
        "elapsed": 0,
        "progress": 0,
    }


@app.get("/api/audio/{book_id}/{chapter_id}")
def download_audio(book_id: int, chapter_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter or not chapter.audio_path:
        raise HTTPException(404, "Audio not found")
    return FileResponse(chapter.audio_path, filename=f"{chapter.title or chapter_id}.wav")


@app.get("/api/audio/{book_id}/{chapter_id}/stream")
def stream_audio(book_id: int, chapter_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id, Chapter.book_id == book_id).first()
    if not chapter or not chapter.audio_path:
        raise HTTPException(404, "Audio not found")

    # 根据文件扩展名设置媒体类型
    ext = Path(chapter.audio_path).suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".aac": "audio/aac",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".opus": "audio/opus",
        ".wma": "audio/x-ms-wma",
    }
    media_type = media_types.get(ext, "audio/wav")

    return FileResponse(
        chapter.audio_path,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        }
    )


@app.get("/api/audio/{book_id}/zip")
def download_book_audio_zip(book_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(404, "Book not found")

    chapters = db.query(Chapter).filter(
        Chapter.book_id == book_id,
        Chapter.audio_path.isnot(None)
    ).order_by(Chapter.chapter_number).all()

    if not chapters:
        raise HTTPException(404, "No audio files found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for chapter in chapters:
            if os.path.exists(chapter.audio_path):
                ext = Path(chapter.audio_path).suffix
                arcname = f"{chapter.chapter_number:03d}_{chapter.title or chapter.id}{ext}"
                zip_file.write(chapter.audio_path, arcname)

    zip_buffer.seek(0)
    return FileResponse(
        zip_buffer,
        media_type="application/zip",
        filename=f"{book.title}.zip",
    )


@app.post("/api/voice-presets", response_model=VoicePresetResponse)
def create_voice_preset(data: VoicePresetCreate, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    if data.is_default:
        db.query(VoicePreset).filter(VoicePreset.is_default == True).update({"is_default": False})
    preset = VoicePreset(**data.dict())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@app.get("/api/voice-presets", response_model=VoicePresetList)
def list_voice_presets(db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    presets = db.query(VoicePreset).order_by(VoicePreset.created_at.desc()).all()
    return VoicePresetList(items=presets, total=len(presets))


@app.get("/api/voice-presets/{preset_id}", response_model=VoicePresetResponse)
def get_voice_preset(preset_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    return preset


@app.put("/api/voice-presets/{preset_id}", response_model=VoicePresetResponse)
def update_voice_preset(preset_id: int, data: VoicePresetUpdate, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")

    update_data = data.dict(exclude_unset=True)
    if update_data.get("is_default"):
        db.query(VoicePreset).filter(VoicePreset.is_default == True).update({"is_default": False})

    for key, value in update_data.items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return preset


@app.delete("/api/voice-presets/{preset_id}")
def delete_voice_preset(preset_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    db.delete(preset)
    db.commit()
    return {"message": "Preset deleted"}


@app.patch("/api/voice-presets/{preset_id}/set-default", response_model=VoicePresetResponse)
def set_default_preset(preset_id: int, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    preset = db.query(VoicePreset).filter(VoicePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    db.query(VoicePreset).filter(VoicePreset.is_default == True).update({"is_default": False})
    preset.is_default = True
    db.commit()
    db.refresh(preset)
    return preset


@app.post("/api/voice-presets/upload-reference")
async def upload_reference_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    """上传参考音频并使用ASR自动转录"""
    import uuid
    import torch
    import torchaudio

    # 检查文件类型
    ext = Path(file.filename).suffix.lower()
    allowed_exts = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac"]
    if ext not in allowed_exts:
        raise HTTPException(400, f"不支持的音频格式，支持: {', '.join(allowed_exts)}")

    # 生成唯一文件名
    unique_id = str(uuid.uuid4())[:8]
    safe_filename = f"ref_{unique_id}{ext}"
    save_path = f"data/reference/{safe_filename}"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # 保存文件
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 截取前30秒
    duration = 0
    try:
        audio, sr = torchaudio.load(save_path)
        max_duration = 30  # 秒
        max_samples = min(audio.shape[-1], sr * max_duration)
        audio = audio[:, :max_samples]
        duration = max_samples / sr

        # 转换为WAV格式保存
        wav_path = f"data/reference/{unique_id}.wav"
        torchaudio.save(wav_path, audio, sr)

        # 删除原始文件（如果不是wav）
        if ext != ".wav" and os.path.exists(save_path):
            os.remove(save_path)

        save_path = wav_path
    except Exception as e:
        logger.warning(f"音频处理失败: {e}")

    # 使用ASR转录
    transcribed_text = ""
    try:
        # 使用本地HuggingFace Whisper模型进行转录
        import torch
        import torchaudio
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        # 获取设备
        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # 本地Whisper模型路径
        model_id = "/home/x/code/OmniVoice/models/whisper-large-v3-turbo"
        
        logger.info(f"使用本地Whisper ASR模型: {model_id}, 设备: {device}")
        
        # 加载模型和处理器
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        )
        model.to(device)
        
        processor = AutoProcessor.from_pretrained(model_id)
        
        # 创建pipeline
        asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
        
        # 转录音频
        result = asr_pipeline(save_path)
        transcribed_text = result["text"].strip()
        logger.info(f"转录结果: {transcribed_text}")
    except Exception as e:
        logger.error(f"ASR转录失败: {e}")
        transcribed_text = "(自动转录失败，请手动输入)"

    return {
        "success": True,
        "audio_path": save_path,  # 文件系统路径，用于保存和生成
        "audio_url": f"/api/reference-audio/{Path(save_path).name}",  # API路径，用于播放
        "transcribed_text": transcribed_text,
        "duration": duration,
        "message": "音频上传成功",
    }


@app.get("/api/reference-audio/{filename}")
def get_reference_audio(filename: str, _auth: bool = Depends(require_auth)):
    """获取参考音频文件"""
    file_path = f"data/reference/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(404, "音频文件不存在")

    ext = Path(filename).suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".aac": "audio/aac",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }
    media_type = media_types.get(ext, "audio/wav")

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/config", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db)):
    configs = {c.key: c.value for c in db.query(SystemConfig).all()}
    return ConfigResponse(**{
        "model_path": configs.get("model_path", LOCAL_MODEL_PATH),
        "device": configs.get("device", "auto"),
        "precision": configs.get("precision", "float16"),
        "asr_model_path": configs.get("asr_model_path", LOCAL_ASR_MODEL_PATH),
        "concurrency": int(configs.get("concurrency", "1")),
        "audio_format": configs.get("audio_format", "wav"),
        "sample_rate": int(configs.get("sample_rate", "24000")),
        "chunk_duration": float(configs.get("chunk_duration", "15.0")),
        "chunk_threshold": float(configs.get("chunk_threshold", "30.0")),
        "chunk_size": int(configs.get("chunk_size", "200")),
        "book_dir": configs.get("book_dir", "data/books"),
        "audio_dir": configs.get("audio_dir", "data/audio"),
    })


@app.put("/api/config", response_model=ConfigResponse)
def update_config(data: ConfigUpdate, db: Session = Depends(get_db), _auth: bool = Depends(require_auth)):
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config:
                config.value = str(value)
            else:
                db.add(SystemConfig(key=key, value=str(value)))
    db.commit()

    if "concurrency" in update_data:
        task_queue.max_workers = int(update_data["concurrency"])
        task_queue.executor._max_workers = int(update_data["concurrency"])

    if "chunk_size" in update_data:
        if task_queue.converter:
            task_queue.converter.chunk_size = int(update_data["chunk_size"])

    return get_config(db)


@app.post("/api/config/test")
async def test_tts(
    text: str = Form(...),
    voice_preset_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    _auth: bool = Depends(require_auth),
):
    """测试 TTS 配置，生成音频并返回"""
    import uuid
    import tempfile

    # 获取配置
    configs = {c.key: c.value for c in db.query(SystemConfig).all()}
    audio_format = configs.get("audio_format", "wav")
    chunk_size = int(configs.get("chunk_size", "200"))

    # 获取语音预设
    voice_mode = "auto"
    instruct = None
    ref_audio_path = None
    ref_text = None
    language = None
    num_step = 32
    guidance_scale = 2.0
    speed = 1.0

    if voice_preset_id:
        preset = db.query(VoicePreset).filter(VoicePreset.id == voice_preset_id).first()
        if preset:
            voice_mode = preset.voice_mode
            instruct = preset.instruct
            ref_audio_path = preset.ref_audio_path
            ref_text = preset.ref_text
            language = preset.language
            num_step = preset.num_step
            guidance_scale = preset.guidance_scale
            speed = preset.speed

    # 生成临时文件路径
    test_id = str(uuid.uuid4())[:8]
    output_path = f"data/audio/test_{test_id}.{audio_format}"

    try:
        # 确保 converter 已加载
        if not task_queue.converter:
            raise HTTPException(500, "TTS 模型未加载")

        task_queue.converter.chunk_size = chunk_size

        result = task_queue.converter.convert_chapter(
            text=text,
            output_path=output_path,
            voice_mode=voice_mode,
            instruct=instruct,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            num_step=num_step,
            guidance_scale=guidance_scale,
            speed=speed,
        )

        return {
            "success": True,
            "audio_url": f"/api/config/test-audio/test_{test_id}.{audio_format}",
            "duration": result["duration"],
            "message": f"生成成功，时长 {result['duration']:.1f} 秒",
        }
    except Exception as e:
        return {
            "success": False,
            "audio_url": None,
            "duration": 0,
            "message": f"生成失败: {str(e)}",
        }


@app.get("/api/config/test-audio/{filename}")
def get_test_audio(filename: str, _auth: bool = Depends(require_auth)):
    """获取测试音频文件"""
    file_path = f"data/audio/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(404, "音频文件不存在")

    ext = Path(filename).suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".aac": "audio/aac",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".opus": "audio/opus",
        ".wma": "audio/x-ms-wma",
    }
    media_type = media_types.get(ext, "audio/wav")

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
