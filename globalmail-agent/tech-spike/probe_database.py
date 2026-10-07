"""Creates and removes an isolated, ephemeral PostgreSQL container for smoke checks."""
import json
import secrets
import subprocess
import time
from pathlib import Path
from typing import TypedDict

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import create_engine, text
from probe_support import cleanup_database, run_reported

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'tmp/tech-selection'
IMAGE = 'pgvector/pgvector@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff'
REPORT = Path(__file__).with_name('database-results.json')


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, encoding='utf-8', stderr=subprocess.PIPE).strip()


class State(TypedDict):
    idempotency_key: str
    amount: int
    committed: bool


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(6)
    name = 'globalmail-tech-spike-'+nonce
    password = secrets.token_hex(24)
    env_file = WORK/('db-'+nonce+'.env')
    env_file.write_text('POSTGRES_PASSWORD='+password+'\nPOSTGRES_DB=globalmail_spike\n',encoding='utf-8')
    result = {'scope':'isolated_component_smoke_not_business_runtime','image':IMAGE,'checks':[]}
    container_id = None
    try:
        container_id = docker('run','--detach','--rm','--name',name,'--label','globalmail.tech-spike='+nonce,
            '--memory','1g','--tmpfs','/var/lib/postgresql:rw','--publish','127.0.0.1::5432',
            '--env-file',str(env_file),IMAGE)
        port = docker('port',name,'5432/tcp').rsplit(':',1)[1]
        dsn = f'postgresql://postgres:{password}@127.0.0.1:{port}/globalmail_spike'
        for _ in range(30):
            try:
                with psycopg.connect(dsn,connect_timeout=2) as conn:
                    conn.execute('SELECT 1')
                break
            except psycopg.OperationalError:
                time.sleep(1)
        else:
            raise RuntimeError('Ephemeral database did not become ready')
        with psycopg.connect(dsn,autocommit=True) as conn:
            conn.execute('CREATE EXTENSION vector')
            result['postgresql']=conn.execute('SHOW server_version').fetchone()[0]
            result['pgvector']=conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]
            conn.execute('CREATE TABLE probe_operations (idempotency_key text PRIMARY KEY, amount integer NOT NULL CHECK(amount > 0))')

        def record(name,detail):
            result['checks'].append({'name':name,'passed':True,'detail':detail})
            print(json.dumps(result['checks'][-1]),flush=True)

        engine=create_engine(dsn.replace('postgresql://','postgresql+psycopg://'),pool_pre_ping=True)
        with engine.begin() as conn:
            assert conn.execute(text('SELECT 42')).scalar_one()==42
        engine.dispose()
        record('sqlalchemy_psycopg_connection',{'connected':True})

        app=FastAPI()
        @app.get('/health')
        def health():
            return {'status':'ok'}
        with TestClient(app) as client:
            assert client.get('/health').json()=={'status':'ok'}
        record('fastapi_testclient',{'http_status':200})

        fail_after_commit=[True]
        attempts=[0]
        def commit_operation(state):
            attempts[0]+=1
            with psycopg.connect(dsn) as conn:
                conn.execute('INSERT INTO probe_operations VALUES (%s,%s) ON CONFLICT DO NOTHING',
                             (state['idempotency_key'],state['amount']))
                existing=conn.execute('SELECT amount FROM probe_operations WHERE idempotency_key=%s',
                                      (state['idempotency_key'],)).fetchone()[0]
                assert existing==state['amount']
            if fail_after_commit[0]:
                fail_after_commit[0]=False
                raise RuntimeError('Synthetic crash after business commit, before graph checkpoint')
            return {'committed':True}

        def build(saver):
            builder=StateGraph(State)
            builder.add_node('commit',commit_operation)
            builder.add_edge(START,'commit'); builder.add_edge('commit',END)
            return builder.compile(checkpointer=saver)

        cfg={'configurable':{'thread_id':'synthetic-run-1'}}
        with PostgresSaver.from_conn_string(dsn) as saver:
            saver.setup()
            graph=build(saver)
            try:
                graph.invoke({'idempotency_key':'operation-1','amount':100,'committed':False},cfg)
            except RuntimeError as exc:
                assert str(exc).startswith('Synthetic crash')
            else:
                raise AssertionError('Failure injection did not run')
        # A fresh saver/graph connection reconstructs the unfinished step.
        with PostgresSaver.from_conn_string(dsn) as saver:
            graph=build(saver)
            assert graph.get_state(cfg).next==('commit',)
            assert graph.invoke(None,cfg)['committed'] is True
            assert graph.get_state(cfg).next==()
        with psycopg.connect(dsn) as conn:
            assert conn.execute('SELECT count(*),sum(amount) FROM probe_operations').fetchone()==(1,100)
        assert attempts[0]==2
        record('checkpoint_reconnect_and_idempotent_replay',{'node_attempts':2,'committed_rows':1,
               'scope':'connection recreation; not OS process kill or actual refund implementation'})

        corpus=json.loads((WORK/'retrieval-corpus.json').read_text(encoding='utf-8'))
        embeddings=json.loads((WORK/'embedding-v4-1024.json').read_text(encoding='utf-8'))['vectors']
        query_rows=[json.loads(s) for s in (ROOT/'data/knowledge/v1/evaluation/retrieval-queries.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
        with psycopg.connect(dsn) as conn:
            conn.execute('CREATE TABLE probe_knowledge (document_id text PRIMARY KEY, skus text[] NOT NULL, embedding vector(1024) NOT NULL)')
            for d,v in zip(corpus,embeddings):
                conn.execute('INSERT INTO probe_knowledge VALUES (%s,%s,%s::vector)',(d['id'],d['skus'],json.dumps(v)))
            passed=0
            for n,q in enumerate(query_rows):
                found=[r[0] for r in conn.execute('SELECT document_id FROM probe_knowledge WHERE %s = ANY(skus) ORDER BY embedding <=> %s::vector LIMIT 5',
                       (q['sku'],json.dumps(embeddings[len(corpus)+n]))).fetchall()]
                expected=set(q['expected_document_ids'])
                assert (bool(expected.intersection(found)) if expected else not found)
                assert not set(found).intersection(q['must_exclude'])
                passed+=1
        record('pgvector_real_provider_vectors_scoped_retrieval',{'queries_passed':passed,'dimensions':1024,
               'scope':'developer queries; SKU filter only, production mode/time/split filters still to implement'})
        result['passed']=True
    except Exception as exc:
        result['passed']=False
        result['error_type']=type(exc).__name__
        raise
    finally:
        cleaned=cleanup_database(docker,container_id,nonce,env_file,result)
        REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if not cleaned:
            raise RuntimeError('Temporary resource cleanup incomplete; see result flags')


if __name__=='__main__':
    run_reported(REPORT,main)
