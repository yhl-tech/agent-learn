"""
原始文件存储。

MaxKB 源码里 File 模型把文件压缩后写入 PostgreSQL Large Object。
学习项目先用本地磁盘保存文件，逻辑更直观：

上传文件 -> 保存到 backend/data/files/{knowledge_id}/ -> FileModel 记录元数据
"""

import hashlib
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


def calculate_file_sha256(path: Path) -> str:
    """
    以流式方式计算文件 SHA-256。

    即使后续放开大文件上传，也不会为了计算摘要一次性把整个文件再次读入内存。
    摘要当前用于展示和一致性检查，暂不把相同摘要自动合并为同一个 File。
    """

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def resolve_stored_file_path(file_path: str) -> Path:
    """
    将数据库中的文件路径解析为经过边界校验的绝对路径。

    删除服务会在操作数据库和向量库之前先调用它。这样路径数据异常时可以
    立即终止，不会出现业务记录已经删除、最后才发现文件路径非法的情况。
    """

    files_root = FILES_DIR.resolve()
    target_path = Path(file_path).resolve()

    if target_path == files_root or files_root not in target_path.parents:
        raise ValueError("文档文件路径不在允许的存储目录内")

    return target_path


def delete_stored_file(file_path: str) -> None:
    """
    删除由本项目保存的原始文件。

    数据库中的 file_path 属于持久化数据，不能未经校验就直接传给 unlink。
    resolve 后再次确认目标位于 FILES_DIR 内，可以避免错误数据导致删除项目外文件。
    文件已经不存在时按删除成功处理，使删除接口具备幂等清理能力。
    """

    target_path = resolve_stored_file_path(file_path)
    target_path.unlink(missing_ok=True)

    # 每个知识库使用独立目录。文件删除后仅尝试清理空目录；
    # 目录里仍有其他文档时 rmdir 会失败，此时保留目录即可。
    try:
        target_path.parent.rmdir()
    except OSError:
        pass
