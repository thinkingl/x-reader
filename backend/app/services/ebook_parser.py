import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path


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

                    # 优先从h1/h2/h3获取标题
                    title_tag = soup.find(["h1", "h2", "h3"])
                    if title_tag:
                        chapter_title = title_tag.get_text(strip=True)
                    else:
                        # 尝试从<title>标签获取
                        html_title_tag = soup.find("title")
                        if html_title_tag and html_title_tag.string:
                            chapter_title = html_title_tag.string.strip()
                        else:
                            chapter_title = f"Chapter {chapter_num + 1}"

                    # 提取正文文本，排除<head>中的<title>以避免重复
                    head_tag = soup.find("head")
                    if head_tag:
                        head_tag.decompose()

                    text = soup.get_text(separator="\n", strip=True)

                    if text and len(text) > 10:
                        chapter_num += 1

                        chapters.append(
                            {
                                "chapter_number": chapter_num,
                                "title": chapter_title,
                                "text_content": text,
                                "word_count": len(text),
                            }
                        )
            else:
                # Fallback: iterate all document items
                for name in epub_zip.namelist():
                    if not name.endswith((".html", ".xhtml")):
                        continue
                    if name.endswith("nav.xhtml"):
                        continue

                    content = epub_zip.read(name).decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(content, "html.parser")

                    # 优先从h1/h2/h3获取标题
                    title_tag = soup.find(["h1", "h2", "h3"])
                    if title_tag:
                        chapter_title = title_tag.get_text(strip=True)
                    else:
                        # 尝试从<title>标签获取
                        html_title_tag = soup.find("title")
                        if html_title_tag and html_title_tag.string:
                            chapter_title = html_title_tag.string.strip()
                        else:
                            chapter_title = f"Chapter {chapter_num + 1}"

                    # 提取正文文本，排除<head>中的<title>以避免重复
                    head_tag = soup.find("head")
                    if head_tag:
                        head_tag.decompose()

                    text = soup.get_text(separator="\n", strip=True)

                    if text and len(text) > 10:
                        chapter_num += 1

                        chapters.append(
                            {
                                "chapter_number": chapter_num,
                                "title": chapter_title,
                                "text_content": text,
                                "word_count": len(text),
                            }
                        )

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


def get_parser(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".epub":
        return EpubParser(file_path)
    elif ext == ".pdf":
        return PdfParser(file_path)
    elif ext == ".txt":
        return TxtParser(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
