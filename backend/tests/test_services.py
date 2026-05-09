import pytest
import tempfile
import os
from app.services.ebook_parser import TxtParser


def test_txt_parser_single_chapter():
    content = "This is the first chapter.\n\nThis is some content."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TxtParser(f.name)
        result = parser.parse()
        assert result["format"] == "txt"
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["word_count"] > 0
        os.unlink(f.name)


def test_txt_parser_multi_chapter():
    content = """第一章 开始

这是第一章的内容。

第二章 继续

这是第二章的内容。
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TxtParser(f.name)
        result = parser.parse()
        assert len(result["chapters"]) >= 2
        os.unlink(f.name)


def test_txt_parser_chapter_detection():
    content = """第1章 引言

引言内容。

第2章 正文

正文内容。

第3章 结尾

结尾内容。
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TxtParser(f.name)
        result = parser.parse()
        assert len(result["chapters"]) == 3
        for ch in result["chapters"]:
            assert ch["word_count"] > 0
        os.unlink(f.name)


def test_txt_parser_uppercase_headers():
    """Test uppercase chapter headers like PROLOGUE, character names (Game of Thrones style)"""
    content = """PROLOGUE

We should start back, Gared urged as the woods began to grow dark.

EDDARD

He dreamt an old dream, of three knights in white cloaks.

CATELYN

Catelyn had never liked this godswood.

JON

Jon found it hard to look away from him.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TxtParser(f.name)
        result = parser.parse()
        assert len(result["chapters"]) == 4
        assert result["chapters"][0]["title"] == "PROLOGUE"
        assert result["chapters"][1]["title"] == "EDDARD"
        assert result["chapters"][2]["title"] == "CATELYN"
        assert result["chapters"][3]["title"] == "JON"
        assert "We should start back" in result["chapters"][0]["text_content"]
        assert "dreamt an old dream" in result["chapters"][1]["text_content"]
        os.unlink(f.name)


def test_txt_parser_uppercase_with_fullwidth_spaces():
    """Test uppercase headers with fullwidth spaces (common in Chinese-prefixed TXT files)"""
    content = "\u3000\u3000PROLOGUE\n\n\u3000\u3000We should start back.\n\n\u3000\u3000EDDARD\n\n\u3000\u3000He dreamt an old dream.\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TxtParser(f.name)
        result = parser.parse()
        assert len(result["chapters"]) == 2
        assert result["chapters"][0]["title"] == "PROLOGUE"
        assert result["chapters"][1]["title"] == "EDDARD"
        os.unlink(f.name)
