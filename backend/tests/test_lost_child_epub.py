"""失踪的孩子 EPUB parsing test: verify toc.ncx bookmark title extraction"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_EPUB = os.path.join(os.path.dirname(__file__), "data", "lost_child.epub")


class TestLostChildEpub:
    """Test parsing of 失踪的孩子 (EPUB, toc.ncx bookmark titles)"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_EPUB)
        return parser.parse()

    def test_format_is_epub(self, parsed):
        assert parsed["format"] == "epub"

    def test_total_chapters(self, parsed):
        assert len(parsed["chapters"]) == 167

    def test_first_chapter_is_copyright(self, parsed):
        assert parsed["chapters"][0]["title"] == "版权信息"

    def test_section_titles_from_ncx(self, parsed):
        """Section titles should come from toc.ncx bookmarks"""
        titles = [ch["title"] for ch in parsed["chapters"]]
        assert "人物表" in titles
        assert "壮年 失踪的孩子" in titles
        assert "老年 坏血统的故事" in titles
        assert "尾声 归还" in titles

    def test_no_book_title_as_chapter_title(self, parsed):
        """Chapter titles should not all be the book title"""
        titles = [ch["title"] for ch in parsed["chapters"]]
        book_title = "失踪的孩子（全球畅销近千万册"
        matching = [t for t in titles if t.startswith(book_title)]
        assert len(matching) == 0, f"Found {len(matching)} chapters with book title"

    def test_chapter_numbers_sequential(self, parsed):
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 168))

    def test_chapter_content_not_empty(self, parsed):
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 10, f"Chapter '{ch['title']}' only has {ch['word_count']} chars"
