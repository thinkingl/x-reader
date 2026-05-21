"""My Brilliant Friend MOBI parsing test: verify -\\d- format chapter title support"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_MOBI = os.path.join(os.path.dirname(__file__), "data", "new_name_story.mobi")


class TestNewNameStoryMobi:
    """测试《新名字的故事》MOBI 文件解析（\d- 格式章节）"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_MOBI)
        return parser.parse()

    def test_format_is_mobi(self, parsed):
        assert parsed["format"] == "mobi"

    def test_title(self, parsed):
        assert parsed["title"] == "new_name_story"

    def test_total_chapters(self, parsed):
        """应有 127 章"""
        assert len(parsed["chapters"]) == 127

    def test_total_word_count(self, parsed):
        total = sum(ch["word_count"] for ch in parsed["chapters"])
        assert total > 250_000

    def test_first_two_chapters_are_metadata(self, parsed):
        """前 2 章为元数据（版权信息/人物表/目录等）"""
        titles = [ch["title"] for ch in parsed["chapters"][:2]]
        metadata_keywords = ["版权", "目录", "人物", "Chapter", "前言"]
        for t in titles:
            assert any(kw in t for kw in metadata_keywords), \
                f"前2章应为元数据，实际: {titles}"

    def test_chapter_titles_are_dash_pattern(self, parsed):
        """第3章起标题应为 -\d+- 格式（如 -1-, -2-）"""
        import re
        for ch in parsed["chapters"][2:]:
            assert re.match(r'^-\d{1,3}-$', ch["title"]), \
                f"第{ch['chapter_number']}章标题不符合 -\\d- 格式: '{ch['title']}'"

    def test_chapter_content_not_too_short(self, parsed):
        """每章内容不少于 500 字（跳过前 2 章元数据）"""
        for ch in parsed["chapters"][2:]:
            assert ch["word_count"] > 500, \
                f"第{ch['chapter_number']}章仅 {ch['word_count']} 字"

    def test_chapter_numbers_are_sequential(self, parsed):
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 128))

    def test_content_mentions_characters(self, parsed):
        """内容应包含主要角色名字"""
        all_text = " ".join(ch["text_content"][:200] for ch in parsed["chapters"][3:10])
        assert any(name in all_text for name in ["莉拉", "埃莱娜", "尼诺", "斯特凡诺"]), \
            f"应包含主要角色名，实际: {all_text[:200]}"

    def test_no_chapter_pattern_in_content(self, parsed):
        """章节标题不应出现在正文中间（跳过前15章可能包含的目录内容）"""
        import re
        for ch in parsed["chapters"][15:25]:
            lines = ch["text_content"].split("\n")
            for line in lines[1:6]:  # 跳过第一行（可能是章节标题本身）
                assert not re.match(r'^-\d{1,3}-$', line.strip()), \
                    f"第{ch['chapter_number']}章正文中包含章节标记"
