"""娜娜 EPUB 解析测试：章节拆分 + 注解内联"""

import os
import re
import pytest
from app.services.ebook_parser import EpubParser, inline_annotations

TEST_EPUB = os.path.join(os.path.dirname(__file__), "data", "nana.epub")


class TestNanaChapterSplitting:
    """测试《娜娜》EPUB 的章节拆分"""

    @pytest.fixture
    def parsed(self):
        parser = EpubParser(TEST_EPUB)
        return parser.parse()

    def test_total_chapters(self, parsed):
        """应拆分出 14 章"""
        assert len(parsed["chapters"]) == 14

    def test_chapter_titles(self, parsed):
        """章节标题应为中文数字 一 到 十四"""
        expected_titles = ["一", "二", "三", "四", "五", "六", "七",
                           "八", "九", "十", "十一", "十二", "十三", "十四"]
        actual_titles = [ch["title"] for ch in parsed["chapters"]]
        assert actual_titles == expected_titles

    def test_chapter_content_not_empty(self, parsed):
        """每章内容不少于 1000 字"""
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 1000, f"Ch{ch['chapter_number']} too short"

    def test_first_chapter_starts_with_correct_text(self, parsed):
        """第一章应以"晚上九点钟"开头"""
        ch1 = parsed["chapters"][0]
        assert "晚上九点钟" in ch1["text_content"][:500]

    def test_metadata(self, parsed):
        """应正确提取书目元数据"""
        assert "娜娜" in parsed["title"]
        assert "左拉" in parsed["author"] or "爱弥尔" in parsed["author"]
        assert parsed["format"] == "epub"


class TestAnnotationInlining:
    """测试圆圈数字注解内联功能"""

    def test_function_returns_unchanged_if_no_annotations(self):
        """无注解文本原样返回"""
        text = "这是一段普通文本，没有任何注解。"
        result = inline_annotations(text)
        assert result == text

    def test_simple_inline(self):
        """单个①注解被内联"""
        text = """正文内容奥林匹斯山①，继续正文。

①古希腊神话中提及的一高峰。"""
        result = inline_annotations(text)
        assert "①" not in result
        assert "(注: 古希腊神话中提及的一高峰。)" in result
        assert "奥林匹斯山(注: 古希腊神话中提及的一高峰。)，" in result

    def test_multiple_sequential(self):
        """多个①②③顺序注解被正确内联"""
        text = """奥林匹斯山①，朱庇特②，司酒童③。

①古希腊高峰。
②罗马天神。
③希腊美少年。"""
        result = inline_annotations(text)
        assert "①" not in result and "②" not in result and "③" not in result
        assert "奥林匹斯山(注: 古希腊高峰。)" in result
        assert "朱庇特(注: 罗马天神。)" in result
        assert "司酒童(注: 希腊美少年。)" in result

    def test_annotations_removed_from_text(self):
        """注解正文行从正文中移除"""
        text = """正文①。

①注解内容。"""
        result = inline_annotations(text)
        assert "注解内容" in result  # 在内联中
        assert "(注: 注解内容。)" in result
        # 注解行本身不应保留为独立行
        lines = result.split("\n")
        for line in lines:
            if line.strip().startswith("①"):
                pytest.fail(f"Annotation line not removed: {line}")

    def test_no_circled_numbers_remain_in_body(self, parsed_nana):
        """《娜娜》正文中不应残留任何圆圈数字"""
        for ch in parsed_nana["chapters"]:
            remaining = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩]', ch["text_content"])
            assert len(remaining) == 0, f"Ch{ch['chapter_number']} has {remaining}"

    def test_annotations_are_inlined_in_nana(self, parsed_nana):
        """《娜娜》第1章应有7处注解内联"""
        ch1 = parsed_nana["chapters"][0]
        count = ch1["text_content"].count("(注:")
        assert count == 7, f"Expected 7 annotations inlined, got {count}"

    def test_annotation_content_correct(self, parsed_nana):
        """验证具体注解内容被正确内联"""
        ch1 = parsed_nana["chapters"][0]
        expected_annotations = [
            "古希腊神话中提及的一高峰",
            "罗马神话中的天神",
            "希腊神话中达耳达尼亚",
            "战神玛尔斯",
            "火神伏耳甘",
            "康康舞",
            "加洛普舞曲",
        ]
        for expected in expected_annotations:
            assert f"(注: " in ch1["text_content"]
            assert expected in ch1["text_content"], f"Annotation '{expected}' not found inlined"


@pytest.fixture
def parsed_nana():
    parser = EpubParser(TEST_EPUB)
    return parser.parse()
