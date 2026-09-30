"""v0.5 PostgreSQL and pgvector schema

Revision ID: 0001_v05
Revises:
"""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_v05"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    创建 v0.5 的 PostgreSQL 基线结构。

    该版本一次建立知识库、目录、文件、段落、问题映射和 pgvector 向量表，
    同时为全文检索创建 GIN 索引、为余弦检索创建 HNSW 索引。它是 PostgreSQL
    新环境的首个版本，不负责迁移 SQLite 数据。
    """

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_folder",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_folder.id"]),
    )
    op.create_index("ix_knowledge_folder_name", "knowledge_folder", ["name"])
    op.create_index(
        "ix_knowledge_folder_parent_id",
        "knowledge_folder",
        ["parent_id"],
    )

    op.create_table(
        "knowledge",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("folder_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("retrieval_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["knowledge_folder.id"]),
    )
    op.create_index("ix_knowledge_folder_id", "knowledge", ["folder_id"])
    op.create_index("ix_knowledge_name", "knowledge", ["name"])

    op.create_table(
        "file",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_file_file_name", "file", ["file_name"])

    op.create_table(
        "document",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_file_id", sa.String(64), nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("char_length", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["file.id"]),
    )
    op.create_index("ix_document_knowledge_id", "document", ["knowledge_id"])
    op.create_index("ix_document_name", "document", ["name"])
    op.create_index("ix_document_source_file_id", "document", ["source_file_id"])

    search_expression = (
        "setweight(to_tsvector('simple'::regconfig, coalesce(title, '')), 'A') "
        "|| setweight(to_tsvector('simple'::regconfig, content), 'B')"
    )
    op.create_table(
        "paragraph",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("chunk_length", sa.Integer(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(search_expression, persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
    )
    op.create_index("ix_paragraph_knowledge_id", "paragraph", ["knowledge_id"])
    op.create_index("ix_paragraph_document_id", "paragraph", ["document_id"])
    op.create_index("ix_paragraph_position", "paragraph", ["position"])
    op.create_index(
        "ix_paragraph_search_vector",
        "paragraph",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "problem",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_id", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"]),
    )
    op.create_index("ix_problem_knowledge_id", "problem", ["knowledge_id"])

    op.create_table(
        "problem_paragraph_mapping",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("problem_id", sa.String(64), nullable=False),
        sa.Column("paragraph_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.ForeignKeyConstraint(["problem_id"], ["problem.id"]),
        sa.ForeignKeyConstraint(["paragraph_id"], ["paragraph.id"]),
    )
    for column_name in ("knowledge_id", "document_id", "problem_id", "paragraph_id"):
        op.create_index(
            f"ix_problem_paragraph_mapping_{column_name}",
            "problem_paragraph_mapping",
            [column_name],
        )

    op.create_table(
        "embedding_ref",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("knowledge_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("paragraph_id", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("problem_id", sa.String(64), nullable=True),
        sa.Column("score_meta", sa.JSON(), nullable=False),
        sa.Column("vector_id", sa.String(128), nullable=False),
        sa.Column("embedding", Vector(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.ForeignKeyConstraint(["paragraph_id"], ["paragraph.id"]),
        sa.ForeignKeyConstraint(["problem_id"], ["problem.id"]),
        sa.UniqueConstraint("problem_id"),
        sa.UniqueConstraint("vector_id"),
    )
    for column_name in (
        "knowledge_id",
        "document_id",
        "paragraph_id",
        "source_type",
        "problem_id",
        "vector_id",
    ):
        op.create_index(
            f"ix_embedding_ref_{column_name}",
            "embedding_ref",
            [column_name],
        )
    op.create_index(
        "ix_embedding_ref_embedding_hnsw",
        "embedding_ref",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_where=sa.text("embedding IS NOT NULL"),
    )


def downgrade() -> None:
    """
    按外键依赖的逆序删除 v0.5 全部业务表。

    这是破坏性回滚，会删除关系数据和 pgvector 向量；vector 扩展本身保留，
    避免影响同一数据库中的其他 schema。
    """

    op.drop_table("embedding_ref")
    op.drop_table("problem_paragraph_mapping")
    op.drop_table("problem")
    op.drop_table("paragraph")
    op.drop_table("document")
    op.drop_table("file")
    op.drop_table("knowledge")
    op.drop_table("knowledge_folder")
