"""
v0.4-v0.7 后端集成回归测试。

测试模块在导入应用前设置临时数据目录，确保 SQLite、上传文件和 Chroma
全部写入临时位置，不会污染开发环境中的 backend/data。

覆盖范围包括混合检索、问题增强、目录树、文档状态与补偿、SQLite 轻量迁移，
以及 Outbox 至少一次投递、attempt 幂等、自动重试和取消状态机。
"""

from __future__ import annotations

import os
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


TEST_DATA_DIR = tempfile.TemporaryDirectory()
os.environ["MINI_MAXKB_DATA_DIR"] = TEST_DATA_DIR.name
os.environ["OUTBOX_RELAY_IN_WEB"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text, update

from app.database import SessionLocal, engine
from app.dependencies import get_vector_store
from app.dependencies import get_embedding_service
from app.main import app
from app.migrations import run_lightweight_migrations
from app.models import (
    DOCUMENT_STATUS_CANCELLED,
    DOCUMENT_STATUS_FAILED,
    DOCUMENT_STATUS_SUCCESS,
    EMBEDDING_SOURCE_PARAGRAPH,
    EMBEDDING_SOURCE_PROBLEM,
    OUTBOX_STATUS_DISCARDED,
    OUTBOX_STATUS_PENDING,
    OUTBOX_STATUS_PUBLISHED,
    DocumentModel,
    EmbeddingRefModel,
    FileModel,
    KnowledgeFolderModel,
    ParagraphModel,
    ProblemModel,
    ProblemParagraphMappingModel,
    OutboxEventModel,
    TaskAttemptModel,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RETRYING,
    TASK_STATUS_SUCCESS,
    TaskModel,
)
from app.services.outbox_service import (
    BackgroundTaskPublisher,
    dispatch_outbox_batch,
)
from app.services.task_service import TASK_RUN_IGNORED, run_document_task


def dispatch_document_tasks(vector_store=None) -> int:
    """
    用单机 Publisher 同步跑完当前一批 Outbox 事件，便于测试最终状态。

    生产环境由独立 Relay 和 Celery Worker 分步完成同一流程。
    """

    publisher = BackgroundTaskPublisher(
        embedding_service=get_embedding_service(),
        vector_store=vector_store,
        worker_id="test-worker",
    )
    return dispatch_outbox_batch(publisher=publisher)


class FailingVectorStore:
    """
    用于稳定复现向量写入失败。

    真正的 Chroma 故障依赖外部状态，不适合自动化测试。这个替身只模拟
    add_paragraphs 失败，并记录服务是否调用了 delete_by_document 补偿清理。
    """

    transactional = False

    def __init__(self) -> None:
        self.attempted_vector_ids: list[str] = []
        self.deleted_vector_ids: list[str] = []

    def add_paragraphs(self, **kwargs) -> None:
        self.upsert_paragraphs(**kwargs)

    def upsert_paragraphs(self, **kwargs) -> None:
        self.attempted_vector_ids = list(kwargs["ids"])
        raise RuntimeError("模拟向量写入失败")

    def delete_by_ids(self, db, vector_ids: list[str]) -> None:
        self.deleted_vector_ids.extend(vector_ids)


class PartiallyFailingVectorStore:
    """
    模拟重新索引时“旧向量只删掉一部分就失败”的情况。

    其他操作委托给真实 Chroma，只有第一次删除指定旧向量时主动抛错，
    用于验证补偿逻辑能恢复旧向量并撤销新向量。
    """

    transactional = False

    def __init__(self, delegate, old_vector_ids: list[str]) -> None:
        self.delegate = delegate
        self.old_vector_ids = set(old_vector_ids)
        self.new_vector_ids: list[str] = []
        self.failure_injected = False

    def add_paragraphs(self, **kwargs) -> None:
        self.new_vector_ids = list(kwargs["ids"])
        self.delegate.add_paragraphs(**kwargs)

    def delete_by_ids(self, db, vector_ids: list[str]) -> None:
        if (
            not self.failure_injected
            and vector_ids
            and set(vector_ids) == self.old_vector_ids
        ):
            self.failure_injected = True
            self.delegate.delete_by_ids(db, vector_ids[:1])
            raise RuntimeError("模拟旧向量部分删除失败")
        self.delegate.delete_by_ids(db, vector_ids)

    def upsert_paragraphs(self, **kwargs) -> None:
        if not self.new_vector_ids:
            self.new_vector_ids = list(kwargs["ids"])
        self.delegate.upsert_paragraphs(**kwargs)


class TransientFailingVectorStore:
    """
    每次写入都抛 ConnectionError，用于验证受控自动重试和最大次数。
    """

    transactional = False

    def __init__(self) -> None:
        self.calls = 0

    def upsert_paragraphs(self, **_kwargs) -> None:
        self.calls += 1
        raise ConnectionError("模拟瞬时向量服务故障")

    def delete_by_ids(self, _db, _vector_ids: list[str]) -> None:
        return


class PublishThenFailPublisher:
    """
    模拟消息已送达，但 Relay 在回写 PUBLISHED 前崩溃。
    """

    def __init__(self) -> None:
        self.delegate = BackgroundTaskPublisher(worker_id="publish-before-crash")

    def publish(self, event) -> str:
        self.delegate.publish(event)
        raise ConnectionError("模拟发布成功后的 Relay 崩溃")


class LightweightMigrationTestCase(unittest.TestCase):
    """
    用原始旧版 DDL 验证 v0.4-v0.7 SQLite 迁移、数据回填和重复执行幂等。
    """

    def test_existing_sqlite_tables_are_migrated_and_backfilled(self) -> None:
        old_engine = create_engine("sqlite:///:memory:")
        legacy_file_path = (
            Path(TEST_DATA_DIR.name)
            / "files"
            / "knowledge-1"
            / "legacy.md"
        )
        legacy_file_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_content = "旧文档内容"
        legacy_file_path.write_text(legacy_content, encoding="utf-8")

        # 用原始 SQL 模拟升级前的数据表，确保测试覆盖的是真实旧结构，
        # 而不是已经包含新字段的 SQLAlchemy Model。
        with old_engine.begin() as connection:
            # create_all 新增 File 表时，default=now 属于 ORM 客户端默认值，
            # 数据库列本身没有 DEFAULT。这里按真实 DDL 建表，确保迁移 SQL
            # 必须显式写入 created_at/updated_at。
            connection.execute(
                text(
                    """
                    CREATE TABLE file (
                        id VARCHAR(64) PRIMARY KEY,
                        file_name VARCHAR(255) NOT NULL,
                        file_size INTEGER NOT NULL,
                        sha256_hash VARCHAR(64) NOT NULL,
                        file_path VARCHAR(1024) NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE knowledge (
                        id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(150) NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE embedding_ref (
                        id VARCHAR(64) PRIMARY KEY,
                        paragraph_id VARCHAR(64) NOT NULL,
                        vector_id VARCHAR(128) NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE document (
                        id VARCHAR(64) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        file_path VARCHAR(1024) NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE paragraph (
                        id VARCHAR(64) PRIMARY KEY,
                        content TEXT NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE task (
                        id VARCHAR(64) PRIMARY KEY,
                        type VARCHAR(40) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        document_id VARCHAR(64) NOT NULL,
                        error_message TEXT,
                        started_at DATETIME,
                        finished_at DATETIME,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        cancel_requested BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            connection.execute(
                text("INSERT INTO knowledge (id, name) VALUES ('knowledge-1', '旧知识库')")
            )
            connection.execute(
                text(
                    "INSERT INTO document (id, name, file_path) "
                    "VALUES ('document-1', '旧文档', :file_path)"
                ),
                {"file_path": str(legacy_file_path)},
            )
            connection.execute(
                text("INSERT INTO paragraph (id, content) VALUES ('paragraph-1', '四个字符')")
            )
            connection.execute(
                text(
                    "INSERT INTO embedding_ref (id, paragraph_id, vector_id) "
                    "VALUES ('embedding-1', 'paragraph-1', 'vector-1')"
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO task (
                        id,
                        type,
                        status,
                        document_id
                    )
                    VALUES (
                        'task-1',
                        'DOCUMENT_INDEX',
                        'PENDING',
                        'document-1'
                    )
                    """
                )
            )

        # 连续执行两次用于验证迁移幂等，应用每次启动都可以安全调用。
        run_lightweight_migrations(old_engine)
        run_lightweight_migrations(old_engine)

        inspector = inspect(old_engine)
        knowledge_columns = {
            column["name"] for column in inspector.get_columns("knowledge")
        }
        document_columns = {column["name"] for column in inspector.get_columns("document")}
        paragraph_columns = {column["name"] for column in inspector.get_columns("paragraph")}
        embedding_columns = {
            column["name"] for column in inspector.get_columns("embedding_ref")
        }
        task_columns = {
            column["name"] for column in inspector.get_columns("task")
        }

        self.assertIn("problem", inspector.get_table_names())
        self.assertIn("problem_paragraph_mapping", inspector.get_table_names())
        self.assertIn("task", inspector.get_table_names())
        self.assertIn("task_attempt", inspector.get_table_names())
        self.assertIn("outbox_event", inspector.get_table_names())
        self.assertIn("folder_id", knowledge_columns)
        self.assertIn("retrieval_config", knowledge_columns)
        self.assertIn("source_file_id", document_columns)
        self.assertIn("status", document_columns)
        self.assertIn("error_message", document_columns)
        self.assertIn("chunk_length", paragraph_columns)
        self.assertIn("source_type", embedding_columns)
        self.assertIn("problem_id", embedding_columns)
        self.assertIn("score_meta", embedding_columns)
        self.assertIn("embedding", embedding_columns)
        self.assertIn("title", paragraph_columns)
        self.assertIn("attempt_no", task_columns)
        self.assertIn("max_attempts", task_columns)
        self.assertIn("idempotency_key", task_columns)
        self.assertIn("lease_expires_at", task_columns)

        with old_engine.connect() as connection:
            knowledge_row = connection.execute(
                text(
                    "SELECT folder_id, retrieval_config "
                    "FROM knowledge WHERE id = 'knowledge-1'"
                )
            ).one()
            document_row = connection.execute(
                text(
                    "SELECT status, error_message, source_file_id "
                    "FROM document WHERE id = 'document-1'"
                )
            ).one()
            file_row = connection.execute(
                text(
                    "SELECT file_name, file_size, sha256_hash, file_path "
                    "FROM file WHERE id = :source_file_id"
                ),
                {"source_file_id": document_row.source_file_id},
            ).one()
            file_count = connection.execute(text("SELECT count(*) FROM file")).scalar_one()
            paragraph_row = connection.execute(
                text("SELECT chunk_length FROM paragraph WHERE id = 'paragraph-1'")
            ).one()
            embedding_row = connection.execute(
                text(
                    "SELECT source_type, problem_id, score_meta FROM embedding_ref "
                    "WHERE id = 'embedding-1'"
                )
            ).one()
            task_row = connection.execute(
                text(
                    "SELECT attempt_no, max_attempts, idempotency_key "
                    "FROM task WHERE id = 'task-1'"
                )
            ).one()
            outbox_rows = connection.execute(
                text(
                    "SELECT task_id, attempt_no, status, payload "
                    "FROM outbox_event WHERE task_id = 'task-1'"
                )
            ).all()

        self.assertIsNone(knowledge_row.folder_id)
        self.assertEqual(
            json.loads(knowledge_row.retrieval_config),
            {
                "top_k": 4,
                "score_threshold": 0.0,
                "search_mode": "embedding",
                "blend_weight": 0.5,
            },
        )
        self.assertEqual(document_row.status, DOCUMENT_STATUS_SUCCESS)
        self.assertIsNone(document_row.error_message)
        self.assertIsNotNone(document_row.source_file_id)
        self.assertEqual(file_count, 1)
        self.assertEqual(file_row.file_name, "旧文档")
        self.assertEqual(file_row.file_size, len(legacy_content.encode("utf-8")))
        self.assertEqual(
            file_row.sha256_hash,
            hashlib.sha256(legacy_content.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(file_row.file_path, str(legacy_file_path))
        self.assertEqual(paragraph_row.chunk_length, len("四个字符"))
        self.assertEqual(embedding_row.source_type, EMBEDDING_SOURCE_PARAGRAPH)
        self.assertIsNone(embedding_row.problem_id)
        self.assertEqual(json.loads(embedding_row.score_meta), {})
        self.assertEqual(task_row.attempt_no, 1)
        self.assertEqual(task_row.max_attempts, 3)
        self.assertEqual(task_row.idempotency_key, "legacy:task-1")
        self.assertEqual(len(outbox_rows), 1)
        self.assertEqual(outbox_rows[0].status, OUTBOX_STATUS_PENDING)
        self.assertEqual(json.loads(outbox_rows[0].payload)["attempt_no"], 1)


class TaskDeliveryTestCase(unittest.TestCase):
    """
    覆盖 Outbox 至少一次投递和 Worker attempt 幂等边界。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def _create_pending_task(self, name: str, content: bytes = b"task content") -> dict:
        knowledge_response = self.client.post(
            "/api/knowledges",
            json={"name": name, "description": "v0.7 task delivery"},
        )
        self.assertEqual(knowledge_response.status_code, 200, knowledge_response.text)
        response = self.client.post(
            f"/api/knowledges/{knowledge_response.json()['id']}/documents",
            files={"file": (f"{name}.md", content, "text/markdown")},
        )
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_outbox_recovers_when_publish_fails_after_api_commit(self) -> None:
        document = self._create_pending_task("outbox-recovery")
        task_id = document["task"]["id"]

        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            event = db.scalar(
                select(OutboxEventModel).where(
                    OutboxEventModel.task_id == task_id
                )
            )
            self.assertEqual(task.status, TASK_STATUS_PENDING)
            self.assertEqual(event.status, OUTBOX_STATUS_PENDING)

        with self.assertLogs(
            "app.services.outbox_service",
            level="ERROR",
        ):
            self.assertEqual(
                dispatch_outbox_batch(publisher=PublishThenFailPublisher()),
                1,
            )
        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            event = db.scalar(
                select(OutboxEventModel).where(
                    OutboxEventModel.task_id == task_id
                )
            )
            paragraph_ids = list(
                db.scalars(
                    select(ParagraphModel.id).where(
                        ParagraphModel.document_id == document["id"]
                    )
                ).all()
            )
            self.assertEqual(task.status, TASK_STATUS_SUCCESS)
            self.assertEqual(event.status, OUTBOX_STATUS_PENDING)
            self.assertEqual(event.attempts, 1)
            self.assertIn("模拟发布成功后的 Relay 崩溃", event.last_error)
            db.execute(
                update(OutboxEventModel)
                .where(OutboxEventModel.id == event.id)
                .values(available_at=datetime.utcnow() - timedelta(seconds=1))
            )
            db.commit()

        self.assertEqual(dispatch_document_tasks(), 1)
        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            event = db.scalar(
                select(OutboxEventModel).where(
                    OutboxEventModel.task_id == task_id
                )
            )
            self.assertEqual(task.status, TASK_STATUS_SUCCESS)
            self.assertEqual(event.status, OUTBOX_STATUS_PUBLISHED)
            self.assertEqual(event.attempts, 2)
            self.assertEqual(
                list(
                    db.scalars(
                        select(ParagraphModel.id).where(
                            ParagraphModel.document_id == document["id"]
                        )
                    ).all()
                ),
                paragraph_ids,
            )

    def test_duplicate_message_is_ignored_without_duplicate_index(self) -> None:
        document = self._create_pending_task("duplicate-message")
        task_id = document["task"]["id"]
        self.assertEqual(dispatch_document_tasks(), 1)

        with SessionLocal() as db:
            paragraph_ids_before = list(
                db.scalars(
                    select(ParagraphModel.id).where(
                        ParagraphModel.document_id == document["id"]
                    )
                ).all()
            )
            vector_ids_before = list(
                db.scalars(
                    select(EmbeddingRefModel.vector_id).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all()
            )

        result = run_document_task(
            task_id=task_id,
            attempt_no=1,
            worker_id="duplicate-worker",
        )
        self.assertEqual(result, TASK_RUN_IGNORED)

        with SessionLocal() as db:
            paragraph_ids_after = list(
                db.scalars(
                    select(ParagraphModel.id).where(
                        ParagraphModel.document_id == document["id"]
                    )
                ).all()
            )
            vector_ids_after = list(
                db.scalars(
                    select(EmbeddingRefModel.vector_id).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all()
            )
            attempts = list(
                db.scalars(
                    select(TaskAttemptModel).where(
                        TaskAttemptModel.task_id == task_id
                    )
                ).all()
            )

        self.assertEqual(paragraph_ids_after, paragraph_ids_before)
        self.assertEqual(vector_ids_after, vector_ids_before)
        self.assertEqual(len(attempts), 1)

    def test_old_attempt_message_cannot_run_after_manual_retry(self) -> None:
        document = self._create_pending_task("stale-attempt")
        task_id = document["task"]["id"]
        self.assertEqual(dispatch_document_tasks(FailingVectorStore()), 1)

        retry_response = self.client.post(f"/api/tasks/{task_id}/retry")
        self.assertEqual(retry_response.status_code, 202, retry_response.text)
        self.assertEqual(retry_response.json()["attempt_no"], 2)
        self.assertEqual(
            run_document_task(task_id, 1, "stale-worker"),
            TASK_RUN_IGNORED,
        )
        self.assertEqual(dispatch_document_tasks(), 1)

        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            attempts = list(
                db.scalars(
                    select(TaskAttemptModel)
                    .where(TaskAttemptModel.task_id == task_id)
                    .order_by(TaskAttemptModel.attempt_no)
                ).all()
            )

        self.assertEqual(task.status, TASK_STATUS_SUCCESS)
        self.assertEqual(task.attempt_no, 2)
        self.assertEqual(
            [attempt.status for attempt in attempts],
            [TASK_STATUS_FAILED, TASK_STATUS_SUCCESS],
        )

    def test_transient_failure_retries_until_max_attempts(self) -> None:
        document = self._create_pending_task("max-retries")
        task_id = document["task"]["id"]
        vector_store = TransientFailingVectorStore()

        with patch("app.services.task_service._task_retry_delay", return_value=0):
            self.assertEqual(dispatch_document_tasks(vector_store), 1)
            self.assertEqual(dispatch_document_tasks(vector_store), 1)
            self.assertEqual(dispatch_document_tasks(vector_store), 1)

        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            attempts = list(
                db.scalars(
                    select(TaskAttemptModel).where(
                        TaskAttemptModel.task_id == task_id
                    )
                ).all()
            )
            events = list(
                db.scalars(
                    select(OutboxEventModel).where(
                        OutboxEventModel.task_id == task_id
                    )
                ).all()
            )

        self.assertEqual(task.status, TASK_STATUS_FAILED)
        self.assertEqual(task.attempt_no, 3)
        self.assertEqual(task.retry_count, 2)
        self.assertEqual(task.error_code, "TRANSIENT_INFRASTRUCTURE")
        self.assertEqual(vector_store.calls, 3)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(events), 3)


class DocumentUploadStatusTestCase(unittest.TestCase):
    """
    覆盖上传、失败、重试、取消、删除和重新索引的跨存储一致性。

    断言同时检查 API、SQLite、Chroma 和原始文件，避免只验证表面状态而遗漏
    半成品数据或补偿失败。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def _create_knowledge(self, name: str) -> str:
        response = self.client.post(
            "/api/knowledges",
            json={"name": name, "description": "文档状态测试"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["id"]

    def _upload_document(self, knowledge_id: str, file_name: str, content: str) -> dict:
        response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={"file": (file_name, content.encode("utf-8"), "text/markdown")},
        )
        self.assertEqual(response.status_code, 202, response.text)
        document = response.json()
        self.assertEqual(dispatch_document_tasks(), 1)
        task_response = self.client.get(f"/api/tasks/{document['task']['id']}")
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_SUCCESS)
        return document

    def test_new_database_contains_observability_columns(self) -> None:
        database_inspector = inspect(engine)
        document_columns = {column["name"] for column in database_inspector.get_columns("document")}
        paragraph_columns = {column["name"] for column in database_inspector.get_columns("paragraph")}
        task_columns = {
            column["name"] for column in database_inspector.get_columns("task")
        }

        self.assertIn("status", document_columns)
        self.assertIn("error_message", document_columns)
        self.assertIn("chunk_length", paragraph_columns)
        self.assertIn("retry_count", task_columns)
        self.assertIn("cancel_requested", task_columns)

    def test_failed_task_can_retry(self) -> None:
        knowledge_id = self._create_knowledge("失败任务重试")
        failing_vector_store = FailingVectorStore()
        upload_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={
                "file": (
                    "retry.md",
                    b"retryable content",
                    "text/markdown",
                )
            },
        )

        self.assertEqual(upload_response.status_code, 202, upload_response.text)
        self.assertEqual(dispatch_document_tasks(failing_vector_store), 1)
        task_id = upload_response.json()["task"]["id"]
        self.assertEqual(
            self.client.get(f"/api/tasks/{task_id}").json()["status"],
            TASK_STATUS_FAILED,
        )

        retry_response = self.client.post(f"/api/tasks/{task_id}/retry")
        self.assertEqual(retry_response.status_code, 202, retry_response.text)
        self.assertEqual(dispatch_document_tasks(), 1)
        completed_task = self.client.get(f"/api/tasks/{task_id}").json()
        self.assertEqual(completed_task["status"], TASK_STATUS_SUCCESS)
        self.assertEqual(completed_task["retry_count"], 1)

        documents = self.client.get(
            f"/api/knowledges/{knowledge_id}/documents"
        ).json()
        self.assertEqual(documents[0]["status"], DOCUMENT_STATUS_SUCCESS)
        self.assertGreater(documents[0]["paragraph_count"], 0)

    def test_pending_task_can_be_cancelled(self) -> None:
        knowledge_id = self._create_knowledge("等待任务取消")
        upload_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={
                "file": (
                    "cancel.md",
                    b"content that should not be indexed",
                    "text/markdown",
                )
            },
        )

        self.assertEqual(upload_response.status_code, 202, upload_response.text)
        document_id = upload_response.json()["id"]
        task_id = upload_response.json()["task"]["id"]

        blocked_delete = self.client.delete(f"/api/documents/{document_id}")
        self.assertEqual(blocked_delete.status_code, 409, blocked_delete.text)

        cancel_response = self.client.post(f"/api/tasks/{task_id}/cancel")
        self.assertEqual(cancel_response.status_code, 200, cancel_response.text)
        self.assertEqual(cancel_response.json()["status"], TASK_STATUS_CANCELLED)
        self.assertTrue(cancel_response.json()["cancel_requested"])

        with SessionLocal() as db:
            task = db.get(TaskModel, task_id)
            document = db.get(DocumentModel, document_id)
            paragraphs = db.scalars(
                select(ParagraphModel).where(
                    ParagraphModel.document_id == document_id
                )
            ).all()
            event = db.scalar(
                select(OutboxEventModel).where(
                    OutboxEventModel.task_id == task_id
                )
            )

        self.assertEqual(task.status, TASK_STATUS_CANCELLED)
        self.assertEqual(document.status, DOCUMENT_STATUS_CANCELLED)
        self.assertEqual(paragraphs, [])
        self.assertEqual(event.status, OUTBOX_STATUS_DISCARDED)
        self.assertEqual(dispatch_document_tasks(), 0)

    def test_successful_upload_records_status_and_chunk_length(self) -> None:
        knowledge_id = self._create_knowledge("成功上传")
        content = "# RAG\n\nRAG 由检索和生成组成。"

        response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={"file": ("rag.md", content.encode("utf-8"), "text/markdown")},
        )

        self.assertEqual(response.status_code, 202, response.text)
        document = response.json()
        self.assertEqual(document["status"], TASK_STATUS_PENDING)
        self.assertEqual(document["task"]["status"], TASK_STATUS_PENDING)
        self.assertIsNotNone(document["source_file_id"])
        self.assertIsNone(document["error_message"])

        self.assertEqual(dispatch_document_tasks(), 1)
        task_response = self.client.get(f"/api/tasks/{document['task']['id']}")
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_SUCCESS)
        stored_document = self.client.get(
            f"/api/knowledges/{knowledge_id}/documents"
        ).json()[0]
        self.assertEqual(stored_document["status"], DOCUMENT_STATUS_SUCCESS)
        self.assertEqual(stored_document["char_length"], len(content))
        self.assertEqual(stored_document["paragraph_count"], 2)

        file_response = self.client.get(f"/api/documents/{document['id']}/file")
        self.assertEqual(file_response.status_code, 200, file_response.text)
        source_file = file_response.json()
        self.assertEqual(source_file["id"], document["source_file_id"])
        self.assertEqual(source_file["file_name"], "rag.md")
        self.assertEqual(source_file["file_size"], len(content.encode("utf-8")))
        self.assertEqual(
            source_file["sha256_hash"],
            hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("file_path", source_file)

        paragraph_response = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        )
        self.assertEqual(paragraph_response.status_code, 200, paragraph_response.text)

        paragraphs = paragraph_response.json()
        self.assertGreater(len(paragraphs), 0)
        for paragraph in paragraphs:
            self.assertEqual(paragraph["chunk_length"], len(paragraph["content"]))

    def test_empty_document_is_persisted_as_failed(self) -> None:
        knowledge_id = self._create_knowledge("空文档")

        response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={"file": ("empty.txt", b"   \n", "text/plain")},
        )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(dispatch_document_tasks(), 1)
        task_response = self.client.get(
            f"/api/tasks/{response.json()['task']['id']}"
        )
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_FAILED)
        self.assertEqual(
            task_response.json()["error_message"],
            "文档内容为空，无法入库",
        )
        documents = self.client.get(
            f"/api/knowledges/{knowledge_id}/documents"
        ).json()

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["status"], DOCUMENT_STATUS_FAILED)
        self.assertEqual(documents[0]["error_message"], "文档内容为空，无法入库")

    def test_vector_failure_rolls_back_relational_data_and_runs_cleanup(self) -> None:
        knowledge_id = self._create_knowledge("向量写入失败")
        failing_vector_store = FailingVectorStore()
        response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={"file": ("failure.md", b"content for failure", "text/markdown")},
        )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(dispatch_document_tasks(failing_vector_store), 1)
        task_response = self.client.get(
            f"/api/tasks/{response.json()['task']['id']}"
        )
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_FAILED)
        self.assertIn("模拟向量写入失败", task_response.json()["error_message"])
        documents = self.client.get(
            f"/api/knowledges/{knowledge_id}/documents"
        ).json()
        self.assertEqual(len(documents), 1)

        document = documents[0]
        self.assertEqual(document["status"], DOCUMENT_STATUS_FAILED)
        self.assertIn("模拟向量写入失败", document["error_message"])
        self.assertEqual(
            failing_vector_store.deleted_vector_ids,
            failing_vector_store.attempted_vector_ids,
        )

        # 段落和向量引用都属于失败事务，必须随 rollback 一起消失。
        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            paragraphs = db.scalars(
                select(ParagraphModel).where(ParagraphModel.document_id == document["id"])
            ).all()
            embedding_refs = db.scalars(
                select(EmbeddingRefModel).where(
                    EmbeddingRefModel.document_id == document["id"]
                )
            ).all()

        self.assertIsNotNone(stored_document)
        self.assertEqual(paragraphs, [])
        self.assertEqual(embedding_refs, [])
        # 原始文件有意保留，后续重新索引不需要用户再次上传。
        self.assertTrue(Path(stored_document.file_path).exists())

    def test_delete_document_removes_database_vectors_and_original_file(self) -> None:
        knowledge_id = self._create_knowledge("删除文档")
        document = self._upload_document(
            knowledge_id,
            "delete.md",
            "# 第一段\n\n需要被完整删除的第二段。",
        )

        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            file_path = Path(stored_document.file_path)
            source_file_id = stored_document.source_file_id
            vector_ids = list(
                db.scalars(
                    select(EmbeddingRefModel.vector_id).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all()
            )

        self.assertTrue(file_path.exists())
        self.assertGreater(len(vector_ids), 0)

        response = self.client.delete(f"/api/documents/{document['id']}")

        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertFalse(file_path.exists())
        self.assertEqual(
            self.client.get(
                f"/api/knowledges/{knowledge_id}/documents"
            ).json(),
            [],
        )

        with SessionLocal() as db:
            self.assertIsNone(db.get(DocumentModel, document["id"]))
            self.assertIsNone(db.get(FileModel, source_file_id))
            self.assertEqual(
                db.scalars(
                    select(ParagraphModel).where(
                        ParagraphModel.document_id == document["id"]
                    )
                ).all(),
                [],
            )
            self.assertEqual(
                db.scalars(
                    select(EmbeddingRefModel).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all(),
                [],
            )

        remaining_vectors = get_vector_store().collection.get(ids=vector_ids)
        self.assertEqual(remaining_vectors["ids"], [])

    def test_reindex_replaces_paragraphs_and_vectors(self) -> None:
        knowledge_id = self._create_knowledge("重新索引")
        document = self._upload_document(
            knowledge_id,
            "reindex.md",
            "旧内容第一段。\n\n旧内容第二段。",
        )
        old_paragraphs = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        ).json()
        problem_response = self.client.post(
            f"/api/paragraphs/{old_paragraphs[0]['id']}/problems",
            json={"content": "重新索引前的问题"},
        )
        self.assertEqual(problem_response.status_code, 200, problem_response.text)
        old_problem_id = problem_response.json()["id"]

        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            file_path = Path(stored_document.file_path)
            old_paragraph_ids = list(
                db.scalars(
                    select(ParagraphModel.id).where(
                        ParagraphModel.document_id == document["id"]
                    )
                ).all()
            )
            old_vector_ids = list(
                db.scalars(
                    select(EmbeddingRefModel.vector_id).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all()
            )

        new_content = "重新索引后的唯一内容。"
        file_path.write_text(new_content, encoding="utf-8")

        response = self.client.post(f"/api/documents/{document['id']}/reindex")

        self.assertEqual(response.status_code, 200, response.text)
        reindexed_document = response.json()
        self.assertEqual(reindexed_document["status"], DOCUMENT_STATUS_SUCCESS)
        self.assertIsNone(reindexed_document["error_message"])
        self.assertEqual(reindexed_document["char_length"], len(new_content))
        self.assertEqual(reindexed_document["paragraph_count"], 1)
        source_file = self.client.get(
            f"/api/documents/{document['id']}/file"
        ).json()
        self.assertEqual(
            source_file["file_size"],
            len(new_content.encode("utf-8")),
        )
        self.assertEqual(
            source_file["sha256_hash"],
            hashlib.sha256(new_content.encode("utf-8")).hexdigest(),
        )

        paragraphs = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        ).json()
        self.assertEqual([paragraph["content"] for paragraph in paragraphs], [new_content])
        self.assertTrue(
            set(old_paragraph_ids).isdisjoint(
                {paragraph["id"] for paragraph in paragraphs}
            )
        )
        self.assertEqual(
            get_vector_store().collection.get(ids=old_vector_ids)["ids"],
            [],
        )
        with SessionLocal() as db:
            self.assertIsNone(db.get(ProblemModel, old_problem_id))

    def test_failed_reindex_preserves_previous_paragraphs(self) -> None:
        knowledge_id = self._create_knowledge("重新索引失败")
        document = self._upload_document(
            knowledge_id,
            "reindex-failed.md",
            "原有索引内容。",
        )

        original_paragraphs = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        ).json()
        problem_response = self.client.post(
            f"/api/paragraphs/{original_paragraphs[0]['id']}/problems",
            json={"content": "旧索引对应的问题是什么？"},
        )
        self.assertEqual(problem_response.status_code, 200, problem_response.text)
        problem_id = problem_response.json()["id"]

        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            Path(stored_document.file_path).write_text("   \n", encoding="utf-8")

        response = self.client.post(f"/api/documents/{document['id']}/reindex")

        self.assertEqual(response.status_code, 400, response.text)
        current_paragraphs = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        ).json()
        self.assertEqual(current_paragraphs, original_paragraphs)

        documents = self.client.get(
            f"/api/knowledges/{knowledge_id}/documents"
        ).json()
        self.assertEqual(documents[0]["status"], DOCUMENT_STATUS_FAILED)
        self.assertEqual(documents[0]["paragraph_count"], len(original_paragraphs))
        self.assertEqual(
            [
                problem["id"]
                for problem in self.client.get(
                    f"/api/paragraphs/{original_paragraphs[0]['id']}/problems"
                ).json()
            ],
            [problem_id],
        )

    def test_partial_vector_delete_failure_restores_previous_index(self) -> None:
        knowledge_id = self._create_knowledge("重新索引补偿")
        document = self._upload_document(
            knowledge_id,
            "reindex-compensation.md",
            "旧索引第一段。\n\n旧索引第二段。",
        )

        original_paragraphs = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        ).json()
        problem_response = self.client.post(
            f"/api/paragraphs/{original_paragraphs[0]['id']}/problems",
            json={"content": "部分删除失败后还能恢复吗？"},
        )
        self.assertEqual(problem_response.status_code, 200, problem_response.text)
        problem_id = problem_response.json()["id"]

        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            Path(stored_document.file_path).write_text("全新的索引内容。", encoding="utf-8")
            old_vector_ids = list(
                db.scalars(
                    select(EmbeddingRefModel.vector_id).where(
                        EmbeddingRefModel.document_id == document["id"]
                    )
                ).all()
            )

        real_vector_store = get_vector_store()
        failing_vector_store = PartiallyFailingVectorStore(
            real_vector_store,
            old_vector_ids,
        )
        app.dependency_overrides[get_vector_store] = lambda: failing_vector_store

        try:
            response = self.client.post(f"/api/documents/{document['id']}/reindex")
        finally:
            app.dependency_overrides.pop(get_vector_store, None)

        self.assertEqual(response.status_code, 500, response.text)
        self.assertIn("模拟旧向量部分删除失败", response.json()["detail"])
        self.assertEqual(
            self.client.get(f"/api/documents/{document['id']}/paragraphs").json(),
            original_paragraphs,
        )
        self.assertEqual(
            [
                problem["id"]
                for problem in self.client.get(
                    f"/api/paragraphs/{original_paragraphs[0]['id']}/problems"
                ).json()
            ],
            [problem_id],
        )

        restored_old_vectors = real_vector_store.collection.get(ids=old_vector_ids)
        remaining_new_vectors = real_vector_store.collection.get(
            ids=failing_vector_store.new_vector_ids
        )
        self.assertCountEqual(restored_old_vectors["ids"], old_vector_ids)
        self.assertEqual(remaining_new_vectors["ids"], [])


