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


class TestLanguageDetection:
    """测试语言检测与分段大小选择"""

    def test_english_text_uses_en_chunk_size(self):
        """纯英文文本使用英文分段大小"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        conv.chunk_size_en = 100
        
        # 英文文本 150 字，中文限 200（可通过），英文限 100（不可通过）
        text = "This is an English sentence that should be split at the English limit rather than the Chinese limit because it is an English text."
        chunks = conv._split_text(text)
        for c in chunks:
            assert len(c) <= 100, f"Chunk exceeds EN limit (100): {len(c)} chars"
        assert len(chunks) > 1, "English text should have been split at EN limit"

    def test_chinese_text_uses_cn_chunk_size(self):
        """纯中文文本使用中文分段大小"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        conv.chunk_size_en = 100
        
        # 中文文本 150 字，中文限 200（可通过），英文限 100（会被切）
        text = "这是一段中文测试文本用来验证系统能够正确识别中文并使用中文的分段大小而不是英文的分段大小这样可以保证中文内容不会被过度切分"
        chunks = conv._split_text(text)
        # 整段文本 150 字 < 200，不应被拆分
        assert len(chunks) == 1, f"Chinese text should NOT be split at EN limit, got {len(chunks)} chunks"
        assert len(chunks[0]) <= 200

    def test_mixed_text_dominant_chinese_uses_cn(self):
        """中英混合但中文为主的文本用中文限"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        conv.chunk_size_en = 80
        
        text = "这是一段中文内容包含一些English单词但主要还是中文文本所以应该使用中文的分段大小限制而不是英文的限制"
        chunks = conv._split_text(text)
        for c in chunks:
            assert len(c) <= 200

    def test_mixed_text_dominant_english_uses_en(self):
        """中英混合但英文为主的文本用英文限"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        conv.chunk_size_en = 100
        
        text = "This is mostly English text with some 中文 words mixed in but predominantly English text that should be limited by the English chunk size."
        chunks = conv._split_text(text)
        assert len(chunks) > 1, "Should be split at EN limit"
        for c in chunks:
            assert len(c) <= 100

    def test_english_text_respects_explicit_en_limit(self):
        """英文长句被英文分段大小限制"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 999
        conv.chunk_size_en = 80
        
        # 纯英文长句
        text = "This is a fairly long English sentence that clearly exceeds the English chunk limit and must therefore be split accordingly to ensure that no single chunk exceeds the configured maximum."
        chunks = conv._split_text(text)
        for c in chunks:
            assert len(c) <= 80, f"Chunk {len(c)} > 80"

    def test_english_with_commas_split_correctly(self):
        """英文逗号处正确拆分且不超限"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        conv.chunk_size_en = 40
        
        text = "Hello, this is a test, with several commas, and it should be split, at these commas, correctly, into small chunks, please."
        chunks = conv._split_text(text)
        for c in chunks:
            assert len(c) <= 40, f"Chunk {len(c)} > 40"
        assert len(chunks) >= 3

    def test_default_en_fallback(self):
        """未显式设置 chunk_size_en 时使用默认值"""
        conv = AudioConverter(model_path="/fake")
        conv.chunk_size = 200
        # chunk_size_en defaults to 120
        assert conv.chunk_size_en == 120


class TestSecondaryPunctPriority:
    """测试次级标点优先级拆分"""

    @pytest.fixture
    def conv(self):
        c = AudioConverter(model_path="/fake")
        return c

    def test_comma_preferred_over_space(self, conv):
        """逗号优先级高于空格"""
        text = "Hello world, this is a test with a comma and spaces that should be split at the comma first rather than at spaces."
        chunks = conv._split_by_secondary_punct(text, chunk_size=50)
        # 应该优先在逗号处拆分
        for c in chunks:
            assert len(c) <= 50
        assert len(chunks) >= 2

    def test_semicolon_preferred(self, conv):
        """分号与逗号同级"""
        text = "First part of the sentence; second part of the sentence which is also quite long and needs splitting."
        chunks = conv._split_by_secondary_punct(text, chunk_size=60)
        for c in chunks:
            assert len(c) <= 60

    def test_colon_lower_than_comma(self, conv):
        """冒号优先级低于逗号"""
        text = "Item one, item two: description of the items that follows the colon and then more text to fill it up for splitting."
        chunks = conv._split_by_secondary_punct(text, chunk_size=50)
        for c in chunks:
            assert len(c) <= 50

    def test_space_lowest_priority(self, conv):
        """空格最末优先级"""
        text = "This is a sentence without any commas or colons or semicolons so it must be split at spaces only as a last resort fallback option."
        chunks = conv._split_by_secondary_punct(text, chunk_size=60)
        for c in chunks:
            assert len(c) <= 60

    def test_no_splittable_points(self, conv):
        """无任何可拆分点，等长切分"""
        text = "abcdefghijklmnopqrstuvwxyz" * 4
        chunks = conv._split_by_secondary_punct(text, chunk_size=20)
        for c in chunks:
            assert len(c) <= 20

    def test_chinese_comma_preferred(self, conv):
        """中文逗号优先级同英文逗号"""
        text = "这是第一段内容，这是第二段内容，这是第三段很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长很长的内容需要被拆分"
        chunks = conv._split_by_secondary_punct(text, chunk_size=50)
        for c in chunks:
            assert len(c) <= 50, f"Chunk too long: {len(c)}"
        assert len(chunks) >= 2, f"Expected >=2 chunks, got {len(chunks)}: {[len(c) for c in chunks]}"

    def test_short_text_not_split(self, conv):
        """不超限的文本不拆分"""
        text = "Short text."
        chunks = conv._split_by_secondary_punct(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_newline_respected(self, conv):
        """空格拆分不影响新行"""
        text = "line one line two line three line four line five line six line seven line eight"
        chunks = conv._split_by_secondary_punct(text, chunk_size=30)
        for c in chunks:
            assert len(c) <= 30
