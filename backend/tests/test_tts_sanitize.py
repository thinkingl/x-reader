"""EPUB TTS 文本清理 + 世界尽头电子书解析测试"""

import os
import re
import pytest
from app.services.ebook_parser import EpubParser, sanitize_text, inline_annotations, unwrap_text

NANA_EPUB = os.path.join(os.path.dirname(__file__), "data", "nana.epub")
WORLDS_END_EPUB = os.path.join(os.path.dirname(__file__), "data", "worlds_end.epub")
XUSANGUAN_EPUB = os.path.join(os.path.dirname(__file__), "data", "xusanguan.epub")


class TestSanitizeText:
    """测试 sanitize_text 函数"""

    def test_remove_book_title_marks(self):
        """《》 替换为空格"""
        result = sanitize_text("《世界尽头与冷酷仙境》村上春树")
        assert "《" not in result
        assert "》" not in result
        assert "世界尽头与冷酷仙境" in result

    def test_remove_corner_brackets(self):
        """「」『』 替换为空格"""
        result = sanitize_text("「你好」『世界』")
        assert "「" not in result and "」" not in result
        assert "『" not in result and "』" not in result

    def test_remove_lenticular_brackets(self):
        """【】 替换为空格"""
        result = sanitize_text("【注释】正文")
        assert "【" not in result and "】" not in result

    def test_remove_tortoise_brackets(self):
        """〖〗 替换为空格"""
        result = sanitize_text("〖说明〗内容")
        assert "〖" not in result and "〗" not in result

    def test_remove_angle_brackets(self):
        """〈〉 替换为空格"""
        result = sanitize_text("〈引文〉正文")
        assert "〈" not in result and "〉" not in result

    def test_collapse_multiple_blank_lines(self):
        """多余空行合并为单个"""
        text = "段落一\n\n\n\n段落二\n\n\n\n\n段落三"
        result = sanitize_text(text)
        assert "\n\n\n" not in result
        count = result.count("\n\n")
        assert count == 2, f"expected 2 double-newlines, got {count}"

    def test_strip_whitespace(self):
        """去除首尾空白"""
        result = sanitize_text("\n\n  正文内容  \n\n")
        assert result.startswith("正文")
        assert result.endswith("内容")

    def test_preserve_normal_text(self):
        """正常文本和标点不变"""
        text = '他说："你好。"她回答：「嗯。」这是一个——测试……吧？'
        result = sanitize_text(text)
        assert "他说" in result
        assert "你好" in result
        assert "测试" in result

    def test_all_symbols_removed_from_nana(self, parsed_nana):
        """《娜娜》中不应残留任何 TTS 无意义符号"""
        bad_chars = r'[《》〈〉「」『』【】〖〗]'
        for ch in parsed_nana["chapters"]:
            found = re.findall(bad_chars, ch["text_content"])
            assert len(found) == 0, (
                f"Ch{ch['chapter_number']} contains: {found[:10]}"
            )

    def test_all_symbols_removed_from_worlds_end(self, parsed_worlds_end):
        """《世界尽头》中不应残留任何 TTS 无意义符号"""
        bad_chars = r'[《》〈〉「」『』【】〖〗]'
        for ch in parsed_worlds_end["chapters"]:
            found = re.findall(bad_chars, ch["text_content"])
            assert len(found) == 0, (
                f"Ch{ch['chapter_number']} contains: {found[:10]}"
            )


