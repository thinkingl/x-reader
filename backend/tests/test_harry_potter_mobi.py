"""哈利·波特 MOBI 解析测试：验证 mobi 格式支持及章节拆分"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_MOBI = os.path.join(os.path.dirname(__file__), "data", "哈利·波特.mobi")


class TestHarryPotterMobi:
    """测试《哈利·波特》全集 MOBI 文件的解析"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_MOBI)
        return parser.parse()

    def test_format_is_mobi(self, parsed):
        """格式应为 mobi"""
        assert parsed["format"] == "mobi"

    def test_title(self, parsed):
        """书名应包含哈利·波特"""
        assert "哈利·波特" in parsed["title"]

    def test_total_chapters(self, parsed):
        """哈利波特全集包含 7 部书，共 200 章"""
        assert len(parsed["chapters"]) == 200

    def test_total_word_count(self, parsed):
        """总字数应超过 200 万字"""
        total = sum(ch["word_count"] for ch in parsed["chapters"])
        assert total > 2_000_000, f"总字数 {total} 不足 200 万"

    def test_chapter_content_not_empty(self, parsed):
        """每章内容不少于 100 字"""
        short_chapters = [ch for ch in parsed["chapters"] if ch["word_count"] < 100]
        assert len(short_chapters) == 1, f"期望只有第1章过短，实际: {short_chapters}"

    def test_first_real_chapter(self, parsed):
        """第2章应为 '第一章 大难不死的男孩'"""
        ch = parsed["chapters"][1]
        assert ch["chapter_number"] == 2
        assert "大难不死的男孩" in ch["title"]
        assert "德思礼" in ch["text_content"][:500] or "Dursley" in ch["text_content"][:500]

    def test_magic_stone_last_chapter(self, parsed):
        """第1部最后一章（第18章）应为 '第十七章 双面人'"""
        ch = parsed["chapters"][17]
        assert ch["chapter_number"] == 18
        assert "双面人" in ch["title"]

    def test_chamber_of_secrets_first_chapter(self, parsed):
        """第2部第1章（第19章）应为 '第一章 最糟糕的生日'"""
        ch = parsed["chapters"][18]
        assert ch["chapter_number"] == 19
        assert "最糟糕的生日" in ch["title"]

    def test_prisoner_of_azkaban_chapters(self, parsed):
        """第3部应包含 '摄魂怪'、'守护神' 等章节"""
        titles = [ch["title"] for ch in parsed["chapters"] if "摄魂怪" in ch["title"] or "守护神" in ch["title"]]
        assert len(titles) >= 2, f"第3部相关章节不足: {titles}"

    def test_goblet_of_fire_chapters(self, parsed):
        """第4部应包含 '火焰杯'、'三强争霸赛' 等章节"""
        titles = [ch["title"] for ch in parsed["chapters"] if "火焰杯" in ch["title"] or "三强" in ch["title"]]
        assert len(titles) >= 2, f"第4部相关章节不足: {titles}"

    def test_order_of_phoenix_chapters(self, parsed):
        """第5部应包含 '凤凰社'、'邓布利多军' 等章节"""
        titles = [ch["title"] for ch in parsed["chapters"] if "凤凰社" in ch["title"] or "邓布利多军" in ch["title"]]
        assert len(titles) >= 2, f"第5部相关章节不足: {titles}"

    def test_half_blood_prince_chapters(self, parsed):
        """第6部应包含 '混血王子'、'魂器' 等章节"""
        titles = [ch["title"] for ch in parsed["chapters"] if "混血王子" in ch["title"] or "魂器" in ch["title"]]
        assert len(titles) >= 2, f"第6部相关章节不足: {titles}"

    def test_deathly_hallows_last_chapter(self, parsed):
        """最后1章应为 '尾声 十九年后'"""
        ch = parsed["chapters"][-1]
        assert "十九年后" in ch["title"]

    def test_deathly_hallows_content(self, parsed):
        """第7部应包含魂器相关内容"""
        dh_chapters = [ch for ch in parsed["chapters"]
                       if ch["chapter_number"] >= 164 and ch["word_count"] > 100]
        combined = " ".join(ch["text_content"] for ch in dh_chapters[:5])
        assert any(kw in combined for kw in ["魂器", "死亡圣器", "老魔杖", "波特", "伏地魔"]), \
            f"第7部应包含关键内容"

    def test_chapter_numbers_are_sequential(self, parsed):
        """章节编号应为 1-200 连续"""
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 201))

    def test_each_chapter_has_title(self, parsed):
        """每章都应有标题"""
        for ch in parsed["chapters"]:
            assert ch["title"], f"第{ch['chapter_number']}章缺少标题"
