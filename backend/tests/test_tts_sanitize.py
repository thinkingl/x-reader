"""EPUB TTS 文本清理 + 世界尽头电子书解析测试"""

import os
import re
import pytest
from app.services.ebook_parser import EpubParser, sanitize_text, inline_annotations

NANA_EPUB = os.path.join(os.path.dirname(__file__), "data", "nana.epub")
WORLDS_END_EPUB = os.path.join(os.path.dirname(__file__), "data", "worlds_end.epub")


class TestSanitizeText:
    """测试 sanitize_text 函数"""

    def test_remove_book_title_marks(self):
        """《》 替换为空格"""
        result = sanitize_text("《世界尽头与冷酷仙境》村上春树")
        assert "《" not in result
        assert "》" not in result
        assert "世界尽头与冷酷仙境" in result

    def test_remove_corner_brackets(self):
        """「」『』 替换为空格"""
        result = sanitize_text("「你好」『世界』")
        assert "「" not in result and "」" not in result
        assert "『" not in result and "』" not in result

    def test_remove_lenticular_brackets(self):
        """【】 替换为空格"""
        result = sanitize_text("【注释】正文")
        assert "【" not in result and "】" not in result

    def test_remove_tortoise_brackets(self):
        """〖〗 替换为空格"""
        result = sanitize_text("〖说明〗内容")
        assert "〖" not in result and "〗" not in result

    def test_remove_angle_brackets(self):
        """〈〉 替换为空格"""
        result = sanitize_text("〈引文〉正文")
        assert "〈" not in result and "〉" not in result

    def test_collapse_multiple_blank_lines(self):
        """多余空行合并为单个"""
        text = "段落一\n\n\n\n段落二\n\n\n\n\n段落三"
        result = sanitize_text(text)
        assert "\n\n\n" not in result
        count = result.count("\n\n")
        assert count == 2, f"expected 2 double-newlines, got {count}"

    def test_strip_whitespace(self):
        """去除首尾空白"""
        result = sanitize_text("\n\n  正文内容  \n\n")
        assert result.startswith("正文")
        assert result.endswith("内容")

    def test_preserve_normal_text(self):
        """正常文本和标点不变"""
        text = '他说："你好。"她回答：「嗯。」这是一个——测试……吧？'
        result = sanitize_text(text)
        assert "他说" in result
        assert "你好" in result
        assert "测试" in result

    def test_all_symbols_removed_from_nana(self, parsed_nana):
        """《娜娜》中不应残留任何 TTS 无意义符号"""
        bad_chars = r'[《》〈〉「」『』【】〖〗]'
        for ch in parsed_nana["chapters"]:
            found = re.findall(bad_chars, ch["text_content"])
            assert len(found) == 0, (
                f"Ch{ch['chapter_number']} contains: {found[:10]}"
            )

    def test_all_symbols_removed_from_worlds_end(self, parsed_worlds_end):
        """《世界尽头》中不应残留任何 TTS 无意义符号"""
        bad_chars = r'[《》〈〉「」『』【】〖〗]'
        for ch in parsed_worlds_end["chapters"]:
            found = re.findall(bad_chars, ch["text_content"])
            assert len(found) == 0, (
                f"Ch{ch['chapter_number']} contains: {found[:10]}"
            )


class TestWorldsEnd:
    """测试《世界尽头与冷酷仙境》EPUB 解析"""

    @pytest.fixture
    def parsed(self):
        parser = EpubParser(WORLDS_END_EPUB)
        return parser.parse()

    def test_total_chapters(self, parsed):
        assert len(parsed["chapters"]) == 44

    def test_metadata(self, parsed):
        assert "世界尽头" in parsed["title"]
        assert "冷酷仙境" in parsed["title"]
        assert "村上春树" in parsed["author"]
        assert parsed["format"] == "epub"

    def test_chapter_titles_not_generic(self, parsed):
        """章节标题不应是通用的"正文"或"Chapter X"格式"""
        for ch in parsed["chapters"]:
            title = ch["title"]
            assert title != "正文", f"Ch{ch['chapter_number']} has generic title"
            if ch["chapter_number"] >= 5:  # 前4章是元数据页
                assert "Chapter" not in title, f"Ch{ch['chapter_number']}: {title}"

    def test_chapter_title_format(self, parsed):
        """主体章节标题应为"数字.xxx--xxx"格式"""
        for ch in parsed["chapters"]:
            if ch["chapter_number"] >= 5:
                title = ch["title"]
                assert re.match(r'\d+\.', title), (
                    f"Ch{ch['chapter_number']} title not numbered: {title}"
                )

    def test_chapter_content_not_empty(self, parsed):
        """内容章节字数不少于 500（排除元数据页 Ch1-4）"""
        for ch in parsed["chapters"]:
            if ch["chapter_number"] >= 5:
                assert ch["word_count"] > 500, (
                    f"Ch{ch['chapter_number']} too short ({ch['word_count']})"
                )

    def test_first_story_chapter(self, parsed):
        """第一个故事章节内容正确"""
        ch5 = parsed["chapters"][4]  # Ch5 = first real chapter
        assert "酷仙境" in ch5["title"] or "冷酷仙境" in ch5["title"]
        assert "电梯" in ch5["title"]
        assert "电梯" in ch5["text_content"][:200]
        assert "缓慢" in ch5["text_content"][:500]

    def test_alternating_worlds(self, parsed):
        """章节应交替：冷酷仙境 / 世界尽头"""
        odd_cold = 0  # 奇数序号为"冷酷仙境"
        even_world = 0  # 偶数序号为"世界尽头"
        for ch in parsed["chapters"]:
            if ch["chapter_number"] < 5:
                continue
            adjusted = ch["chapter_number"] - 4
            if adjusted % 2 == 1 and "冷酷" in ch["title"]:
                odd_cold += 1
            if adjusted % 2 == 0 and "世界" in ch["title"]:
                even_world += 1
        assert odd_cold >= 18, f"Expected ~20 odd=cold, got {odd_cold}"
        assert even_world >= 18, f"Expected ~20 even=world, got {even_world}"


class TestCombinedProcessing:
    """测试 sanitize + inline_annotations 组合"""

    def test_sanitize_and_annotate_together(self):
        text = "【题记】奥林匹斯山①，继续。\n\n①注解内容。"
        result = inline_annotations(sanitize_text(text))
        assert "【" not in result and "】" not in result
        assert "①" not in result
        assert "(注: 注解内容。)" in result

    def test_order_invariant(self):
        """sanitize 和 annotate 顺序不影响最终结果"""
        text = "《书名》正文①。\n①注解。"
        r1 = sanitize_text(inline_annotations(text))
        r2 = inline_annotations(sanitize_text(text))
        assert r1 == r2


@pytest.fixture
def parsed_nana():
    return EpubParser(NANA_EPUB).parse()


@pytest.fixture
def parsed_worlds_end():
    return EpubParser(WORLDS_END_EPUB).parse()
