"""中国历代政治得失 MOBI parsing test: verify 第X讲 chapter detection"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_MOBI = os.path.join(os.path.dirname(__file__), "data", "politics.mobi")


class TestPoliticsMobi:
    """Test parsing of 中国历代政治得失 (MOBI, 第X讲 chapter headers)"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_MOBI)
        return parser.parse()

    def test_format_is_mobi(self, parsed):
        assert parsed["format"] == "mobi"

    def test_total_chapters(self, parsed):
        """Should have 7 chapters: 序 + 前言 + 5 lectures"""
        assert len(parsed["chapters"]) == 7

    def test_chapter_titles(self, parsed):
        titles = [ch["title"] for ch in parsed["chapters"]]
        assert titles == ["序", "前言", "第一讲·汉代", "第二讲·唐代", "第三讲·宋代", "第四讲·明代", "第五讲·清代"]

    def test_no_toc_leftover(self, parsed):
        """First chapter should not be a TOC leftover (duplicate title with short content)"""
        titles = [ch["title"] for ch in parsed["chapters"]]
        assert len(titles) == len(set(titles)), "Duplicate chapter titles found"

    def test_chapter_content_not_empty(self, parsed):
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 500, f"Chapter '{ch['title']}' only has {ch['word_count']} chars"

    def test_chapter_numbers_sequential(self, parsed):
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 8))

    def test_content_starts_correctly(self, parsed):
        """序 chapter should start with the correct text"""
        preface = parsed["chapters"][0]
        assert preface["title"] == "序"
        assert "政治制度" in preface["text_content"][:200]
