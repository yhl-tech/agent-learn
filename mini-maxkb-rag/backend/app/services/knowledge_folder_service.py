"""
知识库文件夹服务。

文件夹采用邻接表模型：每条记录只保存直接父节点 parent_id。
这种结构写入简单，适合 SQLite；读取树时一次查出全部目录，再在内存中组装，
避免递归查询产生 N+1 问题。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import KnowledgeFolderModel, KnowledgeModel
from app.schemas import (
    KnowledgeFolderCreate,
    KnowledgeFolderRead,
    KnowledgeFolderUpdate,
)


class KnowledgeFolderNotFoundError(LookupError):
    """
    表示目标文件夹不存在。
    """


class KnowledgeFolderConflictError(RuntimeError):
    """
    表示当前目录状态不允许执行操作，例如删除非空目录。
    """


class KnowledgeFolderValidationError(ValueError):
    """
    表示目录层级或名称不符合约束。
    """


def get_knowledge_folder(
    db: Session,
    folder_id: str,
) -> KnowledgeFolderModel | None:
    """
    根据 ID 查询文件夹。
    """

    return db.get(KnowledgeFolderModel, folder_id)


def create_knowledge_folder(
    db: Session,
    payload: KnowledgeFolderCreate,
) -> KnowledgeFolderModel:
    """
    创建根文件夹或子文件夹。

    同级目录不允许重名。这里在 service 层校验，是因为 SQLite 的唯一索引
    对 NULL parent_id 的根目录不能提供符合预期的唯一性语义。
    """

    _validate_name(payload.name)
    _require_parent(db, payload.parent_id)
    _ensure_sibling_name_available(
        db,
        name=payload.name,
        parent_id=payload.parent_id,
    )

    folder = KnowledgeFolderModel(
        name=payload.name,
        description=payload.description,
        parent_id=payload.parent_id,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def list_knowledge_folder_tree(db: Session) -> list[KnowledgeFolderRead]:
    """
    返回完整文件夹树。

    查询只执行一次。随后用 id -> 节点映射把每个节点挂到父节点 children；
    即使旧数据中出现孤儿 parent_id，也会把该节点作为根节点返回，避免它在
    管理界面中完全不可见。
    """

    folders = list(
        db.scalars(
            select(KnowledgeFolderModel).order_by(
                KnowledgeFolderModel.created_at.asc(),
                KnowledgeFolderModel.name.asc(),
            )
        ).all()
    )
    # 显式构造节点并把 children 初始化为空，不能直接 model_validate(folder)：
    # SQLAlchemy relationship 也叫 children，Pydantic 会先读取 ORM 子节点，
    # 后面的组树逻辑再 append 一次就会产生重复数据。
    nodes = {
        folder.id: KnowledgeFolderRead(
            id=folder.id,
            name=folder.name,
            description=folder.description,
            parent_id=folder.parent_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            children=[],
        )
        for folder in folders
    }
    roots: list[KnowledgeFolderRead] = []

    for folder in folders:
        node = nodes[folder.id]
        parent = nodes.get(folder.parent_id) if folder.parent_id else None
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)

    return roots


def update_knowledge_folder(
    db: Session,
    folder_id: str,
    payload: KnowledgeFolderUpdate,
) -> KnowledgeFolderModel:
    """
    修改文件夹名称、描述或父目录。

    移动目录前会沿目标父目录持续向上查找。如果途中遇到当前目录，说明移动后
    会产生循环引用，必须在写库前拒绝。
    """

    folder = get_knowledge_folder(db, folder_id)
    if folder is None:
        raise KnowledgeFolderNotFoundError("文件夹不存在")

    next_parent_id = folder.parent_id
    if "parent_id" in payload.model_fields_set:
        next_parent_id = payload.parent_id
        _validate_parent_chain(
            db,
            folder_id=folder.id,
            parent_id=next_parent_id,
        )

    next_name = folder.name
    if "name" in payload.model_fields_set:
        if payload.name is None:
            raise KnowledgeFolderValidationError("文件夹名称不能为空")
        _validate_name(payload.name)
        next_name = payload.name

    if next_name != folder.name or next_parent_id != folder.parent_id:
        _ensure_sibling_name_available(
            db,
            name=next_name,
            parent_id=next_parent_id,
            exclude_folder_id=folder.id,
        )

    folder.name = next_name
    folder.parent_id = next_parent_id
    if "description" in payload.model_fields_set:
        folder.description = payload.description or ""

    db.commit()
    db.refresh(folder)
    return folder


def delete_knowledge_folder(db: Session, folder_id: str) -> None:
    """
    删除空文件夹。

    不做级联删除是刻意的安全边界：目录中存在子目录或知识库时返回冲突，
    调用方必须先显式移动或清理内容。
    """

    folder = get_knowledge_folder(db, folder_id)
    if folder is None:
        raise KnowledgeFolderNotFoundError("文件夹不存在")

    child_count = db.scalar(
        select(func.count(KnowledgeFolderModel.id)).where(
            KnowledgeFolderModel.parent_id == folder_id
        )
    )
    knowledge_count = db.scalar(
        select(func.count(KnowledgeModel.id)).where(
            KnowledgeModel.folder_id == folder_id
        )
    )
    if child_count or knowledge_count:
        raise KnowledgeFolderConflictError("文件夹非空，不能删除")

    db.delete(folder)
    db.commit()


def _validate_name(name: str) -> None:
    """
    拒绝只包含空白字符的目录名。

    Pydantic 的 min_length 只能约束原始字符串长度，不能识别全空格输入。
    """

    if not name.strip():
        raise KnowledgeFolderValidationError("文件夹名称不能为空")


def _require_parent(
    db: Session,
    parent_id: str | None,
) -> KnowledgeFolderModel | None:
    """
    当 parent_id 非空时，确保父目录真实存在。
    """

    if parent_id is None:
        return None

    parent = get_knowledge_folder(db, parent_id)
    if parent is None:
        raise KnowledgeFolderNotFoundError("父文件夹不存在")
    return parent


def _validate_parent_chain(
    db: Session,
    folder_id: str,
    parent_id: str | None,
) -> None:
    """
    校验移动后的父链不会形成循环。

    visited 同时保护已有脏数据：如果数据库里原本就存在不包含当前目录的环，
    检查会稳定失败，而不是无限循环。
    """

    current_id = parent_id
    visited: set[str] = set()
    while current_id is not None:
        if current_id == folder_id:
            raise KnowledgeFolderValidationError("不能把文件夹移动到自身或其子目录")
        if current_id in visited:
            raise KnowledgeFolderValidationError("文件夹层级存在循环引用")
        visited.add(current_id)

        current = _require_parent(db, current_id)
        current_id = current.parent_id


def _ensure_sibling_name_available(
    db: Session,
    name: str,
    parent_id: str | None,
    exclude_folder_id: str | None = None,
) -> None:
    """
    保证同一父目录下名称唯一。
    """

    statement = select(KnowledgeFolderModel.id).where(
        KnowledgeFolderModel.name == name
    )
    if parent_id is None:
        statement = statement.where(KnowledgeFolderModel.parent_id.is_(None))
    else:
        statement = statement.where(KnowledgeFolderModel.parent_id == parent_id)
    if exclude_folder_id is not None:
        statement = statement.where(KnowledgeFolderModel.id != exclude_folder_id)

    if db.scalar(statement) is not None:
        raise KnowledgeFolderConflictError("同级文件夹名称已存在")
