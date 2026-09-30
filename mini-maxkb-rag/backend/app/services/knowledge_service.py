"""
知识库服务。

Knowledge 是整个 RAG 链路的顶层容器。
先有 Knowledge，后面上传的 Document、切出来的 Paragraph、写入的 Embedding
都要归属到某一个 knowledge_id。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KnowledgeModel, default_retrieval_config
from app.repositories.knowledge_repository import (
    add_knowledge,
    get_knowledge_by_id,
    list_all_knowledges,
)
from app.schemas import KnowledgeCreate, KnowledgeMove, RetrievalConfigUpdate
from app.services.knowledge_folder_service import (
    KnowledgeFolderNotFoundError,
    get_knowledge_folder,
)


class KnowledgeNotFoundError(LookupError):
    """
    表示知识库 ID 不存在。
    """


def create_knowledge(db: Session, payload: KnowledgeCreate) -> KnowledgeModel:
    """
    创建知识库。

    这里只保存最基础的 name/description/folder_id。
    MaxKB 里的 workspace、scope、embedding_model 等字段会在后续阶段补齐。
    """

    if payload.folder_id is not None:
        folder = get_knowledge_folder(db, payload.folder_id)
        if folder is None:
            raise KnowledgeFolderNotFoundError("文件夹不存在")

    knowledge = KnowledgeModel(
        name=payload.name,
        description=payload.description,
        folder_id=payload.folder_id,
    )
    add_knowledge(db, knowledge)
    db.commit()
    db.refresh(knowledge)
    return knowledge


def list_knowledges(db: Session) -> list[KnowledgeModel]:
    """
    查询所有知识库。

    第一版是单用户学习项目，不做 workspace/user 过滤。
    后续做权限时，这里会增加 workspace_id 或 user_id 条件。
    """

    return list_all_knowledges(db)


def get_knowledge(db: Session, knowledge_id: str) -> KnowledgeModel | None:
    """
    根据 ID 查询知识库。
    """

    return get_knowledge_by_id(db, knowledge_id)


def move_knowledge(
    db: Session,
    knowledge_id: str,
    payload: KnowledgeMove,
) -> KnowledgeModel:
    """
    把知识库移动到目标文件夹，或移回根级。

    folder_id 不做 trim 等隐式转换，API 传入的 ID 必须精确匹配数据库记录。
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise KnowledgeNotFoundError("知识库不存在")

    if payload.folder_id is not None:
        folder = get_knowledge_folder(db, payload.folder_id)
        if folder is None:
            raise KnowledgeFolderNotFoundError("文件夹不存在")

    knowledge.folder_id = payload.folder_id
    db.commit()
    db.refresh(knowledge)
    return knowledge


def update_retrieval_config(
    db: Session,
    knowledge_id: str,
    payload: RetrievalConfigUpdate,
) -> KnowledgeModel:
    """
    局部更新知识库检索参数。

    JSON 字段整体赋一个新 dict，确保 SQLAlchemy 能检测到变更；不要原地修改
    knowledge.retrieval_config，否则普通 JSON 类型不会自动追踪内部键变化。
    """

    knowledge = get_knowledge(db, knowledge_id)
    if knowledge is None:
        raise KnowledgeNotFoundError("知识库不存在")

    config = default_retrieval_config()
    if isinstance(knowledge.retrieval_config, dict):
        config.update(knowledge.retrieval_config)
    config.update(payload.model_dump(exclude_unset=True, exclude_none=True))
    knowledge.retrieval_config = config

    db.commit()
    db.refresh(knowledge)
    return knowledge