class TestWorldsEnd:
    """测试《世界尽头与冷酷仙境》EPUB 解析"""

    @pytest.fixture
    def parsed(self):
        parser = EpubParser(WORLDS_END_EPUB)
        return parser.parse()

    def test_total_chapters(self, parsed):
        assert len(parsed["chapters"]) == 44

    def test_metadata(self, parsed):
        assert "世界尽头" in parsed["title"]
        assert "冷酷仙境" in parsed["title"]
        assert "村上春树" in parsed["author"]
        assert parsed["format"] == "epub"

    def test_chapter_titles_not_generic(self, parsed):
        """章节标题不应是通用的"正文"或"Chapter X"格式"""
        for ch in parsed["chapters"]:
            title = ch["title"]
            assert title != "正文", f"Ch{ch['chapter_number']} has generic title"
            if ch["chapter_number"] >= 5:  # 前4章是元数据页
                assert "Chapter" not in title, f"Ch{ch['chapter_number']}: {title}"

    def test_chapter_title_format(self, parsed):
        """主体章节标题应为"数字.xxx--xxx"格式"""
        for ch in parsed["chapters"]:
            if ch["chapter_number"] >= 5:
                title = ch["title"]
                assert re.match(r'\d+\.', title), (
                    f"Ch{ch['chapter_number']} title not numbered: {title}"
                )

    def test_chapter_content_not_empty(self, parsed):
        """内容章节字数不少于 500（排除元数据页 Ch1-4）"""
        for ch in parsed["chapters"]:
            if ch["chapter_number"] >= 5:
                assert ch["word_count"] > 500, (
                    f"Ch{ch['chapter_number']} too short ({ch['word_count']})"
                )

    def test_first_story_chapter(self, parsed):
        """第一个故事章节内容正确"""
        ch5 = parsed["chapters"][4]  # Ch5 = first real chapter
        assert "酷仙境" in ch5["title"] or "冷酷仙境" in ch5["title"]
        assert "电梯" in ch5["title"]
        assert "电梯" in ch5["text_content"][:200]
        assert "缓慢" in ch5["text_content"][:500]

    def test_alternating_worlds(self, parsed):
        """章节应交替：冷酷仙境 / 世界尽头"""
        odd_cold = 0  # 奇数序号为"冷酷仙境"
        even_world = 0  # 偶数序号为"世界尽头"
        for ch in parsed["chapters"]:
            if ch["chapter_number"] < 5:
                continue
            adjusted = ch["chapter_number"] - 4
            if adjusted % 2 == 1 and "冷酷" in ch["title"]:
                odd_cold += 1
            if adjusted % 2 == 0 and "世界" in ch["title"]:
                even_world += 1
        assert odd_cold >= 18, f"Expected ~20 odd=cold, got {odd_cold}"
        assert even_world >= 18, f"Expected ~20 even=world, got {even_world}"


class TestCombinedProcessing:
    """测试 sanitize + inline_annotations 组合"""

    def test_sanitize_and_annotate_pipeline(self):
        """验证实际流水线(先annotate再sanitize)结果正确"""
        text = "【题记】奥林匹斯山①，继续。\n\n①注解内容。"
        # 实际流水线：先内联注解，再清理符号
        result = sanitize_text(inline_annotations(text))
        assert "【" not in result and "】" not in result
        assert "①" not in result
        assert "(注:" in result


class TestUnwrapText:
    """测试 unwrap_text 硬换行截断修复"""

    def test_merge_mid_sentence_lines(self):
        """句子中间的截断行应合并为一句"""
        text = "晚上九点钟了，游艺剧院的演出厅里还是空荡荡的，只有楼厅和正厅前座里，有几个早\n到的观众在等候开演。"
        result = unwrap_text(text)
        lines = result.split('\n')
        assert len(lines) == 1, f"Expected 1 paragraph, got {len(lines)}"
        assert "早到的观众" in result

    def test_preserve_paragraph_boundary(self):
        """以句号结束的行应保留为段落边界"""
        text = "第一个段落结束。\n第二个段落开始。"
        result = unwrap_text(text)
        lines = result.split('\n')
        assert len(lines) >= 2, f"Expected 2 paragraphs, got {len(lines)}"

    def test_exclamation_ends_paragraph(self):
        """以感叹号结束的行应保留段落边界"""
        text = "真是太棒了！\n这是新的段落。"
        result = unwrap_text(text)
        lines = result.split('\n')
        assert len(lines) >= 2

    def test_question_ends_paragraph(self):
        """以问号结束的行应保留段落边界"""
        text = "你认识她吗？\n我不认识。"
        result = unwrap_text(text)
        lines = result.split('\n')
        assert len(lines) >= 2

    def test_quotation_ends_paragraph(self):
        """以引号结束的行应保留段落边界"""
        text = '他说："你好。"\n她回答："你好。"'
        result = unwrap_text(text)
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) == 2, f"Expected 2 paragraphs, got {len(lines)}: {lines}"

    def test_multiple_broken_lines_merge(self):
        """多行截断合并为一个段落"""
        text = "幕布被笼罩在一片昏暗之中，犹如一大块红色的斑点。舞台上阒然无声，成排的脚灯熄灭\n了，乐师们的乐谱架摆得七零八落。只有四楼楼座里，发出阵阵喧嚣声。"
        result = unwrap_text(text)
        # "熄灭了" 和 "发出阵阵喧嚣声。" 都是句号结尾 → 2段落
        assert "七零八落" in result
        assert "熄灭了" in result

    def test_empty_lines_separate_paragraphs(self):
        """空行应分隔段落"""
        text = "第一段。\n\n\n第二段。"
        result = unwrap_text(text)
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) == 2, f"Expected 2 paragraphs, got {lines}"

    def test_unchanged_if_no_broken_lines(self):
        """无截断的文本应保持不变"""
        text = "完整的段落一。\n完整的段落二。"
        result = unwrap_text(text)
        assert "完整的段落一" in result
        assert "完整的段落二" in result

    def test_nana_chapter_has_few_lines(self, parsed_nana):
        """《娜娜》经 unwrap 后每章行数应大幅减少（原 615 → ~200）"""
        ch1 = parsed_nana["chapters"][0]
        lines = [l for l in ch1["text_content"].split('\n') if l.strip()]
        assert len(lines) < 250, (
            f"Expected <250 lines after unwrap, got {len(lines)}"
            f" (original was 615 mid-sentence broken lines)"
        )

    def test_nana_no_mid_sentence_cuts(self, parsed_nana):
        """《娜娜》每章最多 2 行不以句号结尾（排除装饰线）"""
        sentence_end = set('。！？…"-—\uFF09')
        for ch in parsed_nana["chapters"]:
            bad_lines = 0
            for line in ch["text_content"].split('\n'):
                stripped = line.strip()
                if not stripped or len(stripped) <= 10:
                    continue
                if not re.search(r'[\u4e00-\u9fff]', stripped):
                    continue
                if re.match(r'^[\-]{3,}', stripped):
                    continue
                if stripped[-1] not in sentence_end:
                    bad_lines += 1
            assert bad_lines <= 2, (
                f"Ch{ch['chapter_number']} has {bad_lines} mid-sentence cuts (max 2)"
            )

    def test_worlds_end_still_parseable(self, parsed_worlds_end):
        """《世界尽头》unwrap 后解析仍正常"""
        ch5 = parsed_worlds_end["chapters"][4]
        assert "电梯" in ch5["text_content"][:200]
        assert len(ch5["text_content"].split('\n')) < 200


