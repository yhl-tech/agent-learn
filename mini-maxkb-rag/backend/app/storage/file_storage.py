"""
原始文件存储。

MaxKB 源码里 File 模型把文件压缩后写入 PostgreSQL Large Object。
学习项目先用本地磁盘保存文件，逻辑更直观：

上传文件 -> 保存到 backend/data/files/{knowledge_id}/ -> Document.file_path 记录路径
"""

from pathlib import Path

from fastapi import UploadFile

from app.config import FILES_DIR
from app.models import new_id


ALLOWED_SUFFIXES = {".txt", ".md"}


def validate_file_name(filename: str) -> None:
    """
    校验上传文件名。

    第一版只支持 txt/md，是为了把注意力放在 RAG 主链路。
    PDF、Word 解析会引入额外依赖和很多边界问题，后续再加。
    """

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_SUFFIXES))
        raise ValueError(f"只支持上传 {allowed} 文件")


async def save_upload_file(knowledge_id: str, upload_file: UploadFile) -> Path:
    """
    保存用户上传的原始文件，并返回保存后的路径。

    文件名前面加一个 uuid，是为了避免同名文件互相覆盖。
    knowledge_id 单独作为目录，是为了让不同知识库的文件天然隔离。
    """

    validate_file_name(upload_file.filename or "")

    knowledge_dir = FILES_DIR / knowledge_id
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(upload_file.filename or "document.txt").name
    target_path = knowledge_dir / f"{new_id()}-{safe_name}"

    content = await upload_file.read()
    target_path.write_bytes(content)

    return target_path


def read_text_file(path: Path) -> str:
    """
    读取 txt/md 文本文件。

    这里优先使用 utf-8。
    如果遇到带 BOM 的 UTF-8，utf-8-sig 可以正确去掉文件开头的 BOM。
    """

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")
