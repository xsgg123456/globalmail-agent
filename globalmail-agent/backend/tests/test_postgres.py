import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import IntegrityError

from globalmail_agent.adapters.object_store import ObjectStore, Scope, Source
from globalmail_agent.adapters.schema import content_dependencies, objects, workspaces
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings


@unittest.skipUnless(os.getenv("GLOBALMAIL_TEST_DATABASE_URL"), "requires isolated PostgreSQL configuration")
class PostgresTests(unittest.TestCase):
    def setUp(self):
        self.admin = create_engine(os.environ["GLOBALMAIL_TEST_DATABASE_URL"], hide_parameters=True)
        self.schema = "test_phase2_" + uuid4().hex
        with self.admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self.cleanup_schema)
        self.engine = create_engine(os.environ["GLOBALMAIL_TEST_DATABASE_URL"], hide_parameters=True,
                                    connect_args={"options": f"-csearch_path={self.schema}"})
        self.addCleanup(self.engine.dispose)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        self.migrate("head")
        self.workspace = uuid4()
        with self.engine.begin() as connection:
            connection.execute(insert(workspaces).values(id=self.workspace, name="isolated test"))
        self.scope = Scope(workspace_id=self.workspace, mode="simulation", branch_id=uuid4(),
                           customer_id=uuid4(), purpose="test")
        self.store = ObjectStore(Path(self.temp.name), self.engine)
        self.source = Source(kind="test", reference="synthetic")

    def cleanup_schema(self):
        with self.admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.admin.dispose()

    def migrate(self, revision):
        with self.engine.begin() as connection:
            self.config.attributes["connection"] = connection
            command.upgrade(self.config, revision)

    def test_migration_repeat_restart_and_ready(self):
        self.migrate("head")
        object_id = self.store.put(b"persistent body", self.scope, self.source)
        self.engine.dispose()
        restarted = ObjectStore(Path(self.temp.name), self.engine)
        self.assertEqual(restarted.get(object_id, self.scope), b"persistent body")
        settings = Settings(object_root=Path(self.temp.name))
        with TestClient(create_app(settings, engine=self.engine), base_url="http://localhost") as client:
            result = client.get("/api/v1/health/ready")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["data"]["schema"], "ready")

    def test_source_dependency_and_scope_database_constraint(self):
        parent = self.store.put(b"source", self.scope, self.source)
        child = self.store.put(b"derived", self.scope, self.source, derived_from=(parent,))
        other = self.scope.model_copy(update={"customer_id": uuid4()})
        outsider = self.store.put(b"other customer", other, self.source)
        with self.assertRaises(LookupError):
            self.store.get(parent, other)
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(insert(content_dependencies).values(id=uuid4(), **self.scope.model_dump(),
                    source_object_id=parent, dependent_object_id=outsider))
        before = set(Path(self.temp.name).iterdir())
        with self.assertRaises(IntegrityError):
            self.store.put(b"bad derived", self.scope, self.source, derived_from=(outsider,))
        self.assertEqual(before, set(Path(self.temp.name).iterdir()))
        with self.engine.connect() as connection:
            self.assertEqual(len(connection.execute(select(content_dependencies)).all()), 1)
            self.assertEqual(len(connection.execute(select(objects)).all()), 3)
        self.assertEqual(self.store.get(child, self.scope), b"derived")

    def test_path_and_digest_protection(self):
        with self.assertRaises(ValueError):
            self.store.get("../secret", self.scope)
        object_id = self.store.put(b"original", self.scope, self.source)
        (Path(self.temp.name) / str(object_id)).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            self.store.get(object_id, self.scope)

    def test_every_scope_dimension_is_enforced(self):
        parent = self.store.put(b"scope protected", self.scope, self.source)
        alternative_workspace = uuid4()
        with self.engine.begin() as connection:
            connection.execute(insert(workspaces).values(id=alternative_workspace, name="second isolated"))
        for key, value in (("workspace_id", alternative_workspace), ("mode", "historical_replay"),
                           ("branch_id", uuid4()), ("customer_id", uuid4()), ("purpose", "other")):
            other = self.scope.model_copy(update={key: value})
            with self.subTest(scope_key=key):
                with self.assertRaises(LookupError):
                    self.store.get(parent, other)
                with self.assertRaises(IntegrityError):
                    self.store.put(b"not authorized", other, self.source, derived_from=(parent,))

    def test_database_failure_and_missing_table_are_degraded(self):
        bad_engine = create_engine("postgresql+psycopg://invalid:SECRET_MARKER@127.0.0.1:1/missing",
                                   connect_args={"connect_timeout": 1})
        self.addCleanup(bad_engine.dispose)
        with TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=bad_engine),
                        base_url="http://localhost") as client:
            result = client.get("/api/v1/health/ready")
            self.assertEqual(result.status_code, 503)
            self.assertNotIn("SECRET_MARKER", result.text)
            self.assertEqual(result.json()["data"]["database"], "unavailable")
        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE deletion_journal"))
        with TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine),
                        base_url="http://localhost") as client:
            result = client.get("/api/v1/health/ready")
            self.assertEqual(result.status_code, 503)
            self.assertEqual(result.json()["data"]["schema"], "unavailable")

    def test_missing_schema_and_unwritable_store_degraded(self):
        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
        blocked = Path(self.temp.name) / "file"
        blocked.write_bytes(b"not a directory")
        with TestClient(create_app(Settings(object_root=blocked), engine=self.engine),
                        base_url="http://localhost") as client:
            result = client.get("/api/v1/health/ready")
            self.assertEqual(result.status_code, 503)
            self.assertEqual(result.json()["data"]["database"], "ready")
            self.assertEqual(result.json()["data"]["schema"], "unavailable")
            self.assertEqual(result.json()["data"]["object_store"], "unavailable")

