"""
学习版数据库兼容迁移。

SQLAlchemy 的 ``Base.metadata.create_all()`` 只会创建不存在的表，不会给已经
存在的表自动增加字段。项目在 v0.5 引入 Alembic 之前，用这个模块处理少量、
可重复执行的 SQLite 字段迁移，避免开发者必须删除现有学习数据。

这里不是通用迁移框架。每一段 SQL 都应保持：
1. 只处理当前版本明确新增的字段。
2. 执行前检查字段是否存在。
3. 重复启动应用时不会重复修改或破坏数据。

当前集中兼容 v0.4-v0.7 的本地 SQLite 演进：FTS5 检索索引、目录与问题增强
结构、持久化任务状态，以及 Celery 所需的 attempt、租约和 Outbox 表。生产
PostgreSQL 不走这条路径，由 Alembic 版本迁移维护。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, inspect, text

from app.config import FILES_DIR, TASK_MAX_ATTEMPTS
from app.models import (
    DOCUMENT_STATUS_SUCCESS,
    EMBEDDING_SOURCE_PARAGRAPH,
    default_retrieval_config,
)


def run_lightweight_migrations(database_engine: Engine) -> None:
    """
    对已有 SQLite 数据库执行幂等的字段补齐。

    新数据库会先由 ``create_all`` 创建完整字段，因此这里不会执行 ALTER TABLE。
    非 SQLite 数据库暂不执行手写 SQL；后续接入 PostgreSQL 时统一交给 Alembic。
    """

    if database_engine.dialect.name != "sqlite":
        return

    # engine.begin() 会在迁移成功时提交，出现异常时自动回滚。
    # 将字段新增和旧数据回填放在同一个连接中，避免连接看到不同的表结构状态。
    with database_engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())

        if "file" not in table_names:
            # 正常启动时 create_all 会先创建该表。这里仍保留 CREATE IF NOT EXISTS，
            # 让迁移函数在独立脚本或迁移测试中调用时也具备完整行为。
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS file (
                        id VARCHAR(64) PRIMARY KEY,
                        file_name VARCHAR(255) NOT NULL,
                        file_size INTEGER NOT NULL DEFAULT 0,
                        sha256_hash VARCHAR(64) NOT NULL DEFAULT '',
                        file_path VARCHAR(1024) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            table_names.add("file")

        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_file_file_name ON file (file_name)")
        )

        if "problem" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS problem (
                        id VARCHAR(64) PRIMARY KEY,
                        knowledge_id VARCHAR(64) NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            table_names.add("problem")

        if "problem_paragraph_mapping" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS problem_paragraph_mapping (
                        id VARCHAR(64) PRIMARY KEY,
                        knowledge_id VARCHAR(64) NOT NULL,
                        document_id VARCHAR(64) NOT NULL,
                        problem_id VARCHAR(64) NOT NULL,
                        paragraph_id VARCHAR(64) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            table_names.add("problem_paragraph_mapping")

        for index_sql in (
            "CREATE INDEX IF NOT EXISTS ix_problem_knowledge_id "
            "ON problem (knowledge_id)",
            "CREATE INDEX IF NOT EXISTS ix_problem_paragraph_mapping_knowledge_id "
            "ON problem_paragraph_mapping (knowledge_id)",
            "CREATE INDEX IF NOT EXISTS ix_problem_paragraph_mapping_document_id "
            "ON problem_paragraph_mapping (document_id)",
            "CREATE INDEX IF NOT EXISTS ix_problem_paragraph_mapping_problem_id "
            "ON problem_paragraph_mapping (problem_id)",
            "CREATE INDEX IF NOT EXISTS ix_problem_paragraph_mapping_paragraph_id "
            "ON problem_paragraph_mapping (paragraph_id)",
        ):
            connection.execute(text(index_sql))

        if "task" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS task (
                        id VARCHAR(64) PRIMARY KEY,
                        type VARCHAR(40) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        document_id VARCHAR(64) NOT NULL,
                        error_message TEXT,
                        error_code VARCHAR(80),
                        started_at DATETIME,
                        finished_at DATETIME,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        attempt_no INTEGER NOT NULL DEFAULT 1,
                        max_attempts INTEGER NOT NULL DEFAULT 3,
                        celery_task_id VARCHAR(64),
                        idempotency_key VARCHAR(160) NOT NULL,
                        worker_id VARCHAR(255),
                        queued_at DATETIME,
                        heartbeat_at DATETIME,
                        lease_expires_at DATETIME,
                        next_retry_at DATETIME,
                        cancel_requested BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(document_id) REFERENCES document (id)
                    )
                    """
                )
            )
            table_names.add("task")

        task_columns = {
            column["name"] for column in inspect(connection).get_columns("task")
        }
        task_column_sql = {
            "error_code": "ALTER TABLE task ADD COLUMN error_code VARCHAR(80)",
            "attempt_no": (
                "ALTER TABLE task ADD COLUMN attempt_no "
                "INTEGER NOT NULL DEFAULT 1"
            ),
            "max_attempts": (
                "ALTER TABLE task ADD COLUMN max_attempts "
                f"INTEGER NOT NULL DEFAULT {TASK_MAX_ATTEMPTS}"
            ),
            "celery_task_id": (
                "ALTER TABLE task ADD COLUMN celery_task_id VARCHAR(64)"
            ),
            "idempotency_key": (
                "ALTER TABLE task ADD COLUMN idempotency_key VARCHAR(160)"
            ),
            "worker_id": "ALTER TABLE task ADD COLUMN worker_id VARCHAR(255)",
            "queued_at": "ALTER TABLE task ADD COLUMN queued_at DATETIME",
            "heartbeat_at": "ALTER TABLE task ADD COLUMN heartbeat_at DATETIME",
            "lease_expires_at": (
                "ALTER TABLE task ADD COLUMN lease_expires_at DATETIME"
            ),
            "next_retry_at": (
                "ALTER TABLE task ADD COLUMN next_retry_at DATETIME"
            ),
        }
        for column_name, column_sql in task_column_sql.items():
            if column_name not in task_columns:
                connection.execute(text(column_sql))

        connection.execute(
            text(
                "UPDATE task SET attempt_no = 1 "
                "WHERE attempt_no IS NULL OR attempt_no < 1"
            )
        )
        connection.execute(
            text(
                "UPDATE task SET max_attempts = :max_attempts "
                "WHERE max_attempts IS NULL OR max_attempts < attempt_no"
            ),
            {"max_attempts": TASK_MAX_ATTEMPTS},
        )
        connection.execute(
            text(
                "UPDATE task SET idempotency_key = 'legacy:' || id "
                "WHERE idempotency_key IS NULL OR idempotency_key = ''"
            )
        )

        for index_sql in (
            "CREATE INDEX IF NOT EXISTS ix_task_type ON task (type)",
            "CREATE INDEX IF NOT EXISTS ix_task_status ON task (status)",
            "CREATE INDEX IF NOT EXISTS ix_task_document_id ON task (document_id)",
            "CREATE INDEX IF NOT EXISTS ix_task_error_code ON task (error_code)",
            "CREATE INDEX IF NOT EXISTS ix_task_celery_task_id "
            "ON task (celery_task_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_task_idempotency_key "
            "ON task (idempotency_key)",
            "CREATE INDEX IF NOT EXISTS ix_task_worker_id ON task (worker_id)",
            "CREATE INDEX IF NOT EXISTS ix_task_lease_expires_at "
            "ON task (lease_expires_at)",
            "CREATE INDEX IF NOT EXISTS ix_task_next_retry_at "
            "ON task (next_retry_at)",
        ):
            connection.execute(text(index_sql))

        if "task_attempt" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS task_attempt (
                        id VARCHAR(64) PRIMARY KEY,
                        task_id VARCHAR(64) NOT NULL,
                        attempt_no INTEGER NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        worker_id VARCHAR(255),
                        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        heartbeat_at DATETIME,
                        finished_at DATETIME,
                        error_code VARCHAR(80),
                        error_message TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_task_attempt_task_id_attempt_no
                            UNIQUE (task_id, attempt_no),
                        FOREIGN KEY(task_id) REFERENCES task (id)
                    )
                    """
                )
            )
            table_names.add("task_attempt")

        if "outbox_event" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS outbox_event (
                        id VARCHAR(64) PRIMARY KEY,
                        event_type VARCHAR(80) NOT NULL,
                        task_id VARCHAR(64) NOT NULL,
                        attempt_no INTEGER NOT NULL,
                        deduplication_key VARCHAR(200) NOT NULL,
                        payload JSON NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        attempts INTEGER NOT NULL DEFAULT 0,
                        available_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        leased_until DATETIME,
                        published_at DATETIME,
                        last_error TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_outbox_event_deduplication_key
                            UNIQUE (deduplication_key),
                        FOREIGN KEY(task_id) REFERENCES task (id)
                    )
                    """
                )
            )
            table_names.add("outbox_event")

        for index_sql in (
            "CREATE INDEX IF NOT EXISTS ix_task_attempt_task_id "
            "ON task_attempt (task_id)",
            "CREATE INDEX IF NOT EXISTS ix_task_attempt_status "
            "ON task_attempt (status)",
            "CREATE INDEX IF NOT EXISTS ix_outbox_event_event_type "
            "ON outbox_event (event_type)",
            "CREATE INDEX IF NOT EXISTS ix_outbox_event_task_id "
            "ON outbox_event (task_id)",
            "CREATE INDEX IF NOT EXISTS ix_outbox_event_status "
            "ON outbox_event (status)",
            "CREATE INDEX IF NOT EXISTS ix_outbox_event_available_at "
            "ON outbox_event (available_at)",
            "CREATE INDEX IF NOT EXISTS ix_outbox_event_leased_until "
            "ON outbox_event (leased_until)",
        ):
            connection.execute(text(index_sql))

        # v0.6 可能在升级时留下尚未执行的 PENDING/RUNNING 任务。为没有任何
        # 对应事件的活动 attempt 回填 Outbox；已有 v0.7 事件的任务保持原样。
        orphaned_tasks = connection.execute(
            text(
                """
                SELECT task.id, task.attempt_no, task.status
                FROM task
                WHERE task.status IN ('PENDING', 'QUEUED', 'RETRYING', 'RUNNING')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM outbox_event
                      WHERE outbox_event.task_id = task.id
                        AND outbox_event.attempt_no = task.attempt_no
                  )
                """
            )
        ).mappings()
        migration_time = datetime.utcnow()
        for task in orphaned_tasks:
            if task["status"] == "RUNNING":
                connection.execute(
                    text(
                        """
                        UPDATE task
                        SET status = 'PENDING',
                            worker_id = NULL,
                            heartbeat_at = NULL,
                            lease_expires_at = NULL
                        WHERE id = :task_id
                        """
                    ),
                    {"task_id": task["id"]},
                )
            event_id = str(uuid.uuid4())
            attempt_no = int(task["attempt_no"])
            connection.execute(
                text(
                    """
                    INSERT INTO outbox_event (
                        id,
                        event_type,
                        task_id,
                        attempt_no,
                        deduplication_key,
                        payload,
                        status,
                        attempts,
                        available_at,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :id,
                        'DOCUMENT_INDEX_REQUESTED',
                        :task_id,
                        :attempt_no,
                        :deduplication_key,
                        :payload,
                        'PENDING',
                        0,
                        :available_at,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                {
                    "id": event_id,
                    "task_id": task["id"],
                    "attempt_no": attempt_no,
                    "deduplication_key": (
                        f"DOCUMENT_INDEX_REQUESTED:{task['id']}:{attempt_no}"
                    ),
                    "payload": json.dumps(
                        {
                            "task_id": task["id"],
                            "attempt_no": attempt_no,
                        }
                    ),
                    "available_at": migration_time,
                    "created_at": migration_time,
                    "updated_at": migration_time,
                },
            )

        if "knowledge" in table_names:
            knowledge_columns = {
                column["name"] for column in inspector.get_columns("knowledge")
            }

            if "folder_id" not in knowledge_columns:
                # SQLite 不能通过简单 ALTER TABLE 给已有列补完整外键约束。
                # 学习版先增加可空关联列，并由 service 校验目录存在；新建数据库
                # 仍会通过 SQLAlchemy metadata 创建真正的 ForeignKey。
                connection.execute(
                    text("ALTER TABLE knowledge ADD COLUMN folder_id VARCHAR(64)")
                )
            if "retrieval_config" not in knowledge_columns:
                connection.execute(
                    text("ALTER TABLE knowledge ADD COLUMN retrieval_config JSON")
                )

            connection.execute(
                text(
                    "UPDATE knowledge SET retrieval_config = :retrieval_config "
                    "WHERE retrieval_config IS NULL OR retrieval_config = ''"
                ),
                {"retrieval_config": json.dumps(default_retrieval_config())},
            )

            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_knowledge_folder_id "
                    "ON knowledge (folder_id)"
                )
            )

        if "document" in table_names:
            document_columns = {column["name"] for column in inspector.get_columns("document")}

            if "source_file_id" not in document_columns:
                connection.execute(
                    text("ALTER TABLE document ADD COLUMN source_file_id VARCHAR(64)")
                )

            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_document_source_file_id "
                    "ON document (source_file_id)"
                )
            )

            # 旧版把文件路径直接存在 document。为每条旧记录补一条 File 元数据，
            # 再回填 source_file_id。路径异常或文件已丢失时仍保留元数据记录，
            # file_size=0、sha256_hash='' 明确表示迁移时无法读取实体文件。
            if "file_path" in document_columns:
                legacy_documents = connection.execute(
                    text(
                        "SELECT id, name, file_path FROM document "
                        "WHERE source_file_id IS NULL "
                        "AND file_path IS NOT NULL AND file_path != ''"
                    )
                ).mappings()
                for document in legacy_documents:
                    source_file_id = str(uuid.uuid4())
                    file_size, sha256_hash = _read_legacy_file_metadata(
                        document["file_path"]
                    )
                    connection.execute(
                        text(
                            """
                            INSERT INTO file (
                                id,
                                file_name,
                                file_size,
                                sha256_hash,
                                file_path,
                                created_at,
                                updated_at
                            )
                            VALUES (
                                :id,
                                :file_name,
                                :file_size,
                                :sha256_hash,
                                :file_path,
                                :created_at,
                                :updated_at
                            )
                            """
                        ),
                        {
                            "id": source_file_id,
                            "file_name": document["name"],
                            "file_size": file_size,
                            "sha256_hash": sha256_hash,
                            "file_path": document["file_path"],
                            # SQLAlchemy 的 Python default 只在 ORM INSERT 时生效。
                            # 迁移使用原始 SQL，必须显式提供两个 NOT NULL 时间列。
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        },
                    )
                    connection.execute(
                        text(
                            "UPDATE document SET source_file_id = :source_file_id "
                            "WHERE id = :document_id"
                        ),
                        {
                            "source_file_id": source_file_id,
                            "document_id": document["id"],
                        },
                    )

            if "status" not in document_columns:
                # 旧文档在新增状态字段前都已经完成同步入库，因此迁移默认视为 SUCCESS。
                connection.execute(
                    text(
                        "ALTER TABLE document "
                        "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'"
                    )
                )

            if "error_message" not in document_columns:
                connection.execute(text("ALTER TABLE document ADD COLUMN error_message TEXT"))

            # 字段可能来自一次未完成的历史迁移，所以仍显式修复空状态。
            connection.execute(
                text(
                    "UPDATE document SET status = :success_status "
                    "WHERE status IS NULL OR status = ''"
                ),
                {"success_status": DOCUMENT_STATUS_SUCCESS},
            )

        if "embedding_ref" in table_names:
            embedding_columns = {
                column["name"] for column in inspector.get_columns("embedding_ref")
            }

            if "source_type" not in embedding_columns:
                connection.execute(
                    text(
                        "ALTER TABLE embedding_ref "
                        "ADD COLUMN source_type VARCHAR(20) NOT NULL "
                        "DEFAULT 'PARAGRAPH'"
                    )
                )
            if "problem_id" not in embedding_columns:
                connection.execute(
                    text("ALTER TABLE embedding_ref ADD COLUMN problem_id VARCHAR(64)")
                )
            if "score_meta" not in embedding_columns:
                connection.execute(
                    text("ALTER TABLE embedding_ref ADD COLUMN score_meta JSON")
                )
            if "embedding" not in embedding_columns:
                # SQLite + Chroma 不读取该列；BLOB 只作为跨数据库模型的可空占位。
                connection.execute(
                    text("ALTER TABLE embedding_ref ADD COLUMN embedding BLOB")
                )

            connection.execute(
                text(
                    "UPDATE embedding_ref SET source_type = :source_type "
                    "WHERE source_type IS NULL OR source_type = ''"
                ),
                {"source_type": EMBEDDING_SOURCE_PARAGRAPH},
            )
            connection.execute(
                text(
                    "UPDATE embedding_ref SET score_meta = '{}' "
                    "WHERE score_meta IS NULL OR score_meta = ''"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_embedding_ref_source_type "
                    "ON embedding_ref (source_type)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_embedding_ref_problem_id "
                    "ON embedding_ref (problem_id) WHERE problem_id IS NOT NULL"
                )
            )

        if "paragraph" in table_names:
            paragraph_columns = {column["name"] for column in inspector.get_columns("paragraph")}

            if "chunk_length" not in paragraph_columns:
                connection.execute(
                    text(
                        "ALTER TABLE paragraph "
                        "ADD COLUMN chunk_length INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "title" not in paragraph_columns:
                connection.execute(
                    text(
                        "ALTER TABLE paragraph "
                        "ADD COLUMN title VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )

            # SQLite 的 length() 按字符计算文本长度，与 Python len(content) 的语义一致。
            # 只回填缺失值，避免覆盖未来可能由其他切分策略记录的有效指标。
            connection.execute(
                text(
                    "UPDATE paragraph SET chunk_length = length(content) "
                    "WHERE chunk_length IS NULL "
                    "OR (chunk_length = 0 AND length(content) > 0)"
                )
            )

        _rebuild_sqlite_fts(connection, table_names)


def _read_legacy_file_metadata(file_path: str) -> tuple[int, str]:
    """
    在迁移旧文档时读取文件大小和 SHA-256。

    只允许读取 FILES_DIR 内的文件。数据库路径如果被意外改到项目外，迁移不会
    跟随它读取任意本地文件，而是返回空元数据并保留路径供后续人工排查。
    """

    files_root = FILES_DIR.resolve()
    path = Path(file_path).resolve()
    if files_root not in path.parents or not path.is_file():
        return 0, ""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return path.stat().st_size, digest.hexdigest()


def _rebuild_sqlite_fts(connection, table_names: set[str]) -> None:
    """
    创建并同步段落全文检索索引。

    FTS5 虚表由 SQLite 管理，SQLAlchemy metadata 不会创建它。触发器保证后续
    ORM 增删改自动同步；启动时全量重建一次，用于覆盖升级前已有段落和异常中断
    造成的索引漂移。学习版数据量较小，这个确定性方案优于维护额外迁移版本。
    """

    if "paragraph" not in table_names:
        return
    paragraph_columns = {
        column["name"] for column in inspect(connection).get_columns("paragraph")
    }
    if not {"id", "knowledge_id", "title", "content"}.issubset(
        paragraph_columns
    ):
        # 极早期或手工裁剪的旧表可能缺少知识库归属，无法构建安全的隔离索引。
        # 保留业务表迁移结果，待表结构修复后下次启动会自动创建 FTS。
        return

    connection.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS paragraph_fts USING fts5(
                paragraph_id UNINDEXED,
                knowledge_id UNINDEXED,
                title,
                content,
                tokenize = 'unicode61'
            )
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS paragraph_fts_insert
            AFTER INSERT ON paragraph
            BEGIN
                INSERT INTO paragraph_fts (
                    paragraph_id,
                    knowledge_id,
                    title,
                    content
                )
                VALUES (new.id, new.knowledge_id, new.title, new.content);
            END
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS paragraph_fts_update
            AFTER UPDATE OF knowledge_id, title, content ON paragraph
            BEGIN
                DELETE FROM paragraph_fts WHERE paragraph_id = old.id;
                INSERT INTO paragraph_fts (
                    paragraph_id,
                    knowledge_id,
                    title,
                    content
                )
                VALUES (new.id, new.knowledge_id, new.title, new.content);
            END
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS paragraph_fts_delete
            AFTER DELETE ON paragraph
            BEGIN
                DELETE FROM paragraph_fts WHERE paragraph_id = old.id;
            END
            """
        )
    )

    connection.execute(text("DELETE FROM paragraph_fts"))
    connection.execute(
        text(
            """
            INSERT INTO paragraph_fts (
                paragraph_id,
                knowledge_id,
                title,
                content
            )
            SELECT id, knowledge_id, title, content FROM paragraph
            """
        )
    )