class ProblemApiTestCase(unittest.TestCase):
    """
    覆盖问题向量从创建、召回到删除的完整生命周期。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def _create_document(self) -> tuple[str, dict, dict]:
        knowledge_response = self.client.post(
            "/api/knowledges",
            json={"name": "问题增强知识库", "description": "问题召回测试"},
        )
        self.assertEqual(knowledge_response.status_code, 200, knowledge_response.text)
        knowledge_id = knowledge_response.json()["id"]

        document_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={
                "file": (
                    "problem.md",
                    "# 支付\n\n退款将在三个工作日内到账。".encode("utf-8"),
                    "text/markdown",
                )
            },
        )
        self.assertEqual(document_response.status_code, 202, document_response.text)
        document = document_response.json()
        self.assertEqual(dispatch_document_tasks(), 1)
        task_response = self.client.get(f"/api/tasks/{document['task']['id']}")
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_SUCCESS)

        paragraphs_response = self.client.get(
            f"/api/documents/{document['id']}/paragraphs"
        )
        self.assertEqual(paragraphs_response.status_code, 200, paragraphs_response.text)
        paragraph = paragraphs_response.json()[-1]
        return knowledge_id, document, paragraph

    def test_problem_vector_can_recall_and_return_source_paragraph(self) -> None:
        knowledge_id, _document, paragraph = self._create_document()
        question = "退款多久到账？"

        create_response = self.client.post(
            f"/api/paragraphs/{paragraph['id']}/problems",
            json={"content": question},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        problem = create_response.json()
        self.assertEqual(problem["paragraph_ids"], [paragraph["id"]])

        list_response = self.client.get(
            f"/api/paragraphs/{paragraph['id']}/problems"
        )
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual([item["id"] for item in list_response.json()], [problem["id"]])

        with SessionLocal() as db:
            mapping = db.scalar(
                select(ProblemParagraphMappingModel).where(
                    ProblemParagraphMappingModel.problem_id == problem["id"]
                )
            )
            embedding_ref = db.scalar(
                select(EmbeddingRefModel).where(
                    EmbeddingRefModel.problem_id == problem["id"]
                )
            )

        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.paragraph_id, paragraph["id"])
        self.assertIsNotNone(embedding_ref)
        self.assertEqual(embedding_ref.source_type, EMBEDDING_SOURCE_PROBLEM)

        vector = get_vector_store().collection.get(
            ids=[embedding_ref.vector_id],
            include=["metadatas"],
        )
        self.assertEqual(vector["metadatas"][0]["problem_id"], problem["id"])
        self.assertEqual(
            vector["metadatas"][0]["source_type"],
            EMBEDDING_SOURCE_PROBLEM,
        )

        # top_k=1 时，文本完全相同的问题向量应优先命中，再通过 mapping
        # 返回原始段落，而不是把 Problem 文本当作回答引用。
        chat_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/chat",
            json={"question": question, "top_k": 1},
        )
        self.assertEqual(chat_response.status_code, 200, chat_response.text)
        references = chat_response.json()["references"]
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]["paragraph_id"], paragraph["id"])
        self.assertEqual(references[0]["content"], paragraph["content"])

        other_knowledge_response = self.client.post(
            "/api/knowledges",
            json={"name": "隔离知识库", "description": "不应命中问题向量"},
        )
        self.assertEqual(
            other_knowledge_response.status_code,
            200,
            other_knowledge_response.text,
        )
        isolated_chat_response = self.client.post(
            f"/api/knowledges/{other_knowledge_response.json()['id']}/chat",
            json={"question": question, "top_k": 1},
        )
        self.assertEqual(
            isolated_chat_response.status_code,
            200,
            isolated_chat_response.text,
        )
        self.assertEqual(isolated_chat_response.json()["references"], [])

        duplicate_response = self.client.post(
            f"/api/paragraphs/{paragraph['id']}/problems",
            json={"content": question},
        )
        self.assertEqual(duplicate_response.status_code, 409, duplicate_response.text)

        delete_response = self.client.delete(f"/api/problems/{problem['id']}")
        self.assertEqual(delete_response.status_code, 204, delete_response.text)

        with SessionLocal() as db:
            self.assertIsNone(db.get(ProblemModel, problem["id"]))
            self.assertIsNone(
                db.scalar(
                    select(ProblemParagraphMappingModel).where(
                        ProblemParagraphMappingModel.problem_id == problem["id"]
                    )
                )
            )
            self.assertIsNone(
                db.scalar(
                    select(EmbeddingRefModel).where(
                        EmbeddingRefModel.problem_id == problem["id"]
                    )
                )
            )

        self.assertEqual(
            get_vector_store().collection.get(ids=[embedding_ref.vector_id])["ids"],
            [],
        )

    def test_document_delete_removes_related_problem_data(self) -> None:
        _knowledge_id, document, paragraph = self._create_document()
        create_response = self.client.post(
            f"/api/paragraphs/{paragraph['id']}/problems",
            json={"content": "退款需要几天到账？"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        problem_id = create_response.json()["id"]

        with SessionLocal() as db:
            problem_vector_id = db.scalar(
                select(EmbeddingRefModel.vector_id).where(
                    EmbeddingRefModel.problem_id == problem_id
                )
            )

        delete_response = self.client.delete(f"/api/documents/{document['id']}")
        self.assertEqual(delete_response.status_code, 204, delete_response.text)

        with SessionLocal() as db:
            self.assertIsNone(db.get(ProblemModel, problem_id))
            self.assertIsNone(
                db.scalar(
                    select(ProblemParagraphMappingModel).where(
                        ProblemParagraphMappingModel.problem_id == problem_id
                    )
                )
            )
        self.assertEqual(
            get_vector_store().collection.get(ids=[problem_vector_id])["ids"],
            [],
        )

    def test_problem_vector_failure_rolls_back_problem_and_mapping(self) -> None:
        _knowledge_id, _document, paragraph = self._create_document()
        failing_vector_store = FailingVectorStore()
        app.dependency_overrides[get_vector_store] = lambda: failing_vector_store

        try:
            response = self.client.post(
                f"/api/paragraphs/{paragraph['id']}/problems",
                json={"content": "这条问题不应留下半成品"},
            )
        finally:
            app.dependency_overrides.pop(get_vector_store, None)

        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(
            failing_vector_store.deleted_vector_ids,
            failing_vector_store.attempted_vector_ids,
        )
        with SessionLocal() as db:
            self.assertIsNone(
                db.scalar(
                    select(ProblemModel).where(
                        ProblemModel.content == "这条问题不应留下半成品"
                    )
                )
            )
            self.assertIsNone(
                db.scalar(
                    select(ProblemParagraphMappingModel).where(
                        ProblemParagraphMappingModel.paragraph_id == paragraph["id"]
                    )
                )
            )

    def test_problem_delete_failure_restores_vector_and_database_data(self) -> None:
        _knowledge_id, _document, paragraph = self._create_document()
        create_response = self.client.post(
            f"/api/paragraphs/{paragraph['id']}/problems",
            json={"content": "删除失败后需要恢复吗？"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        problem_id = create_response.json()["id"]

        with SessionLocal() as db:
            vector_id = db.scalar(
                select(EmbeddingRefModel.vector_id).where(
                    EmbeddingRefModel.problem_id == problem_id
                )
            )

        real_vector_store = get_vector_store()
        failing_vector_store = PartiallyFailingVectorStore(
            real_vector_store,
            [vector_id],
        )
        app.dependency_overrides[get_vector_store] = lambda: failing_vector_store

        try:
            response = self.client.delete(f"/api/problems/{problem_id}")
        finally:
            app.dependency_overrides.pop(get_vector_store, None)

        self.assertEqual(response.status_code, 500, response.text)
        with SessionLocal() as db:
            self.assertIsNotNone(db.get(ProblemModel, problem_id))
            self.assertIsNotNone(
                db.scalar(
                    select(ProblemParagraphMappingModel).where(
                        ProblemParagraphMappingModel.problem_id == problem_id
                    )
                )
            )
            self.assertIsNotNone(
                db.scalar(
                    select(EmbeddingRefModel).where(
                        EmbeddingRefModel.problem_id == problem_id
                    )
                )
            )

        restored_vector = real_vector_store.collection.get(
            ids=[vector_id],
            include=["metadatas"],
        )
        self.assertEqual(restored_vector["ids"], [vector_id])
        self.assertEqual(restored_vector["metadatas"][0]["problem_id"], problem_id)


class RetrievalModeApiTestCase(unittest.TestCase):
    """
    覆盖向量、关键词、混合检索以及知识库级配置。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def _create_searchable_document(self) -> tuple[str, dict]:
        knowledge_response = self.client.post(
            "/api/knowledges",
            json={"name": "混合检索知识库", "description": "v0.4 测试"},
        )
        self.assertEqual(knowledge_response.status_code, 200, knowledge_response.text)
        knowledge_id = knowledge_response.json()["id"]

        content = (
            "# Search Architecture\n\n"
            "Hybrid search combines semantic vectors with lexical keywords.\n\n"
            "A reranker merges candidates from independent retrieval channels."
        )
        document_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/documents",
            files={
                "file": (
                    "hybrid.md",
                    content.encode("utf-8"),
                    "text/markdown",
                )
            },
        )
        self.assertEqual(document_response.status_code, 202, document_response.text)
        self.assertEqual(dispatch_document_tasks(), 1)
        task_response = self.client.get(
            f"/api/tasks/{document_response.json()['task']['id']}"
        )
        self.assertEqual(task_response.status_code, 200, task_response.text)
        self.assertEqual(task_response.json()["status"], TASK_STATUS_SUCCESS)
        return knowledge_id, document_response.json()

    def test_retrieval_config_and_all_search_modes(self) -> None:
        knowledge_id, _document = self._create_searchable_document()

        config_response = self.client.patch(
            f"/api/knowledges/{knowledge_id}/retrieval-config",
            json={
                "top_k": 2,
                "score_threshold": 0.0,
                "search_mode": "keywords",
                "blend_weight": 0.65,
            },
        )
        self.assertEqual(config_response.status_code, 200, config_response.text)
        self.assertEqual(
            config_response.json()["retrieval_config"],
            {
                "top_k": 2,
                "score_threshold": 0.0,
                "search_mode": "keywords",
                "blend_weight": 0.65,
            },
        )

        keyword_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={"question": "lexical keywords"},
        )
        self.assertEqual(keyword_response.status_code, 200, keyword_response.text)
        keyword_result = keyword_response.json()
        self.assertEqual(keyword_result["config"]["search_mode"], "keywords")
        self.assertGreater(len(keyword_result["results"]), 0)
        self.assertEqual(keyword_result["results"][0]["match_type"], "keywords")
        self.assertIn(
            "keyword_raw_score",
            keyword_result["results"][0]["score_meta"],
        )

        embedding_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={
                "question": "lexical keywords",
                "search_mode": "embedding",
                "top_k": 1,
            },
        )
        self.assertEqual(embedding_response.status_code, 200, embedding_response.text)
        self.assertEqual(
            embedding_response.json()["results"][0]["match_type"],
            "embedding",
        )

        blend_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={
                "question": "lexical keywords",
                "search_mode": "blend",
                "top_k": 2,
                "blend_weight": 0.6,
            },
        )
        self.assertEqual(blend_response.status_code, 200, blend_response.text)
        blend_result = blend_response.json()["results"][0]
        self.assertEqual(blend_result["match_type"], "blend")
        self.assertEqual(
            blend_result["score_meta"]["algorithm"],
            "weighted_rrf",
        )
        self.assertIn("embedding", blend_result["score_meta"]["sources"])
        self.assertIn("keywords", blend_result["score_meta"]["sources"])

        threshold_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={
                "question": "lexical keywords",
                "search_mode": "embedding",
                "score_threshold": 1.0,
            },
        )
        self.assertEqual(
            threshold_response.status_code,
            200,
            threshold_response.text,
        )
        self.assertEqual(threshold_response.json()["results"], [])

    def test_fts_index_tracks_reindex_and_delete(self) -> None:
        knowledge_id, document = self._create_searchable_document()

        initial_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={"question": "lexical", "search_mode": "keywords"},
        )
        self.assertGreater(len(initial_response.json()["results"]), 0)

        with SessionLocal() as db:
            stored_document = db.get(DocumentModel, document["id"])
            source_file = db.get(FileModel, stored_document.source_file_id)
            Path(source_file.file_path).write_text(
                "This replacement contains only database migration notes.",
                encoding="utf-8",
            )

        reindex_response = self.client.post(
            f"/api/documents/{document['id']}/reindex"
        )
        self.assertEqual(reindex_response.status_code, 200, reindex_response.text)

        stale_keyword_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={"question": "lexical", "search_mode": "keywords"},
        )
        self.assertEqual(stale_keyword_response.json()["results"], [])

        new_keyword_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={"question": "migration", "search_mode": "keywords"},
        )
        self.assertGreater(len(new_keyword_response.json()["results"]), 0)

        delete_response = self.client.delete(f"/api/documents/{document['id']}")
        self.assertEqual(delete_response.status_code, 204, delete_response.text)
        deleted_keyword_response = self.client.post(
            f"/api/knowledges/{knowledge_id}/retrieval-test",
            json={"question": "migration", "search_mode": "keywords"},
        )
        self.assertEqual(deleted_keyword_response.json()["results"], [])


