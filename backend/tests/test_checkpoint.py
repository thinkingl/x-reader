"""Checkpoint 断点续传测试"""

import os
import tempfile
import pytest

os.environ["CHECKPOINT_DIR"] = tempfile.mkdtemp(prefix="cp_test_")

from app.services.checkpoint import (
    create as cp_create,
    save_chunk,
    get_pending_count,
    get_completed_count,
    iter_completed,
    delete as cp_delete,
    exists as cp_exists,
    cleanup_orphans,
)

# 必须在 conftest mock 之前获取真实类
from app.services.audio_converter import AudioConverter as _RealConv

_next_id = 90000


def _new_task_id():
    global _next_id
    _next_id += 1
    cp_delete(_next_id)
    return _next_id


class TestCheckpointDB:
    """测试 checkpoint SQLite 基本操作"""

    def test_create_and_exist(self):
        tid = _new_task_id()
        assert cp_create(tid, ["a", "b", "c"])
        assert cp_exists(tid)

    def test_pending_count_all_null(self):
        tid = _new_task_id()
        cp_create(tid, ["a", "b", "c"])
        assert get_pending_count(tid) == 3
        assert get_completed_count(tid) == 0

    def test_save_and_count(self):
        tid = _new_task_id()
        cp_create(tid, ["a", "b", "c"])
        save_chunk(tid, 0, b"audio_0")
        save_chunk(tid, 1, b"audio_1")
        assert get_completed_count(tid) == 2
        assert get_pending_count(tid) == 1

    def test_iter_completed(self):
        tid = _new_task_id()
        cp_create(tid, ["a", "b", "c"])
        save_chunk(tid, 0, b"data_0")
        save_chunk(tid, 2, b"data_2")
        results = list(iter_completed(tid))
        assert len(results) == 2
        assert results[0] == (0, b"data_0")
        assert results[1] == (2, b"data_2")

    def test_delete(self):
        tid = _new_task_id()
        cp_create(tid, ["a"])
        assert cp_exists(tid)
        cp_delete(tid)
        assert not cp_exists(tid)

    def test_pending_count_negative_if_not_exists(self):
        assert get_pending_count(_new_task_id()) == -1

    def test_recreate_preserves_existing(self):
        tid = _new_task_id()
        cp_create(tid, ["a", "b", "c"])
        save_chunk(tid, 0, b"existing")
        cp_create(tid, ["a", "b", "c"])  # 模拟重启
        results = list(iter_completed(tid))
        assert len(results) == 1
        assert results[0] == (0, b"existing")
        assert get_pending_count(tid) == 2

    def test_cleanup_orphans(self):
        tid = _new_task_id()
        cp_create(tid, ["a"])
        save_chunk(tid, 0, b"data")
        cleanup_orphans(set())  # tid 不在活跃列表
        assert not cp_exists(tid)

    def test_cleanup_keeps_active(self):
        tid = _new_task_id()
        cp_create(tid, ["a"])
        save_chunk(tid, 0, b"data")
        cleanup_orphans({tid})  # tid 在活跃列表
        assert cp_exists(tid)


class TestCheckpointConverter:
    """测试 convert_chapter_with_checkpoint"""

    def _make_mock_model(self):
        import torch

        class MockModel:
            sampling_rate = 24000

        return MockModel()

    def _mock_generate(self, **kwargs):
        import torch
        return torch.zeros(1, 8000)

    def test_local_conversion(self):
        conv = self._make_conv()
        conv.model = self._make_mock_model()
        conv.device = "cpu"
        conv._generate_single_chunk = self._mock_generate

        tid = _new_task_id()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "test.wav")
            result = conv.convert_chapter_with_checkpoint(
                task_id=tid,
                text="这是一段测试文本。这是第二句话。这是第三句。",
                output_path=output,
                preset={"engine": "local_omnivoice", "voice_mode": "auto"},
            )
            files = os.listdir(tmpdir)
            assert os.path.exists(output), f"No output file. Dir contents: {files}, result={result}"
            assert result["duration"] > 0
            assert not cp_exists(tid)

    def test_online_conversion(self):
        conv = self._make_conv()

        class MockMiMo:
            def synthesize(self, **kwargs):
                import io, torchaudio, torch
                buf = io.BytesIO()
                torchaudio.save(buf, torch.zeros(1, 4000), 24000, format="wav")
                return buf.getvalue()

        conv.mimo_client = MockMiMo()
        tid = _new_task_id()

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "test2.wav")
            result = conv.convert_chapter_with_checkpoint(
                task_id=tid,
                text="Hello world. This is a test. More text.",
                output_path=output,
                preset={"engine": "online_mimo", "voice_mode": "auto", "voice_id": "test"},
            )
            assert os.path.exists(output)
            assert result["duration"] > 0
            assert not cp_exists(tid)

    def _make_conv(self):
        conv = _RealConv.__new__(_RealConv)
        conv._report_progress = lambda msg, p=None, ctx=None: None
        conv.progress_callback = None
        conv.chunk_size = 200
        conv.chunk_size_en = 200
        conv._local = type('obj', (), {})()
        conv._local.progress_callback = None
        return conv

    def test_resume_from_checkpoint(self):
        conv = self._make_conv()
        conv.model = self._make_mock_model()
        conv.device = "cpu"
        conv._generate_single_chunk = self._mock_generate

        import io, torch, torchaudio
        tid = _new_task_id()
        text = "这是第一段。这是第二段。这是第三段。这是第四段。这是第五段。"
        chunks = conv._split_text(text, chunk_size=8)

        cp_create(tid, chunks)
        # 用有效 WAV 代替假数据
        for idx in range(2):
            buf = io.BytesIO()
            torchaudio.save(buf, torch.zeros(1, 4000), 24000, format="wav")
            save_chunk(tid, idx, buf.getvalue())

        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "resume.wav")
            result = conv.convert_chapter_with_checkpoint(
                task_id=tid, text=text, output_path=output,
                preset={"engine": "local_omnivoice", "voice_mode": "auto"},
            )
            assert os.path.exists(output)
            assert result["duration"] > 0
            assert not cp_exists(tid)

    def test_checkpoint_deleted_after_completion(self):
        conv = self._make_conv()
        conv.model = self._make_mock_model()
        conv.device = "cpu"
        conv._generate_single_chunk = self._mock_generate

        tid = _new_task_id()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "clean.wav")
            conv.convert_chapter_with_checkpoint(
                task_id=tid, text="短文本测试。", output_path=output,
            )
            assert not cp_exists(tid)
