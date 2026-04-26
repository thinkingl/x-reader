import os
import json
import base64
import logging
import requests
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MiMoTTSClient:
    """小米 MiMo V2.5 TTS 在线 API 客户端"""
    
    BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
    
    MODEL_MAP = {
        "auto": "mimo-v2.5-tts",
        "design": "mimo-v2.5-tts-voicedesign",
        "clone": "mimo-v2.5-tts-voiceclone",
    }
    
    # 内置语音列表
    VOICES = {
        "mimo_default": "MiMo默认",
        "冰糖": "冰糖",
        "茉莉": "茉莉",
        "苏打": "苏打",
        "白桦": "白桦",
        "Mia": "Mia",
        "Chloe": "Chloe",
        "Milo": "Milo",
        "Dean": "Dean",
    }
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "Content-Type": "application/json",
        })
    
    def synthesize(
        self,
        text: str,
        voice_mode: str = "auto",
        voice_id: Optional[str] = None,
        instruct: Optional[str] = None,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        audio_format: str = "wav",
    ) -> bytes:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice_mode: 语音模式 (auto/design/clone)
            voice_id: 内置语音 ID (auto 模式)
            instruct: 语音设计描述 (design 模式)
            ref_audio_path: 参考音频路径 (clone 模式)
            ref_text: 参考音频文本 (clone 模式, 可选)
            audio_format: 输出音频格式 (wav/mp3)
        
        Returns:
            音频文件的字节数据
        """
        model = self.MODEL_MAP.get(voice_mode, self.MODEL_MAP["auto"])
        messages = self._build_messages(
            text=text,
            voice_mode=voice_mode,
            instruct=instruct,
            ref_text=ref_text,
        )
        
        audio_config = {"format": audio_format}
        
        # 设置语音
        if voice_mode == "auto":
            audio_config["voice"] = voice_id or "冰糖"
        elif voice_mode == "clone" and ref_audio_path:
            audio_config["voice"] = self._encode_audio(ref_audio_path)
        
        payload = {
            "model": model,
            "messages": messages,
            "audio": audio_config,
        }
        
        print(f"[MiMo API] model={model}, voice_mode={voice_mode}, text_len={len(text)}")
        print(f"[MiMo API] messages: {json.dumps(messages, ensure_ascii=False)}")
        logger.info(f"调用 MiMo API: model={model}, voice_mode={voice_mode}, text_len={len(text)}")
        logger.info(f"MiMo API 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=120,
        )
        
        if response.status_code != 200:
            error_msg = response.text[:500]
            logger.error(f"MiMo API 错误: {response.status_code} - {error_msg}")
            raise Exception(f"MiMo API 错误: {response.status_code} - {error_msg}")
        
        result = response.json()
        
        # 提取音频数据
        choices = result.get("choices", [])
        if not choices:
            raise Exception("MiMo API 返回空结果")
        
        message = choices[0].get("message", {})
        audio = message.get("audio", {})
        
        if not audio or not audio.get("data"):
            raise Exception("MiMo API 未返回音频数据")
        
        audio_bytes = base64.b64decode(audio["data"])
        logger.info(f"MiMo API 返回音频: {len(audio_bytes)} bytes")
        
        return audio_bytes
    
    def _build_messages(
        self,
        text: str,
        voice_mode: str,
        instruct: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """构建 API 请求的 messages"""
        messages = []
        
        if voice_mode == "design":
            # 语音设计模式：instruct 放在 user 消息中
            messages.append({
                "role": "user",
                "content": instruct or "一个自然清晰的声音",
            })
        elif voice_mode == "clone":
            # 语音克隆模式：user 消息可以为空或包含风格指令
            messages.append({
                "role": "user",
                "content": instruct or "",
            })
        else:
            # 内置语音模式：instruct 作为风格控制
            if instruct:
                messages.append({
                    "role": "user",
                    "content": instruct,
                })
            else:
                messages.append({
                    "role": "user",
                    "content": "自然地说",
                })
        
        # assistant 消息包含要合成的文本
        messages.append({
            "role": "assistant",
            "content": text,
        })
        
        return messages
    
    def _encode_audio(self, audio_path: str) -> str:
        """将音频文件编码为 base64 格式"""
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 确定 MIME 类型
        suffix = path.suffix.lower()
        mime_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
        }
        mime_type = mime_map.get(suffix, "audio/wav")
        
        # 读取并编码
        with open(path, "rb") as f:
            audio_bytes = f.read()
        
        base64_str = base64.b64encode(audio_bytes).decode("utf-8")
        
        # 检查大小限制 (10MB)
        if len(base64_str) > 10 * 1024 * 1024:
            raise ValueError("音频文件过大，base64 编码后不能超过 10MB")
        
        return f"data:{mime_type};base64,{base64_str}"
    
    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            audio = self.synthesize(
                text="你好",
                voice_mode="auto",
                voice_id="冰糖",
            )
            return len(audio) > 0
        except Exception as e:
            logger.error(f"MiMo API 连接测试失败: {e}")
            return False