class KnowledgeFolderApiTestCase(unittest.TestCase):
    """
    覆盖文件夹树和知识库归属的核心约束。

    每个测试使用唯一名称，和文档测试共享临时数据库时也不会互相影响。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)

    def _create_folder(
        self,
        name: str,
        parent_id: str | None = None,
    ) -> dict:
        response = self.client.post(
            "/api/knowledge-folders",
            json={
                "name": name,
                "description": f"{name} 描述",
                "parent_id": parent_id,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_new_database_contains_folder_table_and_knowledge_relation(self) -> None:
        database_inspector = inspect(engine)
        self.assertIn("knowledge_folder", database_inspector.get_table_names())

        knowledge_columns = {
            column["name"] for column in database_inspector.get_columns("knowledge")
        }
        self.assertIn("folder_id", knowledge_columns)

    def test_folder_tree_and_knowledge_move_lifecycle(self) -> None:
        root = self._create_folder("研发资料")
        child = self._create_folder("RAG", parent_id=root["id"])

        knowledge_response = self.client.post(
            "/api/knowledges",
            json={
                "name": "检索知识库",
                "description": "目录归属测试",
                "folder_id": child["id"],
            },
        )
        self.assertEqual(knowledge_response.status_code, 200, knowledge_response.text)
        knowledge = knowledge_response.json()
        self.assertEqual(knowledge["folder_id"], child["id"])

        tree_response = self.client.get("/api/knowledge-folders")
        self.assertEqual(tree_response.status_code, 200, tree_response.text)
        root_node = next(
            node for node in tree_response.json() if node["id"] == root["id"]
        )
        self.assertEqual([node["id"] for node in root_node["children"]], [child["id"]])

        # 根目录移动到自己的后代下面会形成环，必须在写入前拒绝。
        cycle_response = self.client.patch(
            f"/api/knowledge-folders/{root['id']}",
            json={"parent_id": child["id"]},
        )
        self.assertEqual(cycle_response.status_code, 400, cycle_response.text)

        non_empty_response = self.client.delete(
            f"/api/knowledge-folders/{child['id']}"
        )
        self.assertEqual(non_empty_response.status_code, 409, non_empty_response.text)

        move_to_root_response = self.client.patch(
            f"/api/knowledges/{knowledge['id']}/folder",
            json={"folder_id": None},
        )
        self.assertEqual(move_to_root_response.status_code, 200, move_to_root_response.text)
        self.assertIsNone(move_to_root_response.json()["folder_id"])

        self.assertEqual(
            self.client.delete(f"/api/knowledge-folders/{child['id']}").status_code,
            204,
        )
        self.assertEqual(
            self.client.delete(f"/api/knowledge-folders/{root['id']}").status_code,
            204,
        )

    def test_folder_validation_rejects_duplicate_and_missing_parent(self) -> None:
        self._create_folder("同级目录")

        duplicate_response = self.client.post(
            "/api/knowledge-folders",
            json={"name": "同级目录", "description": "", "parent_id": None},
        )
        self.assertEqual(duplicate_response.status_code, 409, duplicate_response.text)

        missing_parent_response = self.client.post(
            "/api/knowledge-folders",
            json={
                "name": "孤儿目录",
                "description": "",
                "parent_id": "missing-folder",
            },
        )
        self.assertEqual(
            missing_parent_response.status_code,
            404,
            missing_parent_response.text,
        )

        missing_knowledge_response = self.client.patch(
            "/api/knowledges/missing-knowledge/folder",
            json={"folder_id": None},
        )
        self.assertEqual(
            missing_knowledge_response.status_code,
            404,
            missing_knowledge_response.text,
        )


if __name__ == "__main__":
    unittest.main()
