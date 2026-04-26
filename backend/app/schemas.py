from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
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
    # TTS 模式
    tts_mode: Optional[str] = None  # local | online | online_first
    
    # 本地模型配置
    model_path: Optional[str] = None
    device: Optional[str] = None
    precision: Optional[str] = None
    asr_model_path: Optional[str] = None
    
    # 在线 API 配置 (MiMo)
    mimo_api_key: Optional[str] = None
    mimo_base_url: Optional[str] = None
    mimo_model: Optional[str] = None
    mimo_default_voice: Optional[str] = None
    
    # 音频输出配置
    audio_format: Optional[str] = None
    sample_rate: Optional[int] = None
    concurrency: Optional[int] = None
    
    # 本地模型分段配置
    local_chunk_size: Optional[int] = None
    local_chunk_gap: Optional[float] = None
    
    # 在线 API 分段配置
    online_chunk_size: Optional[int] = None
    online_chunk_gap: Optional[float] = None
    
    # 目录配置
    book_dir: Optional[str] = None
    audio_dir: Optional[str] = None


class ConfigResponse(BaseModel):
    # TTS 模式
    tts_mode: str = "online_first"
    
    # 本地模型配置
    model_path: str = "models/OmniVoice"
    device: str = "auto"
    precision: str = "float16"
    asr_model_path: str = "models/whisper-large-v3-turbo"
    
    # 在线 API 配置 (MiMo)
    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    mimo_model: str = "mimo-v2.5-tts"
    mimo_default_voice: str = "冰糖"
    
    # 音频输出配置
    audio_format: str = "wav"
    sample_rate: int = 24000
    concurrency: int = 1
    
    # 本地模型分段配置
    local_chunk_size: int = 200
    local_chunk_gap: float = 0.3
    
    # 在线 API 分段配置
    online_chunk_size: int = 800
    online_chunk_gap: float = 0.3
    
    # 目录配置
    book_dir: str = "data/books"
    audio_dir: str = "data/audio"


# Auth schemas
class AuthStatusResponse(BaseModel):
    enabled: bool
    has_key: bool


class AuthChallengeResponse(BaseModel):
    nonce: str
    timestamp: int
    salt: str


class AuthVerifyRequest(BaseModel):
    response: str
    timestamp: int


class AuthEnableRequest(BaseModel):
    key_hash: str
    key_salt: str


class AuthDisableRequest(BaseModel):
    response: str
    timestamp: int


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    expires_in: Optional[int] = None
