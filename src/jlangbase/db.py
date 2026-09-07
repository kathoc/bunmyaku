"""All SQLite access, with explicit transactions and versioned snapshots."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

SCHEMA_VERSION = 1


def now():
    return datetime.now(timezone.utc).isoformat()


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


@contextmanager
def connect(path="data/processed/corpus.sqlite3"):
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        migrate(conn)
        yield conn
    finally:
        conn.close()


def migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise ValueError(f"未対応のDBバージョンです: {version}")
    if version == 0:
        conn.executescript("""
        BEGIN;
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY, collected_at TEXT NOT NULL,
            published_at TEXT, source_type TEXT NOT NULL, platform TEXT,
            topic TEXT, author_type TEXT, edited INTEGER, source_ref TEXT,
            text_hash TEXT UNIQUE NOT NULL, raw_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
            source_type TEXT NOT NULL, analyzer_json TEXT NOT NULL,
            corpus_hash TEXT NOT NULL, result_json TEXT NOT NULL
        );
        CREATE TABLE sentences (
            run_id INTEGER REFERENCES runs(id), document_id INTEGER REFERENCES documents(id),
            position INTEGER, text TEXT NOT NULL,
            PRIMARY KEY (run_id, document_id, position)
        );
        CREATE TABLE tokens (
            run_id INTEGER REFERENCES runs(id), document_id INTEGER REFERENCES documents(id),
            sentence_position INTEGER, position INTEGER, lemma TEXT,
            surface TEXT, pos TEXT, normalized_form TEXT,
            PRIMARY KEY (run_id, document_id, sentence_position, position)
        );
        CREATE TABLE ngrams (
            run_id INTEGER REFERENCES runs(id), document_id INTEGER REFERENCES documents(id),
            kind TEXT, expression TEXT, token_length INTEGER, count INTEGER,
            PRIMARY KEY (run_id, document_id, kind, expression, token_length)
        );
        CREATE TABLE document_metrics (
            run_id INTEGER REFERENCES runs(id), document_id INTEGER REFERENCES documents(id),
            metrics_json TEXT NOT NULL, PRIMARY KEY (run_id, document_id)
        );
        CREATE TABLE expression_stats (
            run_id INTEGER REFERENCES runs(id), kind TEXT, expression TEXT,
            token_length INTEGER, count INTEGER, documents_count INTEGER,
            per_10k_tokens REAL, source_type TEXT, period TEXT,
            PRIMARY KEY (run_id, kind, expression, token_length)
        );
        CREATE TABLE style_profiles (
            id INTEGER PRIMARY KEY, run_id INTEGER REFERENCES runs(id),
            generated_at TEXT NOT NULL, profile_json TEXT NOT NULL
        );
        CREATE INDEX documents_source ON documents(source_type);
        PRAGMA user_version = 1;
        COMMIT;
        """)


def hashes(conn):
    return {row[0] for row in conn.execute("SELECT text_hash FROM documents")}


def insert_document(conn, doc):
    fields = ("collected_at", "published_at", "source_type", "platform", "topic",
              "author_type", "edited", "source_ref")
    values = [doc.get(k) for k in fields]
    values += [text_hash(doc["text"]), doc["text"], encode(doc.get("metadata", {}))]
    with conn:
        cursor = conn.execute("""INSERT INTO documents
            (collected_at,published_at,source_type,platform,topic,author_type,edited,
             source_ref,text_hash,raw_text,metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(text_hash) DO NOTHING""", values)
    return cursor.rowcount == 1


def documents(conn, source_type=None):
    sql = "SELECT * FROM documents"
    rows = conn.execute(sql + " WHERE source_type=? ORDER BY text_hash", (source_type,)) if source_type else conn.execute(sql + " ORDER BY text_hash")
    result = []
    for row in rows:
        doc = dict(row)
        doc["text"] = doc.pop("raw_text")
        doc["metadata"] = json.loads(doc.pop("metadata_json"))
        result.append(doc)
    return result


def save_run(conn, source_type, analyzer, analyzed, result):
    corpus_hash = text_hash(encode(sorted(d["document"]["text_hash"] for d in analyzed)))
    with conn:
        cursor = conn.execute("INSERT INTO runs(created_at,source_type,analyzer_json,corpus_hash,result_json) VALUES(?,?,?,?,?)",
                              (now(), source_type, encode(analyzer), corpus_hash, encode(result)))
        run_id = cursor.lastrowid
        for item in analyzed:
            doc_id = item["document"]["id"]
            conn.execute("INSERT INTO document_metrics VALUES(?,?,?)", (run_id, doc_id, encode(item["metrics"])))
            for i, sentence in enumerate(item["sentences"]):
                conn.execute("INSERT INTO sentences VALUES(?,?,?,?)", (run_id, doc_id, i, sentence["text"]))
                for j, token in enumerate(sentence["tokens"]):
                    conn.execute("INSERT INTO tokens VALUES(?,?,?,?,?,?,?,?)", (run_id, doc_id, i, j,
                                 token["lemma"], token["surface"], token["pos"], token["normalized_form"]))
            for expr in item.get("expressions", []):
                conn.execute("INSERT INTO ngrams VALUES(?,?,?,?,?,?)", (run_id, doc_id, expr["kind"], expr["expression"], expr["token_length"], expr["count"]))
        for expr in result.get("expressions", []):
            conn.execute("INSERT INTO expression_stats VALUES(?,?,?,?,?,?,?,?,?)", (run_id, expr["kind"], expr["expression"], expr["token_length"], expr["count"], expr["documents_count"], expr["per_10k_tokens"], source_type, encode(result["corpus_period"])))
    return run_id


def latest_run(conn, source_type):
    row = conn.execute("SELECT * FROM runs WHERE source_type=? ORDER BY id DESC LIMIT 1", (source_type,)).fetchone()
    if row is None:
        raise ValueError(f"解析結果がありません: {source_type}。先にanalyzeを実行してください")
    return dict(row) | {"result": json.loads(row["result_json"])}


def save_profile(conn, run_id, profile):
    with conn:
        conn.execute("INSERT INTO style_profiles(run_id,generated_at,profile_json) VALUES(?,?,?)",
                     (run_id, profile["generated_at"], encode(profile)))
