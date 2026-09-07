"""CLI orchestration. Analytical modules are reusable without the CLI."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from . import db
from .analysis import Analyzer
from .comparison import compare, write_comparison
from .evaluation import evaluate_versions, load_weights, write_evaluation
from .ingest import ingest, unique_documents
from .profiles import analyze_corpus, build_profile, run_analysis
from .report import write_json, write_profile
from .trends import load_thresholds, time_diff, write_diff
from .experiments import record_experiment
from .craft import reading_map, write_map, write_brief, load_policy
from .reader_study import prepare_study, summarize_study
from .discovery_loop import start, next_request, reflection_request, advance, save_new


def parser():
    root = argparse.ArgumentParser(description="Japanese Language Baseline")
    root.add_argument("--version", action="version", version="0.1.0")
    root.add_argument("--db", default="data/processed/corpus.sqlite3", help="SQLiteファイル")
    commands = root.add_subparsers(dest="command")
    for name in ("ingest", "analyze", "build-profile", "expressions", "compare-human-llm", "evaluate", "diff"):
        command = commands.add_parser(name)
        command.add_argument("--db", default=argparse.SUPPRESS)
        if name in {"ingest", "analyze"}:
            command.add_argument("path", nargs="?" if name == "analyze" else None, type=Path)
            command.add_argument("--platform", default="local")
        if name in {"ingest", "analyze", "build-profile", "expressions", "diff"}:
            command.add_argument("--source-type", "--profile", dest="source_type", default="magazine")
        if name in {"analyze", "compare-human-llm", "evaluate", "diff"}:
            command.add_argument("--backend", choices=["auto", "basic", "sudachi"], default="auto")
        if name in {"analyze", "build-profile", "expressions"}:
            command.add_argument("--top", type=int, default=20)
        if name in {"analyze", "build-profile"}:
            command.add_argument("--compact", action="store_true")
        if name in {"analyze", "build-profile", "compare-human-llm", "evaluate", "diff"}:
            command.add_argument("--out", type=Path, default=Path("output/profile.json") if name == "build-profile" else Path("output"))
        if name == "ingest":
            command.add_argument("--dry-run", action="store_true")
        if name == "analyze":
            command.add_argument("--keep-noise", action="store_true")
        if name == "compare-human-llm":
            command.add_argument("human", nargs="?", type=Path)
            command.add_argument("llm", nargs="?", type=Path)
            command.add_argument("--human-source", "--source-type")
        if name == "evaluate":
            command.add_argument("--reference", required=True, type=Path)
            command.add_argument("--before", required=True, type=Path)
            command.add_argument("--after", required=True, type=Path)
            command.add_argument("--weights", type=Path)
        if name == "diff":
            command.add_argument("--from", dest="date_from", required=True)
            command.add_argument("--to", dest="date_to", required=True)
            command.add_argument("--thresholds", type=Path)
    experiment = commands.add_parser("record-experiment", help="文章の各版と構成の注釈を履歴に保存")
    experiment.add_argument("case", type=Path)
    experiment.add_argument("--backend", choices=["auto", "basic", "sudachi"], default="auto")
    experiment.add_argument("--weights", type=Path)
    craft = commands.add_parser("reading-map", help="段落の順序とひっかかりを分析")
    craft.add_argument("path", type=Path)
    craft.add_argument("--genre", choices=["essay", "explanation", "guide"], default="essay")
    craft.add_argument("--review", type=Path)
    craft.add_argument("--policy", type=Path)
    craft.add_argument("--rhythm-backend", choices=["auto", "basic", "sudachi"], default="auto")
    craft.add_argument("--out", type=Path, default=Path("output/reading-map"))
    brief = commands.add_parser("craft-brief", help="同梱の研究に基づく執筆設計")
    brief.add_argument("--topic", required=True)
    brief.add_argument("--reader", required=True)
    brief.add_argument("--purpose", required=True)
    brief.add_argument("--genre", choices=["essay", "explanation", "guide"], default="essay")
    brief.add_argument("--out", type=Path, default=Path("output/brief"))
    study = commands.add_parser("reader-study", help="版名を伏せた読者比較用の資料")
    study.add_argument("paths", nargs="+", type=Path)
    study.add_argument("--out", required=True, type=Path)
    results = commands.add_parser("reader-results", help="読者の回答を区分して集計")
    results.add_argument("study", type=Path)
    results.add_argument("--responses", required=True, type=Path)
    results.add_argument("--out", type=Path, default=Path("output/reader-results.json"))
    for name in ("loop-start", "loop-request", "loop-step"):
        loop = commands.add_parser(name, help="段落から発見し、認識と未執筆計画を更新")
        loop.add_argument("path", type=Path, help="seedまたはstate JSON")
        loop.add_argument("--out", required=True, type=Path, help="新規JSON。既存ファイルへの上書き不可")
        if name == "loop-request":
            loop.add_argument("--paragraph", type=Path, help="生成後の本文を指定すると発見抽出の要求を出力")
        if name == "loop-step":
            loop.add_argument("--response", required=True, type=Path)
    return root


def corpus(path, label, analyzer):
    return analyze_corpus(unique_documents(path, label), label, analyzer)[1]


def execute(args):
    if args.command in {"loop-start", "loop-request", "loop-step"}:
        state = json.loads(args.path.read_text(encoding="utf-8-sig"))
        if args.command == "loop-start":
            result = start(state)
        elif args.command == "loop-request":
            result = reflection_request(state, args.paragraph.read_text(encoding="utf-8-sig").strip()) if args.paragraph else next_request(state)
        else:
            result = advance(state, json.loads(args.response.read_text(encoding="utf-8-sig")))
        save_new(args.out, result)
        print(f"状態={result.get('status', result.get('stage'))} 出力={args.out}")
        return 0
    if args.command == "reading-map":
        review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
        result = reading_map(args.path.read_text(encoding="utf-8-sig"), args.genre, review, load_policy(args.policy), args.rhythm_backend)
        write_map(args.out, result)
        print(f"段落数={len(result['paragraphs'])} 検討箇所={len(result['findings'])} 出力={args.out}")
        return 0
    if args.command == "craft-brief":
        write_brief(args.out, args.topic, args.reader, args.purpose, args.genre)
        print(f"執筆設計={args.out}")
        return 0
    if args.command == "reader-study":
        print(f"読者比較={prepare_study(args.paths, args.out)}")
        return 0
    if args.command == "reader-results":
        result = summarize_study(args.study, args.responses)
        write_json(args.out, result)
        print(f"人間の回答={result['groups']['human']['reader_count']} モデルの回答={result['groups']['model']['reader_count']}")
        return 0
    if args.command == "record-experiment":
        out = record_experiment(args.case, args.backend, args.weights)
        print(f"改稿記録={out / 'trajectory.md'}")
        return 0
    if hasattr(args, "top") and args.top < 1:
        raise ValueError("--topは1以上で指定してください")
    if args.command == "evaluate":
        analyzer = Analyzer(args.backend)
        result = evaluate_versions(corpus(args.reference, "reference", analyzer), corpus(args.before, "before", analyzer),
                                   corpus(args.after, "after", analyzer), load_weights(args.weights))
        write_evaluation(args.out, result)
        print(f"初稿の距離={result['before']['distance']:.6f} 改稿の距離={result['after']['distance']:.6f}")
        return 0
    # Dry-run must not create a database or its parent directory.
    path = ":memory:" if args.command == "ingest" and args.dry_run and not Path(args.db).exists() else args.db
    if args.command not in {"ingest", "analyze"} and not Path(args.db).exists():
        if args.command != "compare-human-llm" or args.human_source:
            raise ValueError("DBがありません。先にingestまたはanalyzeを実行してください")
        path = ":memory:"
    with db.connect(path) as conn:
        if args.command == "ingest":
            stats = ingest(conn, args.path, args.source_type, args.platform, args.dry_run)
            print(json.dumps(stats, ensure_ascii=False))
            return 1 if stats["failed"] else 0
        if args.command == "analyze":
            failed = 0
            if args.path:
                stats = ingest(conn, args.path, args.source_type, args.platform)
                print(json.dumps(stats, ensure_ascii=False))
                failed = stats["failed"]
            run_id, result = run_analysis(conn, args.source_type, args.backend, not args.keep_noise)
            profile = build_profile(result, args.top, args.compact)
            db.save_profile(conn, run_id, profile)
            write_profile(args.out, profile, args.compact)
            print(f"run_id={run_id} 文書数={profile['document_count']} 出力={args.out}")
            return 1 if failed else 0
        if args.command == "build-profile":
            run = db.latest_run(conn, args.source_type)
            profile = build_profile(run["result"], args.top, args.compact)
            db.save_profile(conn, run["id"], profile)
            write_json(args.out, profile, args.compact)
            print(f"プロファイル出力={args.out}")
        elif args.command == "expressions":
            result = db.latest_run(conn, args.source_type)["result"]
            if not result["analyzer"]["morphology_available"]:
                raise ValueError("表現統計は未計測です。--backend sudachiでanalyzeしてください")
            print(json.dumps(result["expressions"][:args.top], ensure_ascii=False, indent=2))
        elif args.command == "compare-human-llm":
            analyzer = Analyzer(args.backend)
            if args.human_source:
                if args.human and args.llm:
                    raise ValueError("--human-source使用時は比較対象のパスを1つ指定してください")
                llm_path = args.llm or args.human
                if not llm_path:
                    raise ValueError("LLMコーパスのパスを指定してください")
                human = analyze_corpus(db.documents(conn, args.human_source), args.human_source, analyzer)[1]
            else:
                if not args.human or not args.llm:
                    raise ValueError("基準コーパスとLLMコーパスのパスを指定してください")
                human = corpus(args.human, "human", analyzer)
                llm_path = args.llm
            result = compare(human, corpus(llm_path, "llm", analyzer))
            write_comparison(args.out, result)
            print(f"比較結果={args.out}")
        elif args.command == "diff":
            result = time_diff(db.documents(conn, args.source_type), args.source_type, args.date_from, args.date_to,
                               Analyzer(args.backend), load_thresholds(args.thresholds))
            write_diff(args.out, result)
            print(f"期間差分={args.out}")
    return 0


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    if not args.command:
        root.print_help()
        return 0
    try:
        return execute(args)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2
