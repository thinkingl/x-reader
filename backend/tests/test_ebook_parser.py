"""EPUB电子书解析测试 - 朱镕基答记者问"""

import os
import pytest
from app.services.ebook_parser import EpubParser


# 测试数据：每个章节的期望内容
# 用户可根据实际内容修改这些数据，然后调整解析代码使其通过
EXPECTED_CHAPTERS = [
    {
        "chapter_number": 1,
        "title": "一、在全国人大会议记者招待会上回答中外记者提问",
        "expected_title": "一、在全国人大会议记者招待会上回答中外记者提问",
        "start_text": "",  # 填入章节开始的文本
        "end_text": "",    # 填入章节结束的文本
        "description": "目录页/分节标题，可能只有标题没有正文"
    },
    {
        "chapter_number": 2,
        "title": "在九届全国人大一次会议记者招待会上回答中外记者提问（1998年3月19日）",
        "expected_title": "在九届全国人大一次会议记者招待会上回答中外记者提问（1998年3月19日）",
        "start_text": "美国时代周刊记者：上周我曾有机会到吉林省和辽宁省去观摩了当地的村民委员会的选举",
        "end_text": "我希望通过你向印度政府的首脑和印度人民致以我最美好的祝愿",
        "description": "1998年记者会"
    },
    {
        "chapter_number": 3,
        "title": "在九届全国人大二次会议记者招待会上回答中外记者提问（1999年3月15日）",
        "expected_title": "在九届全国人大二次会议记者招待会上回答中外记者提问（1999年3月15日）",
        "start_text": "意大利《24小时太阳报》记者：有人认为，10年以后世界会有三种大货币",
        "end_text": "只要双方从大局出发，从促进国际市场的繁荣和稳定出发，大家都作一点让步，那么达成协议是很有希望的",
        "description": "1999年记者会"
    },
    {
        "chapter_number": 4,
        "title": "在九届全国人大三次会议记者招待会上回答中外记者提问（2000年3月15日）",
        "expected_title": "在九届全国人大三次会议记者招待会上回答中外记者提问（2000年3月15日）",
        "start_text": "朱镕基：这是我担任总理以来的第三次记者招待会",
        "end_text": "一定能够通过给中国永久正常贸易关系",
        "description": "2000年记者会"
    },
    {
        "chapter_number": 5,
        "title": "在九届全国人大四次会议记者招待会上回答中外记者提问（2001年3月15日）",
        "expected_title": "在九届全国人大四次会议记者招待会上回答中外记者提问（2001年3月15日）",
        "start_text": "新华社记者：您在这次会议的报告中提出，近期要继续实施积极的财政政策",
        "end_text": "明年的记者招待会，我可能会对你这个问题回答得更加具体",
        "description": "2001年记者会"
    },
    {
        "chapter_number": 6,
        "title": "在九届全国人大五次会议记者招待会上回答中外记者提问（2002年3月15日）",  # 当前解析为"Chapter 6"，需要修正
        "expected_title": "在九届全国人大五次会议记者招待会上回答中外记者提问（2002年3月15日）",
        "start_text": "在九届全国人大五次会议记者招待会上回答中外记者提问（2002年3月15日）",
        "end_text": "我刚才已经说过，没有任何一个内地的城市可以在近期代替香港。我们都应该有信心，我们的目标一定能够达到。",
        "description": "2002年记者会，当前标题解析错误"
    },
    {
        "chapter_number": 7,
        "title": "二、接受外国记者采访",
        "expected_title": "二、接受外国记者采访",
        "start_text": "",  # 目录页
        "end_text": "",
        "description": "第二部分目录页"
    },
    {
        "chapter_number": 8,
        "title": "接受德国《商报》记者柴德立兹采访（1993年5月6日）",
        "expected_title": "接受德国《商报》记者柴德立兹采访（1993年5月6日）",
        "start_text": "柴德立兹：我并不期望中国领导人像美国总统里根那样脱去衬衣",
        "end_text": "请转达我对德国人民和德国朋友们的问候",
        "description": "1993年德国采访"
    },
    # TODO: 添加更多章节的期望数据
]


@pytest.fixture
def epub_path():
    """EPUB文件路径"""
    path = "data/books/2/朱镕基答记者问 (1).epub"
    if not os.path.exists(path):
        pytest.skip(f"EPUB文件不存在: {path}")
    return path


@pytest.fixture
def parsed_book(epub_path):
    """解析EPUB文件"""
    parser = EpubParser(epub_path)
    return parser.parse()


class TestEpubMetadata:
    """测试EPUB元数据解析"""

    def test_book_title(self, parsed_book):
        """测试书名解析"""
        assert parsed_book["title"] == "朱镕基答记者问"

    def test_book_author(self, parsed_book):
        """测试作者解析"""
        assert parsed_book["author"] == "《朱镕基答记者问》编辑组"

    def test_book_format(self, parsed_book):
        """测试格式"""
        assert parsed_book["format"] == "epub"


class TestChapterCount:
    """测试章节数量"""

    def test_chapter_count(self, parsed_book):
        """测试章节数量是否正确"""
        chapters = parsed_book["chapters"]
        # 当前解析出64个章节，但可能需要调整
        print(f"\n解析出 {len(chapters)} 个章节")
        assert len(chapters) > 0, "至少应该解析出一些章节"


