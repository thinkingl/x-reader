"""章节模式框架"""

from .base import Chapter, ParseResult, ChapterMode, score_chapters, build_chapters, _is_special
from .regex_mode import RegexChapterMode, create_all_regex_modes
from .ncx_mode import NcxBookmarkMode, parse_ncx
from .spine_mode import SpineFileMode
from .html_heading_mode import HtmlHeadingMode

__all__ = [
    "Chapter", "ParseResult", "ChapterMode", "score_chapters", "build_chapters", "_is_special",
    "RegexChapterMode", "create_all_regex_modes",
    "NcxBookmarkMode", "parse_ncx",
    "SpineFileMode",
    "HtmlHeadingMode",
    "select_best_mode",
]


def select_best_mode(chapters_from_modes: list, min_score: float = 20.0):
    """从多个模式结果中选择最佳的。

    Args:
        chapters_from_modes: list of (mode_name, [Chapter])
        min_score: 最低可接受分数

    Returns:
        (best_mode_name, best_chapters) 或 (None, []) 如果都低于阈值
    """
    from .base import ParseResult, score_chapters

    results = []
    for mode_name, chapters in chapters_from_modes:
        if len(chapters) < 2:
            continue
        s = score_chapters(chapters)
        results.append(ParseResult(mode_name=mode_name, chapters=chapters, score=s))

    if not results:
        return None, []

    best = max(results, key=lambda r: r.score)
    if best.score < min_score:
        return None, []

    return best.mode_name, best.chapters
