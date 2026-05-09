"""Game of Thrones TXT parsing test: verify numbered + uppercase chapter header detection"""

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
        """Should have 73 chapters (38 numbered + 35 unnumbered POV chapters)"""
        assert len(parsed["chapters"]) == 73

    def test_first_chapter_is_prologue(self, parsed):
        assert parsed["chapters"][0]["title"] == "PROLOGUE"

    def test_second_chapter_is_bran(self, parsed):
        """Chapter 2 should be BRAN (1．BRAN)"""
        assert parsed["chapters"][1]["title"] == "BRAN"

    def test_chapter_titles_are_uppercase(self, parsed):
        """All chapter titles should be uppercase words"""
        import re
        for ch in parsed["chapters"]:
            assert re.fullmatch(r'[A-Z ]{3,}', ch["title"]), \
                f"Chapter {ch['chapter_number']} title not uppercase: '{ch['title']}'"

    def test_unique_pov_characters(self, parsed):
        """Should have chapters from multiple POV characters"""
        titles = {ch["title"] for ch in parsed["chapters"]}
        expected = {"PROLOGUE", "EDDARD", "CATELYN", "JON", "ARYA",
                    "SANSA", "TYRION", "DAENERYS", "BRAN"}
        assert expected.issubset(titles), f"Missing POV characters: {expected - titles}"

    def test_chapter_content_not_empty(self, parsed):
        """Each chapter should have substantial content"""
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 1000, \
                f"Chapter {ch['chapter_number']} ({ch['title']}) only has {ch['word_count']} chars"

    def test_prologue_content_start(self, parsed):
        """Prologue should start with the correct text"""
        text = parsed["chapters"][0]["text_content"]
        assert "We should start back" in text

    def test_eddard_chapters_exist(self, parsed):
        """Eddard should have multiple POV chapters"""
        eddard_chs = [ch for ch in parsed["chapters"] if ch["title"] == "EDDARD"]
        assert len(eddard_chs) >= 6, f"Eddard should have >= 6 chapters, got {len(eddard_chs)}"

    def test_daenerys_chapters_exist(self, parsed):
        """Daenerys should have multiple POV chapters"""
        dany_chs = [ch for ch in parsed["chapters"] if ch["title"] == "DAENERYS"]
        assert len(dany_chs) >= 4, f"Daenerys should have >= 4 chapters, got {len(dany_chs)}"

    def test_chapter_numbers_sequential(self, parsed):
        numbers = [ch["chapter_number"] for ch in parsed["chapters"]]
        assert numbers == list(range(1, 74))

    def test_total_word_count(self, parsed):
        """Total content should be over 1 million characters"""
        total = sum(ch["word_count"] for ch in parsed["chapters"])
        assert total > 1_000_000, f"Total {total} chars, expected > 1M"

    def test_no_number_prefix_in_titles(self, parsed):
        """Titles should not contain number prefixes like '1．'"""
        import re
        for ch in parsed["chapters"]:
            assert not re.match(r'^\d+[．.]', ch["title"]), \
                f"Chapter {ch['chapter_number']} title has number prefix: '{ch['title']}'"
