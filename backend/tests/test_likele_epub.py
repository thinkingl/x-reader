"""李可乐抗拆记 EPUB parsing test: single-chapter book with no chapter markers"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_EPUB = os.path.join(os.path.dirname(__file__), "data", "likele.epub")


class TestLikeleEpub:
    """Test parsing of a single-chapter EPUB with no internal chapter structure"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_EPUB)
        return parser.parse()

    def test_format_is_epub(self, parsed):
        assert parsed["format"] == "epub"

    def test_title(self, parsed):
        assert "李可乐抗拆记" in parsed["title"]

    def test_author(self, parsed):
        assert parsed["author"] == "李承鹏"

    def test_no_chapter_structure(self, parsed):
        """Book has no chapter markers - entire content is one chapter"""
        # Should have catalog (short) + 1 main chapter
        content_chapters = [ch for ch in parsed["chapters"] if ch["word_count"] > 100]
        assert len(content_chapters) == 1

    def test_main_chapter_word_count(self, parsed):
        """Main chapter should have substantial content"""
        main = [ch for ch in parsed["chapters"] if ch["word_count"] > 1000]
        assert len(main) == 1
        assert main[0]["word_count"] > 100000

    def test_content_starts_correctly(self, parsed):
        main = [ch for ch in parsed["chapters"] if ch["word_count"] > 1000][0]
        assert "违章建筑" in main["text_content"][:200]