class TestXuSanguan:
    """测试《许三观卖血记》EPUB — 正常段落结构，不应被 unwrap"""

    @pytest.fixture
    def parsed(self):
        return EpubParser(XUSANGUAN_EPUB).parse()

    def test_total_chapters(self, parsed):
        assert len(parsed["chapters"]) == 30

    def test_metadata(self, parsed):
        assert "许三观" in parsed["title"]
        assert "余华" in parsed["author"]

    def test_no_chapters_are_split(self, parsed):
        """所有章节都不应标记为 was_split（每章来自独立 HTML 文件）"""
        for ch in parsed["chapters"]:
            assert not ch.get("was_split"), (
                f"Ch{ch['chapter_number']} should NOT be was_split"
            )

    def test_paragraphs_preserved(self, parsed):
        """段落结构应保持：每章有多个 <p> 段落，且内容正确"""
        ch2 = parsed["chapters"][1]  # 第一章
        text = ch2["text_content"]
        # 验证关键段落的独立性——不应被合并
        assert "第一章" in text.split('\n')[0], "First line should be chapter title"
        assert "许三观是城里丝厂的送茧工" in text
        assert "他爷爷问：" in text
        assert "我爹早死啦" in text
        assert "许三观的四叔正在下面瓜地里浇粪" in text
        
        # 检查段落之间存在换行（至少10个段落）
        paragraphs = [l for l in text.split('\n') if l.strip()]
        assert len(paragraphs) >= 10, f"Expected >=10 paragraphs, got {len(paragraphs)}"
        
        # 验证没有意外的合并：书名不应紧挨着作者
        ch1 = parsed["chapters"][0]
        assert "许三观卖血记\n" in ch1["text_content"] or \
               "许三观卖血记" == ch1["text_content"].split('\n')[0].strip(), \
               "Title should be on its own line"

    def test_chapter_content_not_empty(self, parsed):
        for ch in parsed["chapters"]:
            assert ch["word_count"] > 0, f"Ch{ch['chapter_number']} is empty"

    def test_title_format(self, parsed):
        """章节标题应为第X章格式（排除首页信息页）"""
        for ch in parsed["chapters"]:
            if ch["chapter_number"] >= 2:
                title = ch["title"]
                assert "第" in title or "章" in title, f"Ch{ch['chapter_number']}: {title}"


@pytest.fixture
def parsed_nana():
    return EpubParser(NANA_EPUB).parse()


@pytest.fixture
def parsed_worlds_end():
    return EpubParser(WORLDS_END_EPUB).parse()