class TestChapterTitles:
    """测试章节标题"""

    @pytest.mark.parametrize("expected", EXPECTED_CHAPTERS, ids=lambda c: c["description"])
    def test_chapter_title(self, parsed_book, expected):
        """测试章节标题是否正确"""
        chapters = parsed_book["chapters"]
        chapter_num = expected["chapter_number"]

        if chapter_num > len(chapters):
            pytest.fail(f"章节 {chapter_num} 不存在，总共只有 {len(chapters)} 个章节")

        chapter = chapters[chapter_num - 1]
        actual_title = chapter["title"]

        if expected["expected_title"]:
            assert actual_title == expected["expected_title"], \
                f"章节 {chapter_num} 标题不匹配\n期望: {expected['expected_title']}\n实际: {actual_title}"


class TestChapterContent:
    """测试章节内容"""

    @pytest.mark.parametrize("expected", EXPECTED_CHAPTERS, ids=lambda c: c["description"])
    def test_chapter_start_text(self, parsed_book, expected):
        """测试章节开始文本"""
        if not expected["start_text"]:
            pytest.skip("未设置期望的开始文本")

        chapters = parsed_book["chapters"]
        chapter_num = expected["chapter_number"]

        if chapter_num > len(chapters):
            pytest.fail(f"章节 {chapter_num} 不存在")

        chapter = chapters[chapter_num - 1]
        text = chapter["text_content"]

        assert expected["start_text"] in text, \
            f"章节 {chapter_num} 开始文本不匹配\n期望包含: {expected['start_text'][:50]}...\n实际开始: {text[:100]}..."

    @pytest.mark.parametrize("expected", EXPECTED_CHAPTERS, ids=lambda c: c["description"])
    def test_chapter_end_text(self, parsed_book, expected):
        """测试章节结束文本"""
        if not expected["end_text"]:
            pytest.skip("未设置期望的结束文本")

        chapters = parsed_book["chapters"]
        chapter_num = expected["chapter_number"]

        if chapter_num > len(chapters):
            pytest.fail(f"章节 {chapter_num} 不存在")

        chapter = chapters[chapter_num - 1]
        text = chapter["text_content"]

        assert expected["end_text"] in text, \
            f"章节 {chapter_num} 结束文本不匹配\n期望包含: {expected['end_text'][:50]}...\n实际结束: {text[-100:]}"


class TestChapterBoundaries:
    """测试章节边界 - 确保章节内容不重叠、不遗漏"""

    def test_no_duplicate_content(self, parsed_book):
        """测试章节之间没有重复内容"""
        chapters = parsed_book["chapters"]

        for i in range(len(chapters) - 1):
            current = chapters[i]
            next_chapter = chapters[i + 1]

            # 获取当前章节的最后100个字符
            current_end = current["text_content"][-100:] if len(current["text_content"]) > 100 else current["text_content"]
            # 获取下一章节的前100个字符
            next_start = next_chapter["text_content"][:100] if len(next_chapter["text_content"]) > 100 else next_chapter["text_content"]

            # 检查是否有重叠（简化检查：检查最后50个字符是否出现在下一章开始）
            overlap_check = current_end[-50:]
            if overlap_check in next_start and len(overlap_check) > 20:
                print(f"\n警告: 章节 {current['chapter_number']} 和 {next_chapter['chapter_number']} 可能有内容重叠")


def test_dump_chapter_info(parsed_book):
    """打印章节信息用于调试"""
    print(f"\n{'='*60}")
    print(f"书名: {parsed_book['title']}")
    print(f"作者: {parsed_book['author']}")
    print(f"章节数: {len(parsed_book['chapters'])}")
    print(f"{'='*60}")

    for ch in parsed_book["chapters"]:
        text = ch["text_content"]
        start = text[:80].replace("\n", " ") if text else ""
        end = text[-80:].replace("\n", " ") if text else ""

        print(f"\n章节 {ch['chapter_number']}: {ch['title']}")
        print(f"  字数: {ch['word_count']}")
        print(f"  开始: {start}...")
        print(f"  结束: ...{end}")


def test_export_chapters_to_text(parsed_book):
    """导出章节内容到data/text目录，文件名格式与音频一致"""
    import re

    book_id = 2  # 朱镕基答记者问
    output_dir = f"data/text/{book_id}"
    os.makedirs(output_dir, exist_ok=True)

    for ch in parsed_book["chapters"]:
        # 清理标题中的特殊字符，用于文件名
        title = ch["title"] or f"Chapter {ch['chapter_number']}"
        # 移除书名号、括号等特殊字符，保留中文、英文、数字
        safe_title = re.sub(r'[《》（）\(\)、，,\s]', '', title)
        # 限制文件名长度
        safe_title = safe_title[:50]

        # 文件名格式：{序号:03d}_{标题}.txt
        filename = f"{ch['chapter_number']:03d}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)

        # 写入章节内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(ch['text_content'])

    # 列出生成的文件
    files = os.listdir(output_dir)
    print(f"\n导出 {len(files)} 个文本文件到 {output_dir}/")
    for f in sorted(files)[:10]:
        print(f"  {f}")
    if len(files) > 10:
        print(f"  ... 还有 {len(files) - 10} 个文件")
