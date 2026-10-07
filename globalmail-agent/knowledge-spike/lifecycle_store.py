"""Isolated SQL lifecycle contract; deliberately not a production knowledge service."""
import hashlib
import json
import math

import psycopg
from psycopg.rows import dict_row


class ContractError(ValueError):
    """A deterministic contract rejection, safe to report by its fixed code."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def validate_vectors(vectors, count, dimensions):
    if len(vectors) != count or not count:
        raise ContractError('vector_count')
    for vector in vectors:
        if len(vector) != dimensions or any(not math.isfinite(x) for x in vector):
            raise ContractError('vector_shape_or_finiteness')
        if not any(vector):
            raise ContractError('zero_vector')


SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE profiles (id text PRIMARY KEY, config jsonb NOT NULL, dimensions int NOT NULL);
CREATE TABLE documents (id text PRIMARY KEY, active bool NOT NULL DEFAULT true,
                        tombstone bool NOT NULL DEFAULT false);
CREATE TABLE registered_products (sku text PRIMARY KEY, brand text NOT NULL);
CREATE TABLE builds (id text PRIMARY KEY, version text NOT NULL, profile text REFERENCES profiles,
 payload text NOT NULL, expected_count int NOT NULL CHECK(expected_count>0),
 documents text[] NOT NULL, started_epoch bigint NOT NULL, reviewed bool NOT NULL,
 state text NOT NULL CHECK(state IN ('indexing','ready')));
CREATE TABLE chunks (build text REFERENCES builds ON DELETE CASCADE,
 id text, document text REFERENCES documents, body text NOT NULL,
 brands text[] NOT NULL, skus text[] NOT NULL, modes text[] NOT NULL,
 split text NOT NULL, available_at timestamptz NOT NULL, until_at timestamptz,
 location jsonb NOT NULL, embedding vector NOT NULL, PRIMARY KEY(build,id));
CREATE TABLE head (singleton bool PRIMARY KEY CHECK(singleton), epoch bigint NOT NULL,
                   build text REFERENCES builds);
INSERT INTO head VALUES (true,0,NULL);
CREATE TABLE events (epoch bigint PRIMARY KEY, action text NOT NULL, build text,
                     documents text[], actor text NOT NULL DEFAULT 'isolated_probe');
"""

# MATERIALIZED makes the authorization/time candidate boundary explicit before ranking.
CANDIDATES = """
WITH scope AS MATERIALIZED (
 SELECT h.epoch,b.id AS build,b.version,b.profile,c.id,c.document,c.body,c.location,c.embedding
 FROM head h JOIN builds b ON b.id=h.build JOIN chunks c ON c.build=b.id
 JOIN documents d ON d.id=c.document
 JOIN registered_products r ON r.sku=ANY(c.skus) AND r.brand=ANY(c.brands)
 WHERE d.active AND NOT d.tombstone AND b.state='ready' AND b.profile=%s
 AND r.sku=%s AND r.brand=%s AND %s=ANY(c.modes) AND c.split=%s
 AND c.available_at<=%s::timestamptz AND (c.until_at IS NULL OR %s::timestamptz<c.until_at)
) """


