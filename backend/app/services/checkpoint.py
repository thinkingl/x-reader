"""音频转换断点续传 — 基于独立 SQLite 的 chunk 缓存"""

import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = "data/checkpoints"


def _db_path(task_id: int) -> str:
    return os.path.join(CHECKPOINT_DIR, f"{task_id}.db")


def create(task_id: int, chunks: list) -> bool:
    """创建 checkpoint DB，写入所有 chunk_text"""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    db_path = _db_path(task_id)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS chunks (chunk_index INTEGER PRIMARY KEY, chunk_text TEXT, audio_bytes BLOB)")
        conn.executemany(
            "INSERT OR IGNORE INTO chunks (chunk_index, chunk_text) VALUES (?, ?)",
            [(i, text) for i, text in enumerate(chunks)],
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to create checkpoint DB for task {task_id}: {e}")
        return False


def get_pending_count(task_id: int) -> int:
    """返回尚未转换的 chunk 数量"""
    db_path = _db_path(task_id)
    if not os.path.exists(db_path):
        return -1
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM chunks WHERE audio_bytes IS NULL").fetchone()[0]
    conn.close()
    return count


def get_completed_count(task_id: int) -> int:
    """返回已转换的 chunk 数量"""
    db_path = _db_path(task_id)
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM chunks WHERE audio_bytes IS NOT NULL").fetchone()[0]
    conn.close()
    return count


def save_chunk(task_id: int, chunk_index: int, audio_bytes: bytes):
    """保存单个 chunk 的音频数据"""
    db_path = _db_path(task_id)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE chunks SET audio_bytes = ? WHERE chunk_index = ?", (audio_bytes, chunk_index))
    conn.commit()
    conn.close()


def iter_completed(task_id: int):
    """迭代已完成的 chunk，返回 (chunk_index, audio_bytes)"""
    db_path = _db_path(task_id)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT chunk_index, audio_bytes FROM chunks WHERE audio_bytes IS NOT NULL ORDER BY chunk_index")
    for row in cursor:
        yield row[0], row[1]
    conn.close()


def delete(task_id: int):
    """删除 checkpoint DB"""
    db_path = _db_path(task_id)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError as e:
            logger.warning(f"Failed to delete checkpoint DB for task {task_id}: {e}")


def exists(task_id: int) -> bool:
    return os.path.exists(_db_path(task_id))


def cleanup_orphans(active_task_ids: set):
    """清理没有对应活跃任务的 checkpoint DB"""
    if not os.path.isdir(CHECKPOINT_DIR):
        return
    for fname in os.listdir(CHECKPOINT_DIR):
        if not fname.endswith(".db"):
            continue
        try:
            tid = int(fname.replace(".db", ""))
        except ValueError:
            continue
        if tid not in active_task_ids:
            db_path = os.path.join(CHECKPOINT_DIR, fname)
            try:
                os.remove(db_path)
                logger.info(f"Cleaned orphan checkpoint DB: task {tid}")
            except OSError:
                pass
