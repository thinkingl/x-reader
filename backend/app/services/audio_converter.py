import os
import logging
import torch
import torchaudio
import numpy as np
import time
import re
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK

logger = logging.getLogger(__name__)


class AudioConverter:
    def __init__(self, model_path: str, device: str = "auto", precision: str = "float16",
                 asr_model_path: str = "openai/whisper-large-v3-turbo",
                 allow_download: bool = False):
        self.model_path = model_path
        self.device = self._get_device(device)
        self.precision = precision
        self.asr_model_path = asr_model_path
        self.allow_download = allow_download
        self.model = None
        self.progress_callback: Optional[Callable] = None
        self.chunk_size = 200  # 每段文本的最大字符数
        self.chunk_size_en = 120  # 英文分段大小
        self._local = threading.local()
        self._cancelled = False  # 取消标志  # 线程本地存储，用于并发安全的回调
        
        # 在线 TTS 配置
        self.tts_mode = "local"  # local | online | online_first
        self.mimo_client = None
        self.online_chunk_size = 800  # 在线 TTS 分段大小
        self.tts_timeout = 120  # TTS 单次请求超时秒数
        self._model_lock = threading.Lock()  # 模型加载互斥锁

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback
    
    def configure_online_tts(self, tts_mode: str, api_key: str = "", 
                              online_chunk_size: int = 800, base_url: str = None,
                              tts_timeout: int = 120):
        """配置在线 TTS"""
        self.tts_mode = tts_mode
        self.online_chunk_size = online_chunk_size
        self.tts_timeout = tts_timeout
        
        if api_key:
            from app.services.mimo_tts import MiMoTTSClient
            self.mimo_client = MiMoTTSClient(api_key=api_key, base_url=base_url, timeout=tts_timeout)
            logger.info(f"在线 TTS 已配置: mode={tts_mode}, chunk_size={online_chunk_size}, timeout={tts_timeout}s")
        else:
            self.mimo_client = None
            if tts_mode in ("online", "online_first"):
                logger.warning("在线 TTS 模式但未提供 API Key")

    def _report_progress(self, message: str, progress: float = None):
        if self._cancelled:
            raise Exception("任务已取消")
        cb = getattr(self._local, 'progress_callback', None) or self.progress_callback
        if cb:
            cb(message, progress)
        logger.info(message)

    def _get_device(self, device: str) -> str:
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return device

    def load_model(self):
        if self.model is None:
            if not self.allow_download:
                model_file = os.path.join(self.model_path, "model.safetensors")
                if not os.path.isfile(model_file):
                    raise FileNotFoundError(
                        f"本地模型文件不存在: {model_file}\n"
                        f"请先下载模型到 {self.model_path}，或设置环境变量 ALLOW_MODEL_DOWNLOAD=true 允许在线下载"
                    )

            with self._model_lock:
                # 双重检查：可能其他线程已经加载完了
                if self.model is not None:
                    return

                from omnivoice import OmniVoice
                dtype = torch.float16 if self.precision == "float16" else torch.float32
                self._report_progress(f"正在加载模型: {self.model_path} (设备: {self.device})")
                self.model = OmniVoice.from_pretrained(
                    self.model_path,
                    device_map=self.device,
                    dtype=dtype,
                    load_asr=True,
                    asr_model_name=self.asr_model_path,
                )
                self._report_progress(f"模型加载完成 (设备: {self.device})")

    def _split_text(self, text: str, chunk_size: int = None, chunk_size_en: int = None) -> List[str]:
        """将长文本按标点符号分段，根据文本语言选择分段大小"""
        explicit = chunk_size is not None
        
        if chunk_size is None:
            chunk_size = self.chunk_size
        if chunk_size_en is None:
            chunk_size_en = self.chunk_size_en
        
        # 未显式指定 chunk_size 时，自动检测语言并切换
        if not explicit:
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            total_chars = sum(1 for c in text if c.isalpha() or '\u4e00' <= c <= '\u9fff')
            is_chinese = total_chars > 0 and chinese_chars / total_chars > 0.3
            chunk_size = chunk_size if is_chinese else chunk_size_en
        
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        # 按句子分隔符分割（中文 + 英文）
        sentences = re.split(r'([。！？；\n\.!\?])', text)

        current_chunk = ""
        for i, part in enumerate(sentences):
            if len(current_chunk) + len(part) <= chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    # 单个句子超过限制时，在次级标点处拆分
                    if len(current_chunk) > chunk_size:
                        for sub in self._split_by_secondary_punct(current_chunk, chunk_size):
                            chunks.append(sub.strip())
                    else:
                        chunks.append(current_chunk.strip())
                current_chunk = part

        if current_chunk.strip():
            if len(current_chunk) > chunk_size:
                for sub in self._split_by_secondary_punct(current_chunk, chunk_size):
                    chunks.append(sub.strip())
            else:
                chunks.append(current_chunk.strip())

        # 合并过短的段落
        merged_chunks = []
        temp = ""
        for chunk in chunks:
            if len(temp) + len(chunk) <= chunk_size:
                temp += chunk
            else:
                if temp:
                    merged_chunks.append(temp)
                temp = chunk
        if temp:
            merged_chunks.append(temp)

        return merged_chunks if merged_chunks else [text]

    def _split_by_secondary_punct(self, text: str, chunk_size: int) -> List[str]:
        """在次级标点处拆分超长句子，优先级：逗号分号 > 冒号 > 空格"""
        split_points = []
        # 逗号分号（优先级1）
        for m in re.finditer(r';|；', text):
            split_points.append((m.end(), 1))
        for m in re.finditer(r',|，', text):
            split_points.append((m.end(), 1))
        # 冒号（优先级2）
        for m in re.finditer(r':|：', text):
            split_points.append((m.end(), 2))
        # 空格（优先级3）
        for m in re.finditer(r'\s', text):
            split_points.append((m.end(), 3))
        
        if not split_points:
            if len(text) > chunk_size:
                return self._split_anywhere(text, chunk_size)
            return [text]
        
        split_points.sort(key=lambda x: x[0])  # 按位置排序
        
        chunks = []
        start = 0
        for i in range(len(split_points)):
            pos, pri = split_points[i]
            if pos - start <= chunk_size:
                continue  # 还没超限，继续往后看
            
            # 当前已超限，在 [start, pos) 范围内找最佳拆分点
            # 从右往左找最高优先级的点
            best = None
            for j in range(i - 1, -1, -1):
                pj, pj_pri = split_points[j]
                if pj_pri <= (best[1] if best else 3):
                    best = (pj, pj_pri)
                if pj_pri == 1:  # 遇到逗号分号，直接使用
                    break
            
            if best and best[0] - start > 0:
                chunk = text[start:best[0]].strip()
                if chunk:
                    chunks.append(chunk)
                start = best[0]
        
        # 最后一段
        if start < len(text):
            chunk = text[start:].strip()
            if chunk:
                if len(chunk) > chunk_size:
                    # 最后一段仍然超长，退化为简单拆分
                    for sub in self._split_anywhere(chunk, chunk_size):
                        chunks.append(sub)
                else:
                    chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    def _split_anywhere(self, text: str, chunk_size: int) -> List[str]:
        """退避方案：按空格强制拆分，无空格时按字符等长拆分"""
        chunks = []
        words = text.split()
        if len(words) > 1:
            current = ""
            for word in words:
                if len(current) + len(word) + 1 <= chunk_size:
                    current = (current + " " + word).strip()
                else:
                    if current:
                        chunks.append(current)
                    current = word
            if current:
                chunks.append(current)
        else:
            # 无空格，按字符等长拆分
            for i in range(0, len(text), chunk_size):
                chunks.append(text[i:i+chunk_size])
        return chunks

    def _generate_single_chunk(
        self,
        text: str,
        voice_mode: str = "auto",
        instruct: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        num_step: int = 32,
        guidance_scale: float = 2.0,
        speed: float = 1.0,
    ):
        """生成单个文本段的音频"""
        kwargs = {
            "text": text,
            "num_step": num_step,
            "guidance_scale": guidance_scale,
            "speed": speed,
        }

        if language:
            kwargs["language"] = language

        if voice_mode == "clone" and ref_audio_path:
            kwargs["ref_audio"] = ref_audio_path
            if ref_text:
                kwargs["ref_text"] = ref_text
        elif voice_mode == "design" and instruct:
            kwargs["instruct"] = instruct

        audios = self.model.generate(**kwargs)
        audio = audios[0]
        
        # 确保返回 torch Tensor
        if isinstance(audio, np.ndarray):
            audio = torch.from_numpy(audio)
        if audio.dtype == torch.int16:
            audio = audio.float() / 32768.0
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)
        
        return audio

    def convert_chapter(
        self,
        text: str,
        output_path: str,
        preset: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """转换章节文本为音频，根据预设的 engine 路由"""
        cb = progress_callback or self.progress_callback
        self._local.progress_callback = cb
        start_time = time.time()

        params = preset or {}
        engine = params.get("engine", "local_omnivoice")

        if engine == "online_mimo":
            return self._convert_mimo(
                text=text,
                output_path=output_path,
                params=params,
                start_time=start_time,
                metadata=metadata,
            )
        else:
            return self._convert_omnivoice(
                text=text,
                output_path=output_path,
                params=params,
                start_time=start_time,
                metadata=metadata,
            )

    def _convert_mimo(
        self,
        text: str,
        output_path: str,
        params: Dict[str, Any],
        start_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """在线 MiMo TTS 转换"""
        if not self.mimo_client:
            raise Exception("MiMo 客户端未配置")

        voice_mode = params.get("voice_mode", "auto")
        chunk_size = params.get("chunk_size")
        chunks = self._split_text(text, chunk_size=chunk_size)
        total_chunks = len(chunks)

        self._report_progress(f"[MiMo] 文本分为 {total_chunks} 段，共 {len(text)} 字符", 0)

        import io
        audio_chunks = []
        sample_rate = 24000

        for i, chunk in enumerate(chunks):
            progress = (i / total_chunks) * 100
            self._report_progress(f"[MiMo] 转换第 {i+1}/{total_chunks} 段", progress)

            audio_bytes = self.mimo_client.synthesize(
                text=chunk,
                voice_mode=voice_mode,
                voice_id=params.get("voice_id", "冰糖"),
                instruct=params.get("instruct"),
                ref_audio_path=params.get("ref_audio_path"),
                audio_format="wav",
            )
            audio_buffer = io.BytesIO(audio_bytes)
            tensor, sr = torchaudio.load(audio_buffer)
            audio_chunks.append(tensor)

            progress = ((i + 1) / total_chunks) * 100
            self._report_progress(f"[MiMo] 第 {i+1}/{total_chunks} 段完成", progress)

        # 合并音频
        self._report_progress("正在合并音频...", 95)
        if len(audio_chunks) > 1:
            silence = torch.zeros(1, int(0.3 * sample_rate))
            merged = audio_chunks[0]
            for t in audio_chunks[1:]:
                merged = torch.cat([merged, silence, t], dim=1)
        else:
            merged = audio_chunks[0]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, merged, sample_rate)

        if metadata:
            self._write_metadata(output_path, metadata)

        elapsed = time.time() - start_time
        duration = merged.shape[-1] / sample_rate
        self._report_progress(f"[MiMo] 完成: {duration:.1f}s ({elapsed:.1f}s)", 100)
        return {"audio_path": output_path, "duration": duration, "sample_rate": sample_rate, "engine": "online_mimo"}

    def _convert_omnivoice(
        self,
        text: str,
        output_path: str,
        params: Dict[str, Any],
        start_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """本地 OmniVoice TTS 转换"""
        self.load_model()

        voice_mode = params.get("voice_mode", "auto")
        chunk_size = params.get("chunk_size")
        chunks = self._split_text(text, chunk_size=chunk_size)
        total_chunks = len(chunks)

        self._report_progress(f"[OmniVoice] 文本分为 {total_chunks} 段，共 {len(text)} 字符", 0)

        audio_tensors = []

        for i, chunk in enumerate(chunks):
            progress = (i / total_chunks) * 100
            self._report_progress(f"[OmniVoice] 转换第 {i+1}/{total_chunks} 段", progress)

            tensor = self._generate_single_chunk(
                text=chunk,
                voice_mode=voice_mode,
                instruct=params.get("instruct"),
                ref_audio_path=params.get("ref_audio_path"),
                ref_text=params.get("ref_text"),
                language=params.get("language"),
                num_step=params.get("num_step", 32),
                guidance_scale=params.get("guidance_scale", 2.0),
                speed=params.get("speed", 1.0),
            )
            audio_tensors.append(tensor)
            progress = ((i + 1) / total_chunks) * 100
            self._report_progress(f"[OmniVoice] 第 {i+1}/{total_chunks} 段完成", progress)

        self._report_progress("正在合并音频...", 95)
        if len(audio_tensors) > 1:
            silence = torch.zeros(1, int(0.3 * self.model.sampling_rate))
            merged = audio_tensors[0]
            for t in audio_tensors[1:]:
                merged = torch.cat([merged, silence, t], dim=1)
        else:
            merged = audio_tensors[0]

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, merged, self.model.sampling_rate)

        if metadata:
            self._write_metadata(output_path, metadata)

        elapsed = time.time() - start_time
        duration = merged.shape[-1] / self.model.sampling_rate
        self._report_progress(f"[OmniVoice] 完成: {duration:.1f}s ({elapsed:.1f}s)", 100)
        return {"audio_path": output_path, "duration": duration, "sample_rate": self.model.sampling_rate, "engine": "local_omnivoice"}
    
    def _convert_online(
        self,
        text: str,
        output_path: str,
        voice_mode: str = "auto",
        instruct: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        voice_id: Optional[str] = None,
        audio_format: str = "wav",
        speed: float = 1.0,
        start_time: float = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """在线 TTS 转换"""
        if start_time is None:
            start_time = time.time()
        
        chunks = self._split_text(text)
        total_chunks = len(chunks)
        
        self._report_progress(f"[在线] 文本分为 {total_chunks} 段，共 {len(text)} 字符", 0)
        
        audio_chunks = []
        sample_rate = 24000  # MiMo API 固定 24kHz
        
        for i, chunk in enumerate(chunks):
            chunk_preview = chunk[:30] + "..." if len(chunk) > 30 else chunk
            progress = (i / total_chunks) * 100
            self._report_progress(f"[在线] 转换第 {i+1}/{total_chunks} 段: {chunk_preview}", progress)
            
            chunk_start = time.time()
            
            # 调用 MiMo API
            audio_bytes = self.mimo_client.synthesize(
                text=chunk,
                voice_mode=voice_mode,
                voice_id=voice_id or "冰糖",
                instruct=instruct,
                ref_audio_path=ref_audio_path,
                audio_format="wav",
                speed=speed,
            )
            
            # 解码 WAV 音频
            import io
            audio_buffer = io.BytesIO(audio_bytes)
            audio_tensor, sample_rate = torchaudio.load(audio_buffer)
            audio_chunks.append(audio_tensor)
            
            chunk_elapsed = time.time() - chunk_start
            progress = ((i + 1) / total_chunks) * 100
            self._report_progress(f"[在线] 第 {i+1}/{total_chunks} 段完成 ({chunk_elapsed:.1f}s)", progress)
        
        # 合并音频
        self._report_progress("正在合并音频...", 95)
        if len(audio_chunks) > 1:
            silence_duration = 0.3
            silence = torch.zeros(1, int(silence_duration * sample_rate))
            merged_audio = audio_chunks[0]
            for tensor in audio_chunks[1:]:
                merged_audio = torch.cat([merged_audio, silence, tensor], dim=1)
        else:
            merged_audio = audio_chunks[0]
        
        elapsed = time.time() - start_time
        
        # 保存音频
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, merged_audio, sample_rate)
        
        if metadata:
            self._write_metadata(output_path, metadata)
        
        duration = merged_audio.shape[-1] / sample_rate
        rtf = elapsed / duration if duration > 0 else 0
        self._report_progress(f"[在线] 转换完成: {duration:.1f}s 音频, 耗时 {elapsed:.1f}s (RTF: {rtf:.2f})", 100)
        
        return {
            "audio_path": output_path,
            "duration": duration,
            "sample_rate": sample_rate,
            "engine": "online",
        }
    
    def _convert_local(
        self,
        text: str,
        output_path: str,
        voice_mode: str = "auto",
        instruct: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        language: Optional[str] = None,
        num_step: int = 32,
        guidance_scale: float = 2.0,
        speed: float = 1.0,
        start_time: float = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """本地 TTS 转换"""
        if start_time is None:
            start_time = time.time()
        
        self.load_model()
        
        # 分段处理长文本
        chunks = self._split_text(text)
        total_chunks = len(chunks)
        
        self._report_progress(f"[本地] 文本分为 {total_chunks} 段，共 {len(text)} 字符", 0)
        
        # 创建调试输出目录
        debug_dir = os.path.join(os.path.dirname(output_path), "debug", Path(output_path).stem)
        os.makedirs(debug_dir, exist_ok=True)
        
        audio_tensors = []
        
        for i, chunk in enumerate(chunks):
            chunk_preview = chunk[:30] + "..." if len(chunk) > 30 else chunk
            progress = (i / total_chunks) * 100
            self._report_progress(f"[本地] 转换第 {i+1}/{total_chunks} 段: {chunk_preview}", progress)
            
            chunk_start = time.time()
            audio_tensor = self._generate_single_chunk(
                text=chunk,
                voice_mode=voice_mode,
                instruct=instruct,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
                language=language,
                num_step=num_step,
                guidance_scale=guidance_scale,
                speed=speed,
            )
            chunk_elapsed = time.time() - chunk_start
            audio_tensors.append(audio_tensor)
            
            # 保存调试文件
            chunk_base = f"{i+1:03d}"
            with open(os.path.join(debug_dir, f"{chunk_base}.txt"), "w", encoding="utf-8") as f:
                f.write(chunk)
            torchaudio.save(
                os.path.join(debug_dir, f"{chunk_base}.wav"),
                audio_tensor,
                self.model.sampling_rate,
            )
            
            progress = ((i + 1) / total_chunks) * 100
            self._report_progress(f"[本地] 第 {i+1}/{total_chunks} 段完成 ({chunk_elapsed:.1f}s)", progress)
        
        # 合并音频
        self._report_progress("正在合并音频...", 95)
        if len(audio_tensors) > 1:
            silence_duration = 0.3
            silence = torch.zeros(1, int(silence_duration * self.model.sampling_rate))
            merged_audio = audio_tensors[0]
            for tensor in audio_tensors[1:]:
                merged_audio = torch.cat([merged_audio, silence, tensor], dim=1)
        else:
            merged_audio = audio_tensors[0]
        
        elapsed = time.time() - start_time
        
        # 保存音频
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torchaudio.save(output_path, merged_audio, self.model.sampling_rate)
        
        if metadata:
            self._write_metadata(output_path, metadata)
        
        duration = merged_audio.shape[-1] / self.model.sampling_rate
        rtf = elapsed / duration if duration > 0 else 0
        self._report_progress(f"[本地] 转换完成: {duration:.1f}s 音频, 耗时 {elapsed:.1f}s (RTF: {rtf:.2f})", 100)
        
        return {
            "audio_path": output_path,
            "duration": duration,
            "sample_rate": self.model.sampling_rate,
            "engine": "local",
        }

    def _write_metadata(self, file_path: str, metadata: Dict[str, Any]):
        try:
            audio = MutagenFile(file_path)
            if audio is None:
                return

            if not audio.tags:
                audio.add_tags()

            if "title" in metadata:
                audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
            if "artist" in metadata:
                audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
            if "album" in metadata:
                audio.tags.add(TALB(encoding=3, text=metadata["album"]))
            if "genre" in metadata:
                audio.tags.add(TCON(encoding=3, text=metadata["genre"]))
            if "track_number" in metadata and "total_tracks" in metadata:
                track = f"{metadata['track_number']}/{metadata['total_tracks']}"
                audio.tags.add(TRCK(encoding=3, text=track))

            audio.save()
        except Exception as e:
            logger.warning(f"Failed to write metadata: {e}")
