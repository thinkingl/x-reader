"""正则模式：基于文本模式匹配的章节检测"""

import re
import logging
from typing import List, Dict, Any
from .base import ChapterMode, Chapter, build_chapters

logger = logging.getLogger(__name__)


# 每种格式一个独立的正则（不互相干扰）
_PATTERNS = {
    "chinese_chapter": re.compile(r'^第\s*[0-9零一二三四五六七八九十百千万]+\s*章'),
    "chinese_section": re.compile(r'^第\s*[0-9零一二三四五六七八九十百千万]+\s*节'),
    "chinese_lecture": re.compile(r'^第\s*[0-9零一二三四五六七八九十百千万]+\s*讲'),
    "chinese_volume": re.compile(r'^第\s*[0-9零一二三四五六七八九十百千万]+\s*卷'),
    "chinese_part": re.compile(r'^第\s*[0-9零一二三四五六七八九十百千万]+\s*部'),
    "english_chapter": re.compile(r'^Chapter\s+\d+', re.IGNORECASE),
    "dash_number": re.compile(r'^-\d{1,4}-$'),
    "numbered_title": re.compile(r'^\d{1,4}[．.]\s*\S'),
    "uppercase_name": re.compile(r'^[A-Z][A-Z ]{2,30}$'),
    "special_markers": re.compile(r'^(序言|前言|后记|附录|楔子|引子|尾声|终章|卷末|跋|总论)$'),
}

# 模式是否需要前后空行验证（防止正文中的误匹配）
_NEEDS_BLANK_LINE = {
    "chinese_chapter", "chinese_section", "chinese_lecture",
    "chinese_volume", "chinese_part", "english_chapter",
    "numbered_title", "special_markers",
}


class RegexChapterMode(ChapterMode):
    """正则匹配模式：每种格式独立尝试"""

    def __init__(self, pattern_name: str):
        self.pattern_name = pattern_name
        self.name = f"regex_{pattern_name}"
        self._pattern = _PATTERNS[pattern_name]

    def applicable(self, context: Dict[str, Any]) -> bool:
        return "text" in context

    def extract(self, context: Dict[str, Any]) -> List[Chapter]:
        text = context.get("text", "")
        if not text:
            return []

        lines = text.split('\n')
        needs_blank = self.pattern_name in _NEEDS_BLANK_LINE

        # 找到所有匹配行
        boundaries = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if not self._pattern.match(stripped):
                continue
            # 需要前后空行验证
            if needs_blank:
                prev_blank = (i == 0 or not lines[i - 1].strip())
                next_blank = (i + 1 >= len(lines) or not lines[i + 1].strip())
                if not (prev_blank or next_blank):
                    continue
            boundaries.append((i, stripped))

        if len(boundaries) < 2:
            return []

        # 按边界拆分章节
        chapter_data = []
        for j, (line_idx, title) in enumerate(boundaries):
            if j + 1 < len(boundaries):
                end_idx = boundaries[j + 1][0]
            else:
                end_idx = len(lines)
            content = '\n'.join(lines[line_idx + 1:end_idx]).strip()
            chapter_data.append({"title": title, "content": content})

        return build_chapters(chapter_data)


def create_all_regex_modes() -> List[RegexChapterMode]:
    """创建所有正则模式实例"""
    return [RegexChapterMode(name) for name in _PATTERNS]
