import os
import logging
import torch
import torchaudio
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK

logger = logging.getLogger(__name__)


class AudioConverter:
    def __init__(self, model_path: str, device: str = "auto", precision: str = "float16",
                 asr_model_path: str = "openai/whisper-large-v3-turbo"):
        self.model_path = model_path
        self.device = self._get_device(device)
        self.precision = precision
        self.asr_model_path = asr_model_path
        self.model = None
        self.progress_callback: Optional[Callable] = None
        self.chunk_size = 200  # 每段文本的最大字符数

    def set_progress_callback(self, callback: Callable):
        self.progress_callback = callback

    def _report_progress(self, message: str, progress: float = None):
        if self.progress_callback:
            self.progress_callback(message, progress)
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

    def _split_text(self, text: str) -> List[str]:
        """将长文本按标点符号分段"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        # 按句子分隔符分割
        sentences = re.split(r'([。！？；\n])', text)

        current_chunk = ""
        for i, part in enumerate(sentences):
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 合并过短的段落
        merged_chunks = []
        temp = ""
        for chunk in chunks:
            if len(temp) + len(chunk) <= self.chunk_size:
                temp += chunk
            else:
                if temp:
                    merged_chunks.append(temp)
                temp = chunk
        if temp:
            merged_chunks.append(temp)

        return merged_chunks if merged_chunks else [text]

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
        return audios[0]

    def convert_chapter(
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.load_model()

        # 分段处理长文本
        chunks = self._split_text(text)
        total_chunks = len(chunks)

        self._report_progress(f"文本分为 {total_chunks} 段，共 {len(text)} 字符", 0)

        # 创建调试输出目录
        debug_dir = os.path.join(os.path.dirname(output_path), "debug", Path(output_path).stem)
        os.makedirs(debug_dir, exist_ok=True)

        start_time = time.time()
        audio_tensors = []

        for i, chunk in enumerate(chunks):
            chunk_preview = chunk[:30] + "..." if len(chunk) > 30 else chunk
            progress = (i / total_chunks) * 100
            self._report_progress(f"转换第 {i+1}/{total_chunks} 段: {chunk_preview}", progress)

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

            # 保存调试文件：文本和音频
            chunk_base = f"{i+1:03d}"
            with open(os.path.join(debug_dir, f"{chunk_base}.txt"), "w", encoding="utf-8") as f:
                f.write(chunk)
            torchaudio.save(
                os.path.join(debug_dir, f"{chunk_base}.wav"),
                audio_tensor,
                self.model.sampling_rate,
            )

            progress = ((i + 1) / total_chunks) * 100
            self._report_progress(f"第 {i+1}/{total_chunks} 段完成 ({chunk_elapsed:.1f}s)", progress)

        # 合并音频
        self._report_progress("正在合并音频...", 95)
        if len(audio_tensors) > 1:
            # 添加短暂静音作为段落间隔
            silence_duration = 0.3  # 0.3秒
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
        self._report_progress(f"转换完成: {duration:.1f}s 音频, 耗时 {elapsed:.1f}s (RTF: {rtf:.2f})", 100)

        return {
            "audio_path": output_path,
            "duration": duration,
            "sample_rate": self.model.sampling_rate,
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
