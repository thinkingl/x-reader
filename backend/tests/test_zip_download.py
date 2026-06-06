import io
import zipfile
import pytest
from pathlib import Path

from app.models.database import Book, Chapter


def _create_test_book_with_audio(db, tmp_path):
    """Helper: create a book with 3 fake audio files"""
    book = Book(title="测试有声书", author="测试作者", format="epub", file_path=str(tmp_path / "test.txt"))
    db.add(book)
    db.flush()

    (tmp_path / "test.txt").write_text("ebook content")

    for i in range(1, 4):
        audio_path = tmp_path / f"chapter_{i:03d}.mp3"
        audio_path.write_bytes(b'\x00' * 1000)

        chapter = Chapter(
            book_id=book.id,
            chapter_number=i,
            title=f"第{i}章 测试章节",
            text_content=f"章节{i}内容",
            word_count=100 * i,
            audio_path=str(audio_path),
            status="completed"
        )
        db.add(chapter)

    db.commit()
    return book


def test_download_zip_basic(client, db, tmp_path):
    """测试基本的 zip 下载功能"""
    book = _create_test_book_with_audio(db, tmp_path)

    response = client.get(f"/api/audio/{book.id}/zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, 'r') as zf:
        names = zf.namelist()
        assert len(names) == 4
        # File names are like "001_第1章 测试章节.mp3"
        assert any("test.txt" in n for n in names)
        assert any("001_" in n for n in names)
        assert any("002_" in n for n in names)
        assert any("003_" in n for n in names)

    with zipfile.ZipFile(zip_data, 'r') as zf:
        for name in names:
            data = zf.read(name)
            assert len(data) > 0, f"File {name} is empty"


def test_download_zip_filename_utf8(client, db, tmp_path):
    """测试中文文件名编码"""
    book = _create_test_book_with_audio(db, tmp_path)

    response = client.get(f"/api/audio/{book.id}/zip")
    content_disp = response.headers.get("content-disposition", "")
    assert "filename*=utf-8''" in content_disp
    # URL-encoded Chinese characters
    assert "%E6%B5%8B%E8%AF%95%E6%9C%89%E5%A3%B0%E4%B9%A6" in content_disp


def test_download_zip_no_audio(client, db):
    """测试没有音频文件时返回 404"""
    book = Book(title="无音频书", author="作者", format="epub", file_path="/nonexistent.txt")
    db.add(book)
    db.commit()

    response = client.get(f"/api/audio/{book.id}/zip")
    assert response.status_code == 404


def test_download_zip_nonexistent_book(client):
    """测试不存在的书返回 404"""
    response = client.get("/api/audio/99999/zip")
    assert response.status_code == 404


def test_download_zip_integrity(client, db, tmp_path):
    """测试 zip 文件完整性（可正常解压所有文件）"""
    book = _create_test_book_with_audio(db, tmp_path)

    response = client.get(f"/api/audio/{book.id}/zip")
    assert response.status_code == 200

    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, 'r') as zf:
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        zf.extractall(str(extract_dir))

        extracted_files = list(extract_dir.iterdir())
        assert len(extracted_files) == 4

        for i in range(1, 4):
            orig = tmp_path / f"chapter_{i:03d}.mp3"
            extracted = extract_dir / f"00{i}_第{i}章 测试章节.mp3"
            assert extracted.exists(), f"Missing: {extracted.name}"
            assert extracted.read_bytes() == orig.read_bytes()


def test_download_zip_stored_mode(client, db, tmp_path):
    """测试 zip 使用 ZIP_STORED 模式（不压缩）"""
    book = _create_test_book_with_audio(db, tmp_path)

    response = client.get(f"/api/audio/{book.id}/zip")
    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, 'r') as zf:
        for info in zf.infolist():
            assert info.compress_type == zipfile.ZIP_STORED


def test_download_zip_missing_audio_file(client, db, tmp_path):
    """测试音频文件在磁盘上不存在时跳过该文件"""
    book = _create_test_book_with_audio(db, tmp_path)

    (tmp_path / "chapter_002.mp3").unlink()

    response = client.get(f"/api/audio/{book.id}/zip")
    assert response.status_code == 200

    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, 'r') as zf:
        names = zf.namelist()
        assert len(names) == 3
        assert not any("002_" in n for n in names)


def test_download_zip_ebook_missing(client, db, tmp_path):
    """测试电子书文件不存在时仍能下载音频"""
    book = _create_test_book_with_audio(db, tmp_path)

    (tmp_path / "test.txt").unlink()

    response = client.get(f"/api/audio/{book.id}/zip")
    assert response.status_code == 200

    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data, 'r') as zf:
        names = zf.namelist()
        assert len(names) == 3
