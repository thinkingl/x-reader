"""章节模式框架：多模式择优分章"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """解析出的章节"""
    title: str
    text_content: str
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = len(self.text_content)


@dataclass
class ParseResult:
    """某个模式的解析结果"""
    mode_name: str
    chapters: List[Chapter]
    score: float = 0.0


# 特殊章节（前言/目录/后记等），不参与序号连续性评分
_SPECIAL_TITLES = {
    "前言", "序言", "序", "后记", "跋", "目录", "附录", "楔子", "引子",
    "尾声", "终章", "卷末", "总论", "版权信息", "人物表", "注释",
    "preface", "foreword", "introduction", "prologue", "epilogue",
    "afterword", "appendix", "contents", "table of contents",
}


def _is_special(ch: Chapter) -> bool:
    """判断是否为特殊章节（前言/目录/后记等）"""
    t = ch.title.strip().lower()
    return t in {s.lower() for s in _SPECIAL_TITLES}


def score_chapters(chapters: List[Chapter]) -> float:
    """评估章节质量，0-100 分。特殊章节（前言/目录/后记）不参与序号和均匀度评分。"""
    n = len(chapters)
    if n < 2:
        return 0.0

    # 分离特殊章节和正式章节
    special = [ch for ch in chapters if _is_special(ch)]
    main = [ch for ch in chapters if not _is_special(ch)]
    n_main = len(main)

    # 1) 序号连续性（0-40分）—— 只看正式章节
    if n_main >= 2:
        numbers = []
        for ch in main:
            m = re.search(r'(\d+)', ch.title)
            numbers.append(int(m.group(1)) if m else None)

        numbered = [x for x in numbers if x is not None]
        if len(numbered) >= n_main * 0.5:
            if numbered == list(range(1, len(numbered) + 1)):
                sequential_score = 40.0
            else:
                consecutive = sum(1 for i in range(1, len(numbered)) if numbered[i] == numbered[i-1] + 1)
                ratio = consecutive / max(len(numbered) - 1, 1)
                sequential_score = ratio * 40.0
        else:
            unique_ratio = len(set(ch.title for ch in main)) / n_main
            sequential_score = unique_ratio * 30.0
    else:
        # 正式章节太少，用全部章节的标题唯一性
        unique_ratio = len(set(ch.title for ch in chapters)) / n
        sequential_score = unique_ratio * 20.0

    # 2) 标题质量（0-30分）—— 全部章节
    title_scores = []
    default_titles = {"Chapter", "章节", "正文", "无标题"}
    generic_prefixes = ("Chapter ", "Chapter_", "第 ", "第")
    for ch in chapters:
        t = ch.title.strip()
        if not t:
            title_scores.append(0)
            continue
        s = 10  # 有标题基础分
        if 3 <= len(t) <= 50:
            s += 10  # 长度合理
        if t not in default_titles and not any(t.startswith(p) for p in generic_prefixes):
            s += 10  # 非默认标题
        else:
            s -= 5  # 通用标题额外扣分（会截断句子）
        title_scores.append(s)
    title_score = sum(title_scores) / n

    # 3) 长度均匀度（0-30分）—— 只看正式章节
    if n_main >= 2:
        lengths = [ch.word_count for ch in main]
    else:
        lengths = [ch.word_count for ch in chapters]
    mean_len = sum(lengths) / len(lengths)
    if mean_len > 0:
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_len = variance ** 0.5
        cv = std_len / mean_len
        if cv < 0.3:
            uniformity_score = 30.0
        elif cv < 0.5:
            uniformity_score = 25.0
        elif cv < 1.0:
            uniformity_score = 15.0
        else:
            uniformity_score = 5.0
    else:
        uniformity_score = 0.0

    # 4) 超大章节惩罚 —— 超过 100K 字按比例扣分，不一刀切
    penalty = 0.0
    for ch in chapters:
        if ch.word_count > 100_000:
            ratio = ch.word_count / 100_000
            # 100K→0, 200K→5, 500K→15, 1M→25
            penalty += min(25.0, (ratio - 1) * 5.0)
    penalty = min(80.0, penalty)

    # 5) 标题重复惩罚 —— 多数章节标题相同说明分章失败
    title_counts = {}
    for ch in chapters:
        t = ch.title.strip()
        title_counts[t] = title_counts.get(t, 0) + 1
    max_dup = max(title_counts.values()) if title_counts else 0
    dup_ratio = max_dup / n if n > 0 else 0
    if dup_ratio > 0.5:
        penalty += min(30.0, (dup_ratio - 0.5) * 60.0)

    # 6) 截断句子惩罚 —— 章节末尾没有正常结束标点，说明切分点错误
    # 排除歌词/古诗（连续多行无标点是正常格式）
    sentence_enders = set('。！？…!?."）」』')
    cut_count = 0
    for ch in chapters:
        text = ch.text_content.rstrip()
        if not text or text[-1] in sentence_enders:
            continue
        # 检查是否是歌词/古诗（连续无标点行占比高）
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            no_punct_lines = sum(1 for l in lines if l and l[-1] not in sentence_enders)
            if no_punct_lines / len(lines) > 0.6:
                continue  # 歌词/古诗，不惩罚
        cut_count += 1
    cut_ratio = cut_count / n if n > 0 else 0
    if cut_ratio > 0.3:
        penalty += min(40.0, (cut_ratio - 0.3) * 80.0)

    # 7) 过少章节惩罚 —— 少于 10 章通常分章失败
    if n < 10:
        penalty += (10 - n) * 5.0

    # 8) 多章节奖励 —— 检测到更多章节通常更准确（对数奖励，上限 30 分）
    import math
    bonus = min(30.0, math.log2(max(n, 1)) * 5.0)

    total = sequential_score + title_score + uniformity_score - penalty + bonus
    logger.debug(
        f"Score: seq={sequential_score:.1f} title={title_score:.1f} "
        f"uniform={uniformity_score:.1f} total={total:.1f} "
        f"(n={n}, main={n_main}, special={len(special)})"
    )
    return total


def build_chapters(chapter_data: List[Dict[str, str]]) -> List[Chapter]:
    """从 [{title, content}] 构建 Chapter 列表，过滤过短的章节"""
    chapters = []
    for i, d in enumerate(chapter_data):
        title = d.get("title", "").strip()
        content = d.get("content", "").strip()
        if not content or len(content) < 10:
            continue
        chapters.append(Chapter(title=title, text_content=content))
    return chapters


class ChapterMode:
    """章节模式基类"""

    name: str = "base"

    def applicable(self, context: Dict[str, Any]) -> bool:
        """判断此模式是否适用于当前书籍"""
        raise NotImplementedError

    def extract(self, context: Dict[str, Any]) -> List[Chapter]:
        """提取章节，返回 Chapter 列表。空列表表示此模式无法提取。"""
        raise NotImplementedError
