import os
import io
import sys
import time
import shutil
import psutil
import asyncio

import numpy as np
from funasr import AutoModel
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.utils import lang_tag_filter
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

MAX_RETRIES = 2
RETRY_DELAY = 1  # 重试延迟（秒）


# 捕获标准输出
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # 将捕获到的内容通过 logger 输出
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        
        # 内存检测，要求大于2G
        min_mem_bytes = 2 * 1024 * 1024 * 1024
        total_mem = psutil.virtual_memory().total
        if total_mem < min_mem_bytes:
            logger.bind(tag=TAG).error(f"可用内存不足2G，当前仅有 {total_mem / (1024*1024):.2f} MB，可能无法启动FunASR")
        
        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")  # 修正配置键名
        self.delete_audio_file = delete_audio_file

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="hf",
                # device="cuda:0",  # 启用GPU加速
            )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus", artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                if artifacts is None:
                    return "", None

                # 语音识别 - 使用线程池避免阻塞事件循环
                start_time = time.time()
                pcm_int16 = np.frombuffer(artifacts.pcm_bytes, dtype=np.int16)

                # 写成临时 WAV 让 FunASR 从文件读取（numpy 直传有版本兼容问题）
                import wave
                import tempfile
                _tmp_dir = self.output_dir or tempfile.gettempdir()
                os.makedirs(_tmp_dir, exist_ok=True)
                _wav_path = os.path.join(_tmp_dir, f"asr_{session_id[:8]}_{int(time.time()*1000)}.wav")
                try:
                    with wave.open(_wav_path, "wb") as w:
                        w.setnchannels(1)
                        w.setsampwidth(2)
                        w.setframerate(16000)
                        w.writeframes(artifacts.pcm_bytes)
                    _rms = float(np.sqrt(np.mean((pcm_int16.astype(np.float32)/32768.0) ** 2))) if pcm_int16.size else 0.0
                    _peak = float(np.max(np.abs(pcm_int16))/32768.0) if pcm_int16.size else 0.0
                    logger.bind(tag=TAG).info(
                        f"[PCM 诊断] samples={pcm_int16.size} duration={pcm_int16.size/16000:.2f}s "
                        f"rms={_rms:.4f} peak={_peak:.4f} wav={_wav_path}"
                    )
                except Exception as _e:
                    logger.bind(tag=TAG).warning(f"[PCM 诊断] 写 WAV 失败: {_e}")

                result = await asyncio.to_thread(
                    self.model.generate,
                    input=_wav_path,
                    cache={},
                    language="auto",
                    use_itn=True,
                    batch_size_s=60,
                )
                # 兼容 FunASR 多版本返回结构：[{"text":"..."}] / ["..."] / "..."
                raw_text = ""
                if isinstance(result, str):
                    raw_text = result
                elif isinstance(result, (list, tuple)) and result:
                    first = result[0]
                    if isinstance(first, dict):
                        raw_text = first.get("text", "") or first.get("content", "")
                    elif isinstance(first, str):
                        raw_text = first
                    else:
                        raw_text = str(first)
                if not raw_text:
                    logger.bind(tag=TAG).warning(
                        f"ASR 返回空，原始结构 type={type(result).__name__} sample={str(result)[:200]}"
                    )
                text = lang_tag_filter(raw_text)
                _content = text["content"] if isinstance(text, dict) else text
                logger.bind(tag=TAG).info(
                    f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {_content}"
                )

                return text, artifacts.file_path

            except OSError as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.bind(tag=TAG).error(
                        f"语音识别失败（已重试{retry_count}次）: {e}", exc_info=True
                    )
                    return "", None
                logger.bind(tag=TAG).warning(
                    f"语音识别失败，正在重试（{retry_count}/{MAX_RETRIES}）: {e}"
                )
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
                return "", None
