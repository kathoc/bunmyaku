"""Portable, explicit installer; no model downloads or global policy edits."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shlex
import shutil
import sys


def digest(data):
    return sha256(data).hexdigest()


def private_root():
    return Path.home() / ".agents" / "memory" / "jlangbase"


def package_files(source):
    """Use portable resource keys regardless of the source filesystem."""
    return {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*")
            if p.is_file() and p.suffix in {".py", ".json", ".md"} and "__pycache__" not in p.parts}


def install(home, selected, update=False, dry_run=False):
    home = Path(home).expanduser().resolve()
    source = Path(__file__).resolve().parent
    package = package_files(source)
    release = digest(b"".join(k.encode() + b"\0" + package[k] for k in sorted(package)))[:20]
    base = home / ".local" / "share" / "jlangbase"
    runtime = base / "releases" / release
    memory = home / ".agents" / "memory" / "jlangbase"
    rules = home / ".agents" / "references" / "jlangbase-writing.md"
    agent_rules = home / ".agents" / "references" / "jlangbase-agent-writing.md"
    launcher = base / "run.py"
    manifest = base / "installation.json"
    old = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    if old and not update:
        raise ValueError("導入済みです。新しい配布物から--updateで更新してください")
    detected = [name for name in ("codex", "claude", "ollama") if shutil.which(name)]
    targets = detected if selected == "auto" else selected.split(",")
    if not targets or not set(targets) <= {"codex", "claude", "ollama"}:
        raise ValueError("ツールを検出できません。--tools codex,claude,ollamaなどで指定してください")
    # Previously installed integrations remain managed during an update.
    targets = sorted(set(targets) | set(old.get("tools", [])))
    files = {runtime / "jlangbase" / name: data for name, data in package.items()}
    files[rules] = package["resources/writing-workflow.md"]
    files[agent_rules] = package["resources/agent-writing.md"]
    runner = ("import sys\nfrom pathlib import Path\n"
              f"sys.path.insert(0, {str(runtime)!r})\n"
              f"import os\nos.environ['JLANGBASE_MEMORY'] = {str(memory)!r}\n"
              "from jlangbase.bundle_cli import main\nraise SystemExit(main())\n")
    files[launcher] = runner.encode("utf-8")
    if os.name == "nt":
        if any(c in str(launcher) + sys.executable for c in '%\r\n"'):
            raise ValueError("Windowsランチャーに安全に使用できないパスです")
        command = home / ".local" / "bin" / "natural-japanese.cmd"
        files[command] = f'@echo off\r\n"{sys.executable}" "{launcher}" %*\r\n'.encode("utf-8")
        invocation = f'& "{sys.executable}" "{launcher}"'
    else:
        command = home / ".local" / "bin" / "natural-japanese"
        files[command] = f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(launcher))} \"$@\"\n".encode()
        invocation = shlex.quote(sys.executable) + " " + shlex.quote(str(launcher))
    skill = (package["resources/writing-skill.md"].decode().replace("__RULES__", str(rules))
             .replace("__AGENT_RULES__", str(agent_rules)))
    locations = []
    if "codex" in targets:
        locations.append(("codex", home / ".agents" / "skills" / "japanese-discovery-writing"))
    if "claude" in targets:
        locations.append(("claude", home / ".claude" / "skills" / "japanese-discovery-writing"))
    usage = (f"# この端末の設定\n\n実行コマンド: `{invocation}`\n\n"
             f"正本: {rules}\n\n個人メモリー索引: {memory / 'INDEX.md'}\n\n"
             "`context`で共通資料と個人履歴の場所を得る。共通研究は返されたresourcesから必要分だけ読む。\n\n"
             "`engine loop-start seed.json --out state-00.json`から始め、`engine loop-request state-00.json --out write-01.json`へ進む。"
             "本文をparagraph-01.txtへ書き、`engine loop-request state-00.json --paragraph paragraph-01.txt --out reflect-01.json`で抽出要求を作る。"
             "応答JSONを作り、`engine loop-step state-00.json --response response-01.json --out state-01.json`で受理する。\n\n"
             "原稿・stateは個人メモリー配下のsessionsに保存し、成果物だけを利用者指定先へ渡す。"
             "修正記録は`feedback record.json`で保存する。必須項目はsymptom,before,after,reason,applicability,origin。"
             "originはuser/model。reader_responseは未取得ならnull。ユーザーが保存を望まない場合は記録しない。\n")
    usage += (f"\n執筆代理の共通手順: {agent_rules}\n\n"
              "新規執筆は`writing-start brief.json --session DIR --host HOST`から始める。"
              "`writing-task DIR --out request.json`で担当への要求を作り、"
              "`writing-submit DIR response.json --agent-id ID`で戻りを提出する。"
              "Ollamaでは`writing-run DIR --model MODEL`が役割別に呼び出す。"
              "完了時だけ`writing-handoff DIR --out manuscript.md`で書き出す。\n")
    dispatch = {
        "codex": "--host codexを指定し、Codexのサブエージェント機能（spawn_agentとfollowup_task等、現在の環境で提供されるもの）で担当を起動・再開する。Claude CLIやOllamaへ依頼しない。",
        "claude": "--host claudeを指定し、Claude Codeのサブエージェント機能（Agent等、現在の環境で提供されるもの）で担当を起動・再開する。Codex CLIやOllamaへ依頼しない。",
    }
    for host, location in locations:
        host_skill = skill.replace("__HOST__", host).replace("__HOST_DISPATCH__", dispatch[host])
        files[location / "SKILL.md"] = host_skill.encode("utf-8")
        files[location / "INSTALLATION.md"] = usage.encode("utf-8")
    # Preflight every managed destination before modifying any of them.
    for path, data in files.items():
        if path.is_symlink():
            raise ValueError(f"シンボリックリンクを上書きしません: {path}")
        if path.exists():
            current = path.read_bytes()
            expected = old.get("files", {}).get(str(path))
            if current != data and (not expected or digest(current) != expected):
                raise ValueError(f"既存または利用者編集のファイルと競合: {path}")
    result = {"release": release, "tools": targets, "detected": detected,
              "command": str(command), "invocation": invocation, "memory": str(memory),
              "files": {str(p): digest(data) for p, data in files.items()}}
    if dry_run:
        return result
    base.mkdir(parents=True, exist_ok=True)
    if old:
        backups = base / "history"
        backups.mkdir(exist_ok=True)
        from uuid import uuid4
        (backups / (uuid4().hex + ".json")).write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".jlangbase-tmp")
        with temporary.open("xb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    if os.name != "nt":
        command.chmod(0o755)
    memory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, text in {
        "INDEX.md": "# 個人メモリー索引\n\n- writing-memory.md: 作文の個人設定と修正履歴の所在。中央へ送信しない。\n",
        "writing-memory.md": "# 日本語執筆の個人メモリー\n\n共通ルールは ~/.agents/references/jlangbase-writing.md。個別訂正はcorrections/*.json、原稿はsessions/へ保存。モデルの提案とユーザーの採用を混同しない。\n"
    }.items():
        path = memory / name
        if not path.exists():
            with path.open("x", encoding="utf-8") as handle:
                handle.write(text)
    for child in ("corrections", "sessions"):
        (memory / child).mkdir(exist_ok=True, mode=0o700)
    agent_memory = memory / "agent-writing-memory.md"
    if not agent_memory.exists():
        with agent_memory.open("x", encoding="utf-8") as handle:
            handle.write("# 執筆代理の使い方\n\n"
                         f"共通手順は {agent_rules}。CodexはCodex、Claude CodeはClaude、OllamaはOllamaへ依頼する。\n\n"
                         "writing-*で執筆、点検、差し戻し、全文編集、最終受理を管理する。"
                         "原稿と判定はsessions内の各セッションに保存し、completeだけを次工程へ渡す。"
                         "モデルの合格と実読者の評価を区別する。\n")
    index = memory / "INDEX.md"
    if "agent-writing-memory.md" not in index.read_text(encoding="utf-8"):
        with index.open("a", encoding="utf-8") as handle:
            handle.write("\n- agent-writing-memory.md: ホストに合わせた執筆委譲と原稿の受理手順。\n")
    temporary = base / "installation.json.tmp"
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, manifest)
    return result


def main():
    parser = argparse.ArgumentParser(description="Codex / Claude Code / Ollama共通の日本語執筆環境")
    parser.add_argument("--home", default=str(Path.home()))
    parser.add_argument("--tools", default="auto", help="auto または codex,claude,ollama")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.home, args.tools, args.update, args.dry_run)
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc))
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False, indent=2))
