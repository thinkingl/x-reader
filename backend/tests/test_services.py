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
