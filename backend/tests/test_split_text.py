"""AudioConverter._split_text 分句测试 — 中文+英文混排"""

import pytest
from unittest.mock import MagicMock
from app.services.audio_converter import AudioConverter


@pytest.fixture
def converter():
    conv = AudioConverter(model_path="/fake")
    conv.chunk_size = 200
    return conv


class TestSplitTextChinese:
    def test_short_text_no_split(self, converter):
        chunks = converter._split_text("短文本")
        assert len(chunks) == 1
        assert chunks[0] == "短文本"

    def test_split_on_period(self, converter):
        """按。分隔"""
        text = "第一句。第二句。第三句。"
        chunks = converter._split_text(text, chunk_size=5)
        assert len(chunks) >= 2

    def test_split_on_question(self, converter):
        text = "你认识吗？不认识。"
        chunks = converter._split_text(text, chunk_size=5)
        assert len(chunks) >= 2

    def test_split_on_exclamation(self, converter):
        text = "太好了！真是好。"
        chunks = converter._split_text(text, chunk_size=5)
        assert len(chunks) >= 2

    def test_merge_short_chunks(self, converter):
        """短句合并不超过 chunk_size"""
        text = "第一句。第二句。第三句。第四句。第五句。第六句。"
        chunks = converter._split_text(text)
        for ch in chunks:
            assert len(ch) <= 200, f"Chunk too long: {len(ch)} chars"


class TestSplitTextEnglish:
    def test_split_on_dot(self, converter):
        """英文按句号分隔"""
        text = "Hello world. This is a test. More text here."
        chunks = converter._split_text(text, chunk_size=20)
        assert len(chunks) >= 2

    def test_split_on_exclamation_mark(self, converter):
        text = "Great! Amazing. Wonderful."
        chunks = converter._split_text(text, chunk_size=15)
        assert len(chunks) >= 2

    def test_split_on_question_mark(self, converter):
        text = "How are you? I am fine. Thank you."
        chunks = converter._split_text(text, chunk_size=20)
        assert len(chunks) >= 2

    def test_respects_chunk_size(self, converter):
        """每段不超过 chunk_size"""
        text = (
            "This is a sentence about testing. Another sentence here for verification. "
            "Yet another one that should be kept within limits. And a final sentence to check."
        )
        chunks = converter._split_text(text, chunk_size=120)
        for ch in chunks:
            assert len(ch) <= 120, f"Chunk too long: {len(ch)} chars: '{ch[:50]}...'"


class TestMixedLanguages:
    def test_chinese_and_english_mixed(self, converter):
        text = "Hello world. 中文内容。This is English. 继续中文。"
        chunks = converter._split_text(text, chunk_size=30)
        assert len(chunks) >= 2

    def test_english_with_newlines(self, converter):
        text = "Line one.\nLine two.\nLine three."
        chunks = converter._split_text(text, chunk_size=20)
        assert len(chunks) >= 2


class TestLongSentenceSecondarySplit:
    def test_very_long_sentence_splits(self, converter):
        """超长句子在次级标点处拆分"""
        # 一个超过 200 字的英文句子，中间有逗号
        text = "This is an extremely long sentence, it keeps going on and on, with many commas, and it should be split at those commas, because the sentence is way too long for a single chunk, and without splitting, it would exceed the limit, which is not acceptable for TTS."
        chunks = converter._split_text(text, chunk_size=200)
        for ch in chunks:
            assert len(ch) <= 200, f"Chunk too long: {len(ch)} chars"

    def test_long_chinese_no_punct_hard_split(self, converter):
        """无标点的超长中文也会被限制"""
        text = "这是一个非常长的句子没有任何标点符号完全无法被正确分割但系统应该尝试在合适的位置进行切分以保证每段不超过限制这是对系统健壮性的重要测试"
        chunks = converter._split_text(text, chunk_size=100)
        for ch in chunks:
            assert len(ch) <= 100, f"Chunk too long: {len(ch)} chars"

    def test_mixed_long_sentence(self, converter):
        """混合语言超长句子"""
        text = (
            "This is a very long mixed language sentence, 其中包含中文内容 and also "
            "English content, 并且逗号和分号之间, there are commas to split on; "
            "also semicolons should work; 最后还有冒号: the final part of this test."
        )
        chunks = converter._split_text(text, chunk_size=200)
        for ch in chunks:
            assert len(ch) <= 200, f"Chunk too long: {len(ch)} chars"


class TestEdgeCases:
    def test_empty_text(self, converter):
        chunks = converter._split_text("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_exact_boundary(self, converter):
        """恰好等于 chunk_size 的文本"""
        text = "A" * 200
        chunks = converter._split_text(text, chunk_size=200)
        assert len(chunks) == 1

    def test_one_char_over_boundary(self, converter):
        """超过 1 个字符且有次级标点"""
        text = "A" * 150 + ", " + "B" * 100
        chunks = converter._split_text(text, chunk_size=200)
        for ch in chunks:
            assert len(ch) <= 200

    def test_punctuation_only(self, converter):
        """纯标点文本"""
        text = "。！？.!?"
        chunks = converter._split_text(text, chunk_size=5)
        assert len(chunks) >= 1

    def test_secondary_split_preserves_content(self, converter):
        """次级拆分不丢失内容"""
        text = "Part1, Part2, Part3, Part4. End."
        chunks = converter._split_text(text, chunk_size=12)
        combined = "".join(chunks)
        # 所有字符都在（除了合并的空格差异）
        assert "Part1" in combined
        assert "Part4" in combined
        assert "End" in combined
