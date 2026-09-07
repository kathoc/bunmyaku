"""Fault-isolated UTF-8 local ingestion. No network access."""
from datetime import datetime, timezone
import json
from pathlib import Path
from . import db

FORMATS = {".txt", ".md", ".jsonl"}
FIELDS = {"text", "collected_at", "published_at", "source_type", "platform",
          "topic", "author_type", "edited", "source_ref"}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("日時はISO 8601文字列で指定してください")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def normalize(record, ref, source_type, platform, collected_at):
    if not isinstance(record, dict) or not isinstance(record.get("text"), str):
        raise ValueError("textを文字列で持つJSONオブジェクトが必要です")
    for field in ("source_type", "platform", "topic", "author_type", "source_ref", "collected_at", "published_at"):
        if record.get(field) is not None and not isinstance(record[field], str):
            raise ValueError(f"{field}は文字列で指定してください")
    result = {k: record.get(k) for k in FIELDS}
    result["source_type"] = record.get("source_type") or source_type
    result["platform"] = record.get("platform") or platform
    result["source_ref"] = record.get("source_ref") or ref
    result["collected_at"] = timestamp(record.get("collected_at") or collected_at)
    result["published_at"] = timestamp(record["published_at"]) if record.get("published_at") else None
    for field in ("source_type", "platform", "topic", "author_type", "source_ref"):
        if result[field] is not None and not isinstance(result[field], str):
            raise ValueError(f"{field}は文字列で指定してください")
    if result["edited"] is not None and not isinstance(result["edited"], bool):
        raise ValueError("editedはtrue/falseで指定してください")
    result["metadata"] = {k: v for k, v in record.items() if k not in FIELDS}
    # Reject NaN/Infinity even when accepted by Python's JSON decoder.
    db.encode(result["metadata"])
    return result


def read_corpus(path, source_type="magazine", platform="local"):
    path = Path(path)
    if not path.exists():
        raise ValueError(f"入力パスがありません: {path}")
    if path.is_file() and path.suffix.lower() not in FORMATS:
        raise ValueError(f"未対応のファイル形式です: {path.suffix}")
    files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in FORMATS) if path.is_dir() else [path]
    stats = dict(processed=0, added=0, duplicates=0, failed=0, empty=0, errors=[])
    docs = []
    collected_at = db.now()
    for file in files:
        try:
            text = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            stats["processed"] += 1
            stats["failed"] += 1
            stats["errors"].append(f"{file}: {exc}")
            continue
        records = text.splitlines() if file.suffix.lower() == ".jsonl" else [None]
        for line_number, line in enumerate(records, 1):
            if line is not None and not line.strip():
                continue
            stats["processed"] += 1
            ref = f"{file.as_posix()}:{line_number}" if line is not None else file.as_posix()
            try:
                record = json.loads(line) if line is not None else {"text": text}
                doc = normalize(record, ref, source_type, platform, collected_at)
                if not doc["text"].strip():
                    stats["empty"] += 1
                    continue
                doc["text_hash"] = db.text_hash(doc["text"])
                docs.append(doc)
            except (ValueError, TypeError) as exc:
                stats["failed"] += 1
                stats["errors"].append(f"{ref}: {exc}")
    return docs, stats


def ingest(conn, path, source_type="magazine", platform="local", dry_run=False):
    docs, stats = read_corpus(path, source_type, platform)
    seen = db.hashes(conn)
    for doc in docs:
        if doc["text_hash"] in seen:
            stats["duplicates"] += 1
        else:
            if dry_run or db.insert_document(conn, doc):
                stats["added"] += 1
            else:
                stats["duplicates"] += 1
            seen.add(doc["text_hash"])
    return stats


def unique_documents(path, source_type="magazine"):
    docs, stats = read_corpus(path, source_type)
    if stats["failed"]:
        raise ValueError("入力の読み込みに失敗しました: " + "; ".join(stats["errors"]))
    unique = {doc["text_hash"]: doc for doc in docs}
    if not unique:
        raise ValueError(f"有効な文書がありません: {path}")
    return [dict(doc, id=i) for i, (_, doc) in enumerate(sorted(unique.items()), 1)]