class Store:
    def __init__(self, dsn):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def initialize(self):
        with self.connect() as conn:
            conn.execute(SCHEMA)

    def register_products(self, products):
        with self.connect() as conn, conn.transaction():
            for sku, brand in products.items():
                conn.execute('INSERT INTO registered_products VALUES (%s,%s)', (sku, brand))

    @staticmethod
    def fence(conn, epoch, documents=()):
        head = conn.execute('SELECT * FROM head FOR UPDATE').fetchone()
        if head['epoch'] != epoch:
            raise ContractError('stale_epoch')
        bad = conn.execute('SELECT id FROM documents WHERE id=ANY(%s) '
                           'AND (tombstone OR NOT active)', (list(documents),)).fetchone()
        if bad:
            raise ContractError('document_revoked_or_deleted')
        return head

    def epoch(self):
        with self.connect() as conn:
            return conn.execute('SELECT epoch FROM head').fetchone()['epoch']

    def prepare(self, key, version, profile, chunks, vectors, epoch, reviewed=True):
        validate_vectors(vectors, len(chunks), profile['dimensions'])
        profile_id = digest(profile)
        payload = digest([version, profile, chunks, vectors, reviewed])
        documents = sorted({c['document_id'] for c in chunks})
        with self.connect() as conn, conn.transaction():
            self.fence(conn, epoch, documents)
            old = conn.execute('SELECT payload FROM builds WHERE id=%s', (key,)).fetchone()
            if old:
                if old['payload'] != payload:
                    raise ContractError('idempotency_payload_conflict')
                return key
            conn.execute('INSERT INTO profiles VALUES (%s,%s::jsonb,%s) ON CONFLICT DO NOTHING',
                         (profile_id, json.dumps(profile), profile['dimensions']))
            for doc in documents:
                conn.execute('INSERT INTO documents(id) VALUES (%s) ON CONFLICT DO NOTHING', (doc,))
            conn.execute('INSERT INTO builds VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                         (key, version, profile_id, payload, len(chunks), documents,
                          epoch, reviewed, 'indexing'))
        return key

    def finish(self, key, chunks, vectors, epoch):
        with self.connect() as conn, conn.transaction():
            self.fence(conn, epoch)
            build = conn.execute('SELECT b.*,p.config,p.dimensions FROM builds b '
                                 'JOIN profiles p ON p.id=b.profile WHERE b.id=%s', (key,)).fetchone()
            if not build or build['started_epoch'] != epoch:
                raise ContractError('stale_or_missing_build')
            self.fence(conn, epoch, build['documents'])
            validate_vectors(vectors, len(chunks), build['dimensions'])
            if digest([build['version'], build['config'], chunks, vectors, build['reviewed']]) != build['payload']:
                raise ContractError('completion_payload_conflict')
            if build['state'] == 'ready':
                return
            for chunk, vector in zip(chunks, vectors):
                location = {k:chunk[k] for k in ('page','heading','input_hash','parent_id') if k in chunk}
                conn.execute('INSERT INTO chunks VALUES '
                             '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::vector)',
                             (key, chunk['chunk_id'], chunk['document_id'], chunk['text'],
                              chunk['brands'], chunk['skus'], chunk['allowed_modes'],
                              chunk['usage_split'], chunk['available_at'], chunk.get('until_at'),
                              json.dumps(location), json.dumps(vector)))
            conn.execute("UPDATE builds SET state='ready' WHERE id=%s", (key,))

    def publish(self, key, epoch, action='publish'):
        with self.connect() as conn, conn.transaction():
            self.fence(conn, epoch)
            build = conn.execute('SELECT * FROM builds WHERE id=%s', (key,)).fetchone()
            if not build or build['state'] != 'ready' or not build['reviewed']:
                raise ContractError('build_not_ready_or_reviewed')
            self.fence(conn, epoch, build['documents'])
            count = conn.execute('SELECT count(*) AS n FROM chunks WHERE build=%s', (key,)).fetchone()['n']
            if count != build['expected_count']:
                raise ContractError('incomplete_build')
            conn.execute('UPDATE head SET build=%s,epoch=epoch+1', (key,))
            conn.execute('INSERT INTO events(epoch,action,build) VALUES (%s,%s,%s)', (epoch+1, action, key))
        return epoch+1

    @staticmethod
    def scope_params(profile, query):
        return (profile, query['sku'], query['brand'], query['mode'], query['knowledge_split'],
                query['as_of'], query['as_of'])

    def search(self, conn, profile, query, vector, limit=5):
        # One statement reads publication and candidate rows from one MVCC snapshot.
        sql = CANDIDATES + 'SELECT *,embedding <=> %s::vector AS distance FROM scope '
        rows = conn.execute(sql+'ORDER BY distance,id LIMIT %s',
                            (*self.scope_params(profile, query), json.dumps(vector), limit)).fetchall()
        return [{k:v for k,v in row.items() if k != 'embedding'} for row in rows]

    def guard(self, refs, query):
        """Always checks on a fresh transaction; never on a caller's retained MVCC snapshot."""
        if not refs:
            return False
        with self.connect() as conn:
            sql = CANDIDATES + 'SELECT epoch,build,profile,id FROM scope WHERE id=ANY(%s)'
            rows = conn.execute(sql, (*self.scope_params(refs[0]['profile'], query),
                                      [r['id'] for r in refs])).fetchall()
        return {(r['epoch'],r['build'],r['profile'],r['id']) for r in rows} == {
            (r['epoch'],r['build'],r['profile'],r['id']) for r in refs}

    def revoke(self, documents, epoch, delete=False):
        with self.connect() as conn, conn.transaction():
            self.fence(conn, epoch)
            conn.execute('UPDATE documents SET active=false,tombstone=tombstone OR %s '
                         'WHERE id=ANY(%s)', (delete, documents))
            if delete:
                conn.execute('DELETE FROM chunks WHERE document=ANY(%s)', (documents,))
            conn.execute('UPDATE head SET epoch=epoch+1')
            conn.execute('INSERT INTO events(epoch,action,documents) VALUES (%s,%s,%s)',
                         (epoch+1, 'delete' if delete else 'disable', documents))
        return epoch+1
