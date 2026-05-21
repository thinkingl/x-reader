"""Game of Thrones TXT parsing test: verify numbered chapter header detection"""

import os
import pytest
from app.services.ebook_parser import get_parser

TEST_TXT = os.path.join(os.path.dirname(__file__), "data", "game_of_thrones.txt")


class TestGameOfThronesTxt:
    """Test A Game of Thrones TXT file parsing"""

    @pytest.fixture
    def parsed(self):
        parser = get_parser(TEST_TXT)
        return parser.parse()

    def test_format_is_txt(self, parsed):
        assert parsed["format"] == "txt"

    def test_total_chapters(self, parsed):
        """Mode system picks numbered_title pattern (38 chapters)"""
        assert len(parsed["chapters"]) == 38

    def test_chapter_titles_have_numbers(self, parsed):
        """Chapter titles should start with numbers (numbered_title mode)"""
        import re
        for ch in parsed["chapters"]:
            assert re.match(r'^\d+[．.]', ch["title"]), \
                f"Chapter {ch['chapter_number']} title missing number: '{ch['title']}'"

    def test_chapter_content_not_empty(self, parsed):
        """Each chapter should have substantial content"""
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 1000, \
                f"Chapter {ch['chapter_number']} ({ch['title']}) only has {ch['word_count']} chars"

    def test_chapter_numbers_sequential(self, parsed):
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 39))

    def test_total_word_count(self, parsed):
        """Total content should be over 1 million characters"""
        total = sum(ch["word_count"] for ch in parsed["chapters"])
        assert total > 1_000_000, f"Total {total} chars, expected > 1M"
