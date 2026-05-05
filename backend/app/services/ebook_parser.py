import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path

# 章节标题匹配模式
_CHAPTER_NUM_RE = re.compile(
    r'(?:'
    r'第[0-9零一二三四五六七八九十百千万]+\s*[章节篇卷部]'  # 第X章
    r'|第\s*\d+\s*[章节篇卷部]'  # 第 123 章
    r'|Chapter\s+\d+'  # Chapter 123
    r'|楔子|引子|尾声|终章|序言|前言|后记|附录|卷末|跋'  # 特殊标记
    r')'
)
# 裸中文数字作为章节标记（单独成行，1-4个中文字符）
_CHINESE_NUM_RE = re.compile(r'^[　\s]*([一二三四五六七八九十百]+)[　\s]*$')


def split_text_into_chapters(text: str) -> List[Dict[str, str]]:
    """将文本按章节标题拆分为多段，返回 [{title, content}, ...]"""
    lines = text.split('\n')
    segments = []  # [(title, start_line_idx)]
    current_title = None
    current_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 检查是否匹配章节标题模式
        is_chapter_start = False
        title = stripped
        
        if _CHAPTER_NUM_RE.match(stripped):
            is_chapter_start = True
        else:
            num_match = _CHINESE_NUM_RE.match(stripped)
            if num_match and 1 <= len(num_match.group(1)) <= 4:
                # 裸中文数字：检查下一行是否有更多内容（避免误匹配正文中的数字）
                is_chapter_start = True
                title = num_match.group(1)

        if is_chapter_start:
            # 保存前一段
            if current_title is not None:
                content = '\n'.join(lines[current_start:i]).strip()
                if content and len(content) > 10:
                    segments.append({"title": current_title, "content": content})
            elif i > current_start:
                # 第一章之前的内容作为前言
                preamble = '\n'.join(lines[current_start:i]).strip()
                if preamble and len(preamble) > 10:
                    segments.append({"title": "前言", "content": preamble})
            
            current_title = title
            current_start = i + 1

    # 最后一段
    if current_title is not None:
        content = '\n'.join(lines[current_start:]).strip()
        if content and len(content) > 10:
            segments.append({"title": current_title, "content": content})

    return segments


# 圆圈数字注解正则
_CIRCLED_RE = re.compile(r'[①②③④⑤⑥⑦⑧⑨⑩]')

# TTS 不友好的符号，替换为空格
_TTS_NONSPEECH_RE = re.compile(r'[《》〈〉「」『』【】〖〗♦●◆◇★☆○●◎◇◆□■△▲▽▼※→←↑↓↔↕♠♣♥♦♪♫]')

_MULTI_BLANK_RE = re.compile(r'\n{3,}')


def sanitize_text(text: str) -> str:
    """清理 TTS 不适用的符号，规范化空白，移除纯装饰行"""
    text = _TTS_NONSPEECH_RE.sub(' ', text)
    text = _MULTI_BLANK_RE.sub('\n\n', text)
    # 移除纯装饰行：不含任何可读内容（中文、英文字母、数字）
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 至少包含一些可读内容
        if re.search(r'[\u4e00-\u9fff]|[a-zA-Z]|\d', stripped):
            cleaned.append(line)
    text = '\n'.join(cleaned)
    text = text.strip()
    return text


