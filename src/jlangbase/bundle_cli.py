"""Local writing command. Private history never has an upload operation."""
import argparse
from datetime import datetime, timezone
from importlib.resources import files
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
from .discovery_loop import save_new
from .distribution import private_root


def memory_root():
    return Path(os.environ.get("JLANGBASE_MEMORY", str(private_root())))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "engine":
        from .cli import main as engine_main
        return engine_main(argv[1:])
    parser = argparse.ArgumentParser(description="共通日本語執筆・個人履歴")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("context")
    feedback = sub.add_parser("feedback")
    feedback.add_argument("path", type=Path)
    write = sub.add_parser("ollama-write")
    write.add_argument("title")
    write.add_argument("--seed", required=True, type=Path, help="確認済み事実と初期状態のJSON")
    write.add_argument("--model")
    write.add_argument("--endpoint", default="http://127.0.0.1:11434")
    write.add_argument("--max-steps", type=int, default=8, help="安全上限。目標段落数ではない")
    write.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    try:
        if args.command == "context":
            print(json.dumps({"rules": files("jlangbase").joinpath("resources/writing-workflow.md").read_text(encoding="utf-8"),
                              "resources": str(files("jlangbase").joinpath("resources")),
                              "memory_index": str(memory_root() / "INDEX.md"),
                              "corrections": str(memory_root() / "corrections"),
                              "sessions": str(memory_root() / "sessions")}, ensure_ascii=False, indent=2))
        elif args.command == "feedback":
            record = json.loads(args.path.read_text(encoding="utf-8-sig"))
            required = ("symptom", "before", "after", "reason", "applicability")
            if not isinstance(record, dict) or not all(isinstance(record.get(k), str) and record[k].strip() for k in required):
                raise ValueError("修正記録にはsymptom,before,after,reason,applicabilityが必要です")
            if record.get("origin") not in {"user", "model"}:
                raise ValueError("originはuserまたはmodelです")
            record.setdefault("reader_response", None)
            record["recorded_at"] = datetime.now(timezone.utc).isoformat()
            path = memory_root() / "corrections" / (uuid4().hex + ".json")
            save_new(path, record)
            index = memory_root() / "INDEX.md"
            index.parent.mkdir(parents=True, exist_ok=True)
            with index.open("a", encoding="utf-8") as handle:
                handle.write(f"- corrections/{path.name}: 個人修正 ({record['origin']})\n")
            print(path)
        else:
            from .ollama_writer import write_session
            result = write_session(json.loads(args.seed.read_text(encoding="utf-8-sig")), args.title,
                                   args.model, args.endpoint, args.max_steps, args.timeout, memory_root() / "sessions")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "complete" else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2
    return 0
