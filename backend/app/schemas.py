from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Book schemas
class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    publish_year: Optional[int] = None


class BookCreate(BookBase):
    pass


class BookResponse(BookBase):
    id: int
    format: str
    file_path: str
    cover_path: Optional[str]
    chapter_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BookList(BaseModel):
    items: List[BookResponse]
    total: int


# Chapter schemas
class ChapterBase(BaseModel):
    chapter_number: int
    title: Optional[str] = None
    text_content: Optional[str] = None


class ChapterUpdate(BaseModel):
    title: Optional[str] = None


class ChapterResponse(ChapterBase):
    id: int
    book_id: int
    word_count: int
    audio_path: Optional[str]
    audio_duration: Optional[float]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Task schemas
class TaskCreate(BaseModel):
    book_id: int
    chapter_ids: Optional[List[int]] = None
    voice_preset_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    book_id: int
    chapter_id: int
    voice_preset_id: Optional[int]
    status: TaskStatusEnum
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskList(BaseModel):
    items: List[TaskResponse]
    total: int


# VoicePreset schemas
class VoicePresetBase(BaseModel):
    name: str
    is_default: bool = False
    voice_mode: str = "design"
    instruct: Optional[str] = None
    ref_audio_path: Optional[str] = None
    ref_text: Optional[str] = None
    num_step: int = 32
    guidance_scale: float = 2.0
    speed: float = 1.0
    language: Optional[str] = None


class VoicePresetCreate(VoicePresetBase):
    pass


class VoicePresetUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    voice_mode: Optional[str] = None
    instruct: Optional[str] = None
    ref_audio_path: Optional[str] = None
    ref_text: Optional[str] = None
    num_step: Optional[int] = None
    guidance_scale: Optional[float] = None
    speed: Optional[float] = None
    language: Optional[str] = None


class VoicePresetResponse(VoicePresetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VoicePresetList(BaseModel):
    items: List[VoicePresetResponse]
    total: int


# Config schemas
class ConfigUpdate(BaseModel):
    model_path: Optional[str] = None
    device: Optional[str] = None
    precision: Optional[str] = None
    asr_model_path: Optional[str] = None
    concurrency: Optional[int] = None
    audio_format: Optional[str] = None
    sample_rate: Optional[int] = None
    chunk_duration: Optional[float] = None
    chunk_threshold: Optional[float] = None
    chunk_size: Optional[int] = None
    book_dir: Optional[str] = None
    audio_dir: Optional[str] = None


class ConfigResponse(BaseModel):
    model_path: str = "/home/x/code/OmniVoice/models/OmniVoice"
    device: str = "auto"
    precision: str = "float16"
    asr_model_path: str = "/home/x/code/OmniVoice/models/whisper-large-v3-turbo"
    concurrency: int = 1
    audio_format: str = "wav"
    sample_rate: int = 24000
    chunk_duration: float = 15.0
    chunk_threshold: float = 30.0
    chunk_size: int = 200
    book_dir: str = "data/books"
    audio_dir: str = "data/audio"