def inline_annotations(text: str) -> str:
    """
    将文中的圆圈数字注解 (①, ②, ...) 替换为内联格式 (注: xxx)。
    注解行从正文中移除。
    """
    if not _CIRCLED_RE.search(text):
        return text
    
    # 1. 提取所有注解正文（行首圆圈数字后的内容）
    annot_texts = []
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', stripped):
            # 去掉行首的圆圈数字，保留注解正文
            annot_text = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', stripped)
            annot_texts.append(annot_text)
            # 注解行不加入正文
        else:
            clean_lines.append(line)
    
    if not annot_texts:
        return text
    
    clean_text = '\n'.join(clean_lines)
    
    # 2. 找到所有内联引用标记（不在行首的圆圈数字）
    inline_positions = []
    for m in _CIRCLED_RE.finditer(clean_text):
        # 确保不是行首（行首的是注解标题，已被移除）
        if m.start() > 0 and clean_text[m.start()-1] != '\n':
            inline_positions.append(m.start())
    
    if not inline_positions:
        return clean_text
    
    # 3. 按位置倒序替换，避免位置偏移
    result = list(clean_text)
    for i, pos in enumerate(reversed(inline_positions)):
        annot_idx = len(inline_positions) - 1 - i
        if annot_idx < len(annot_texts):
            replacement = f"(注: {annot_texts[annot_idx]})"
            result[pos:pos+1] = list(replacement)
    
    return ''.join(result)


def split_soup_into_chapters(soup, fallback_title: str = "Chapter") -> List[Dict[str, str]]:
    """从 BeautifulSoup HTML 中按章节标记拆分。在文本拆分基础上，额外检测空的 <p>数字</p> 标题。"""
    from bs4 import BeautifulSoup, Tag, NavigableString
    
    # 先尝试 HTML 级别拆分：检测 <p>裸数字</p> 和 <h1>-<h6> 标题
    body = soup.find("body") or soup
    sections = []  # [(title_node, content_start_node)]
    current_title = fallback_title
    content_nodes = []
    found_headings = False
    
    head_tag = soup.find("head")
    if head_tag:
        head_tag.decompose()
    
    for element in body.find_all(True, recursive=False):
        if element.name in ("head", "title", "meta", "link", "style", "script"):
            continue
        
        tag_text = element.get_text(strip=True)
        is_heading = False
        
        if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            is_heading = _CHAPTER_NUM_RE.match(tag_text) is not None
        elif len(tag_text) <= 4:
            num_match = _CHINESE_NUM_RE.match(tag_text)
            if num_match and 1 <= len(num_match.group(1)) <= 4:
                is_heading = True
        
        if is_heading:
            if content_nodes:
                full_text = "\n".join(
                    n.get_text(separator="\n", strip=True) if isinstance(n, Tag) else str(n).strip()
                    for n in content_nodes
                ).strip()
                if full_text and len(full_text) > 10:
                    sections.append({"title": current_title, "content": full_text})
                content_nodes = []
            current_title = tag_text
            found_headings = True
            continue
        
        content_nodes.append(element)
    
    # 最后一段
    if content_nodes:
        full_text = "\n".join(
            n.get_text(separator="\n", strip=True) if isinstance(n, Tag) else str(n).strip()
            for n in content_nodes
        ).strip()
        if full_text and len(full_text) > 10:
            sections.append({"title": current_title, "content": full_text})
    
    if found_headings and len(sections) > 1:
        return sections
    
    # HTML 级别未找到足够的标题，回退到文本级别拆分
    text = body.get_text(separator="\n", strip=True)
    return split_text_into_chapters(text)


_GENERIC_TITLES = {"正文", "正文", "Chapter", "无标题", "Untitled"}


def _get_chapter_title(soup, chapter_num: int) -> str:
    """从 BeautifulSoup 中提取章节标题"""
    title_tag = soup.find(["h1", "h2", "h3"])
    if title_tag:
        return title_tag.get_text(strip=True)
    html_title_tag = soup.find("title")
    if html_title_tag and html_title_tag.string:
        t = html_title_tag.string.strip()
        if t not in _GENERIC_TITLES:
            return t

    # 从正文首行提取标题（不修改 soup）
    body = soup.find("body")
    if body:
        first_tag = body.find(True, recursive=False)
        if first_tag and first_tag.name not in ("meta", "link", "style", "script"):
            # 取前 5 行，找到第一个匹配章标题模式的行
            lines = first_tag.get_text(separator="\n", strip=True).split("\n")
            for line in lines[:5]:
                line = line.strip()
                if 3 < len(line) < 100 and (
                    re.search(r'\d+\.', line) or
                    _CHAPTER_NUM_RE.match(line) or
                    re.search(r'[第序前后附录楔引尾终]', line)
                ):
                    return line

    return f"Chapter {chapter_num + 1}"


class EpubParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Dict[str, Any]:
        from bs4 import BeautifulSoup

        with zipfile.ZipFile(self.file_path, "r") as epub_zip:
            # Find OPF file path
            container = epub_zip.read("META-INF/container.xml").decode("utf-8")
            container_root = ET.fromstring(container)
            opf_path = container_root.find(
                ".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"
            ).get("full-path")
            opf_dir = str(Path(opf_path).parent)

            # Read OPF file
            opf_content = epub_zip.read(opf_path).decode("utf-8")
            opf_root = ET.fromstring(opf_content)

            # Extract metadata
            title_elem = opf_root.find(
                ".//{http://purl.org/dc/elements/1.1/}title"
            )
            author_elem = opf_root.find(
                ".//{http://purl.org/dc/elements/1.1/}creator"
            )

            title = title_elem.text if title_elem is not None else Path(self.file_path).stem
            author = author_elem.text if author_elem is not None else None

            # Build manifest (id -> href)
            manifest = {}
            manifest_elem = opf_root.find("manifest")
            if manifest_elem is None:
                # Try with namespace
                manifest_elem = opf_root.find(
                    "{http://www.idpf.org/2007/opf}manifest"
                )
            if manifest_elem is not None:
                for item in manifest_elem.findall("item") or manifest_elem.findall(
                    "{http://www.idpf.org/2007/opf}item"
                ):
                    item_id = item.get("id")
                    href = item.get("href")
                    if item_id and href:
                        manifest[item_id] = href

            # Get reading order from spine
            spine_ids = []
            spine_elem = opf_root.find("spine")
            if spine_elem is None:
                spine_elem = opf_root.find(
                    "{http://www.idpf.org/2007/opf}spine"
                )
            if spine_elem is not None:
                for itemref in spine_elem.findall("itemref") or spine_elem.findall(
                    "{http://www.idpf.org/2007/opf}itemref"
                ):
                    idref = itemref.get("idref")
                    if idref:
                        spine_ids.append(idref)

            # Parse chapters
            chapters = []
            chapter_num = 0

            if spine_ids:
                # Use spine order
                for idref in spine_ids:
                    if idref not in manifest:
                        continue
                    href = manifest[idref]
                    file_path = (
                        href
                        if opf_dir == "."
                        else f"{opf_dir}/{href}"
                    )
                    if file_path not in epub_zip.namelist():
                        continue

                    content = epub_zip.read(file_path).decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(content, "html.parser")

                    # Skip cover and nav pages
                    if idref in ("cover", "coverpage", "nav", "toc"):
                        continue

                    chapter_title = _get_chapter_title(soup, chapter_num)
                    head_tag = soup.find("head")
                    if head_tag:
                        head_tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    
                    # 如果 spine 文件总数很少（<=3），且单个文件文本 >100KB，尝试文本级拆分
                    if len(spine_ids) <= 3 and len(text) > 100000:
                        sub_chapters = split_soup_into_chapters(soup, chapter_title)
                        if len(sub_chapters) > 1:
                            for sc in sub_chapters:
                                chapter_num += 1
                                chapters.append({
                                    "chapter_number": chapter_num,
                                    "title": sc["title"],
                                    "text_content": sc["content"],
                                    "word_count": len(sc["content"]),
                                })
                            continue

                    if text and len(text) > 10:
                        chapter_num += 1
                        chapters.append({
                            "chapter_number": chapter_num,
                            "title": chapter_title,
                            "text_content": text,
                            "word_count": len(text),
                        })
            else:
                # Fallback: iterate all document items
                for name in epub_zip.namelist():
                    if not name.endswith((".html", ".xhtml")):
                        continue
                    if name.endswith("nav.xhtml"):
                        continue

                    content = epub_zip.read(name).decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(content, "html.parser")

                    chapter_title = _get_chapter_title(soup, chapter_num)
                    head_tag = soup.find("head")
                    if head_tag:
                        head_tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)

                    # 如果单个文件特别大（>100KB文本），尝试文本级拆分
                    if len(text) > 100000:
                        sub_chapters = split_soup_into_chapters(soup, chapter_title)
                        if len(sub_chapters) > 1:
                            for sc in sub_chapters:
                                chapter_num += 1
                                chapters.append({
                                    "chapter_number": chapter_num,
                                    "title": sc["title"],
                                    "text_content": sc["content"],
                                    "word_count": len(sc["content"]),
                                })
                            continue

                    if text and len(text) > 10:
                        chapter_num += 1
                        chapters.append({
                            "chapter_number": chapter_num,
                            "title": chapter_title,
                            "text_content": text,
                            "word_count": len(text),
                        })

        # 处理圆圈数字注解内联 + TTS 符号清理
        for ch in chapters:
            ch["text_content"] = sanitize_text(inline_annotations(ch["text_content"]))
            ch["word_count"] = len(ch["text_content"])

        return {
            "title": title,
            "author": author,
            "format": "epub",
            "chapters": chapters,
        }


class PdfParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Dict[str, Any]:
        import fitz

        doc = fitz.open(self.file_path)
        title = Path(self.file_path).stem

        chapters = []
        chapter_num = 0
        current_text = []
        current_title = None

        for page in doc:
            text = page.get_text()
            lines = text.split("\n")

            for line in lines:
                if re.match(r"^(第.{1,5}[章节篇]|Chapter\s+\d+)", line, re.IGNORECASE):
                    if current_text:
                        chapter_num += 1
                        chapters.append({
                            "chapter_number": chapter_num,
                            "title": current_title or f"Chapter {chapter_num}",
                            "text_content": "\n".join(current_text),
                            "word_count": sum(len(t) for t in current_text),
                        })
                        current_text = []
                    current_title = line.strip()
                else:
                    current_text.append(line)

        if current_text:
            chapter_num += 1
            chapters.append({
                "chapter_number": chapter_num,
                "title": current_title or f"Chapter {chapter_num}",
                "text_content": "\n".join(current_text),
                "word_count": sum(len(t) for t in current_text),
            })

        if not chapters:
            full_text = "\n".join(page.get_text() for page in doc)
            chapters.append({
                "chapter_number": 1,
                "title": title,
                "text_content": full_text,
                "word_count": len(full_text),
            })

        doc.close()

        return {
            "title": title,
            "author": None,
            "format": "pdf",
            "chapters": chapters,
        }


class TxtParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Dict[str, Any]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        title = Path(self.file_path).stem
        pattern = r"^\s*((?:第.{1,10}[章节篇]).*|(?:Chapter\s+\d+).*)\s*$"
        lines = content.split("\n")

        chapters = []
        current_chapter = None
        current_text = []

        for line in lines:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                if current_chapter or current_text:
                    text = "\n".join(current_text).strip()
                    if text:
                        chapters.append({
                            "chapter_number": len(chapters) + 1,
                            "title": current_chapter or f"Chapter {len(chapters) + 1}",
                            "text_content": text,
                            "word_count": len(text),
                        })
                current_chapter = match.group(1).strip()
                current_text = []
            else:
                current_text.append(line)

        if current_text or current_chapter:
            text = "\n".join(current_text).strip()
            if text:
                chapters.append({
                    "chapter_number": len(chapters) + 1,
                    "title": current_chapter or f"Chapter {len(chapters) + 1}",
                    "text_content": text,
                    "word_count": len(text),
                })

        if not chapters:
            chapters.append({
                "chapter_number": 1,
                "title": title,
                "text_content": content,
                "word_count": len(content),
            })

        return {
            "title": title,
            "author": None,
            "format": "txt",
            "chapters": chapters,
        }


class MobiParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Dict[str, Any]:
        import mobi
        import shutil
        import os

        tempdir, filepath = mobi.extract(self.file_path)
        try:
            # 优先使用 mobi7 HTML 解析（章节分割更精确）
            html_path = os.path.join(tempdir, "mobi7", "book.html")
            if os.path.exists(html_path):
                return self._parse_html(html_path)

            ext = Path(filepath).suffix.lower()
            if ext == ".epub":
                return EpubParser(filepath).parse()
            elif ext in (".html", ".xhtml", ".htm"):
                return self._parse_html(filepath)
            elif ext == ".pdf":
                return PdfParser(filepath).parse()
            else:
                raise ValueError(f"Unsupported extracted format: {ext}")
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

    def _parse_html(self, html_path: str) -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        import re

        title = Path(self.file_path).stem

        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # 尝试从 title 标签获取书名
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()

        # 尝试获取作者
        author = None
        author_tag = soup.find("meta", attrs={"name": "author"})
        if author_tag:
            author = author_tag.get("content")

        # 章节标题模式：包括 "第X章"、"序"、"-1-" 等数字标记
        chapter_pattern = re.compile(
            r'(?x)^(第.{1,12}?[章节篇卷](?:\s+|$)|序|前言|后记|附录|目录|楔子|引子|尾声|-\d{1,3}-)'
        )

        # 按章节分割 - 先尝试 p 标签，不足时回退到 h1-h3
        for attempt_tags in (["p"], ["h1", "h2", "h3", "p"]):
            chapters = []
            current_chapter = None
            current_text = []

            for elem in soup.find_all(attempt_tags):
                text = elem.get_text(strip=True)
                if not text:
                    continue

                # 章节边界：h1-h3 标签 或 p 标签匹配章节模式
                is_chapter_boundary = bool(chapter_pattern.match(text))
                if not is_chapter_boundary and elem.name in ("h1", "h2", "h3"):
                    is_chapter_boundary = True

                if is_chapter_boundary:
                    if current_text:
                        content = "\n".join(current_text).strip()
                        if content and len(content) > 10:
                            chapters.append({
                                "chapter_number": len(chapters) + 1,
                                "title": current_chapter or f"Chapter {len(chapters) + 1}",
                                "text_content": content,
                                "word_count": len(content),
                            })
                        current_text = []
                    current_chapter = text
                else:
                    current_text.append(text)

            # 保存最后一章
            if current_text:
                content = "\n".join(current_text).strip()
                if content and len(content) > 10:
                    chapters.append({
                        "chapter_number": len(chapters) + 1,
                        "title": current_chapter or f"Chapter {len(chapters) + 1}",
                        "text_content": content,
                        "word_count": len(content),
                    })

            if len(chapters) > 3:  # 找到了足够的章节，退出
                break

        # 如果没有按标题分割成功，尝试按段落分割
        if not chapters:
            full_text = soup.get_text(separator="\n", strip=True)
            if full_text:
                chapters.append({
                    "chapter_number": 1,
                    "title": title,
                    "text_content": full_text,
                    "word_count": len(full_text),
                })

        # 处理圆圈数字注解内联 + TTS 符号清理
        for ch in chapters:
            ch["text_content"] = sanitize_text(inline_annotations(ch["text_content"]))
            ch["word_count"] = len(ch["text_content"])

        return {
            "title": title,
            "author": author,
            "format": "mobi",
            "chapters": chapters,
        }


def get_parser(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".epub":
        return EpubParser(file_path)
    elif ext == ".pdf":
        return PdfParser(file_path)
    elif ext == ".txt":
        return TxtParser(file_path)
    elif ext == ".mobi":
        return MobiParser(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
