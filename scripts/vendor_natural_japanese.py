#!/usr/bin/env python3
"""Vendor a clean, pinned natural-japanese skill tree into this repository."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "src" / "jlangbase" / "resources" / "natural-japanese"
LICENSE_NAME = "LICENSE.md"
KEEP_TOP = {"SKILL.md", "assets", "references", "scripts"}
KEEP_SCRIPTS = {"lint.py", "outline.py", "terms.py", "textcore.py", "semantic.py"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files(source: Path) -> dict[str, Path]:
    skill = source / "skills" / "natural-japanese"
    if not skill.is_dir():
        raise ValueError(f"natural-japanese のディレクトリがありません: {skill}")
    files = {"SKILL.md": skill / "SKILL.md", LICENSE_NAME: source / "LICENSE"}
    for path in (skill, source / "LICENSE"):
        if path.is_symlink():
            raise ValueError(f"source にシンボリックリンクがあるため停止します: {path}")
    for path in (skill / "references").rglob("*"):
        if path.is_file():
            if path.is_symlink():
                raise ValueError(f"source にシンボリックリンクがあるため停止します: {path}")
            files[f"references/{path.relative_to(skill / 'references').as_posix()}"] = path
    for path in (skill / "assets").rglob("*"):
        if path.is_file():
            if path.is_symlink():
                raise ValueError(f"source にシンボリックリンクがあるため停止します: {path}")
            files[f"assets/{path.relative_to(skill / 'assets').as_posix()}"] = path
    for name in KEEP_SCRIPTS:
        path = skill / "scripts" / name
        if not path.is_file():
            raise ValueError(f"必要な上流ファイルがありません: {path}")
        if path.is_symlink():
            raise ValueError(f"source にシンボリックリンクがあるため停止します: {path}")
        files[f"scripts/{name}"] = path
    return files


def source_origin(source: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "config", "--get", "remote.origin.url"],
        capture_output=True, text=True, check=False,
    )
    origin = result.stdout.strip()
    if not origin or "@" in origin.split("://", 1)[-1].split("/", 1)[0]:
        raise ValueError("上流 origin がないか、資格情報を含むURLです")
    return origin


def require_clean_source(source: Path) -> None:
    result = subprocess.run(["git", "-C", str(source), "status", "--porcelain"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError("source は git リポジトリである必要があります")
    if result.stdout.strip():
        raise ValueError("上流 source の作業ツリーが dirty です。clean にしてください")


def upstream_commit(source: Path) -> str:
    result = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    if result.returncode or not result.stdout.strip():
        raise ValueError("上流 commit を取得できません")
    return result.stdout.strip()


def destination_files() -> set[str]:
    if not DEST.exists():
        return set()
    for path in DEST.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"destination にシンボリックリンクがあるため停止します: {path}")
    return {p.relative_to(DEST).as_posix() for p in DEST.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts}


def build_provenance(source: Path, files: dict[str, Path], old: dict | None) -> dict:
    hashes = {name: sha256(path) for name, path in sorted(files.items())}
    commit = upstream_commit(source)
    imported_at = (old.get("imported_at") if old
                   and old.get("upstream", {}).get("commit") == commit
                   and old.get("files") == hashes else None)
    return {
        "upstream": {"url": source_origin(source), "commit": commit},
        "files": hashes,
        "excluded": {
            "calibrate.py": "corpus 校正用で通常検査に不要",
            "scripts/fixtures/": "fixture は配布機能に不要",
            "__pycache__/": "生成物",
            "corpus/": "研究用コーパスと実験成果物",
        },
        "imported_at": imported_at or datetime.now(timezone.utc).isoformat(),
        "modified": False,
    }


def sync(source: Path, check: bool) -> int:
    source = source.expanduser().resolve()
    require_clean_source(source)
    files = source_files(source)
    allowed = set(files) | {"provenance.json"}
    unknown = destination_files() - allowed
    if unknown:
        raise ValueError("destination に予期しない独自ファイルがあります: " + ", ".join(sorted(unknown)))
    old = None
    provenance_path = DEST / "provenance.json"
    if provenance_path.exists():
        try:
            old = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"既存 provenance.json を読めません: {exc}") from exc
    if old and isinstance(old.get("files"), dict):
        changed = [name for name, digest in old["files"].items()
                   if not (DEST / name).is_file() or sha256(DEST / name) != digest]
        if changed:
            raise ValueError("destination の同梱ファイルが外部変更されています。削除・上書きせず停止します: "
                             + ", ".join(sorted(changed)))
    if old is None:
        collisions = []
        for name, path in files.items():
            target = DEST / name
            if target.exists() and (not target.is_file() or sha256(target) != sha256(path)):
                collisions.append(name)
        if collisions:
            raise ValueError("初回登録先に内容の異なる同名ファイルがあります。上書きせず停止します: "
                             + ", ".join(sorted(collisions)))
    expected = build_provenance(source, files, old)
    mismatches = []
    for name, path in files.items():
        target = DEST / name
        if not target.is_file() or sha256(target) != expected["files"][name]:
            mismatches.append(name)
    actual_provenance = None
    if provenance_path.exists():
        try:
            actual_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            mismatches.append("provenance.json")
    if actual_provenance != expected:
        mismatches.append("provenance.json")
    if check:
        print(json.dumps({"different": sorted(set(mismatches))}, ensure_ascii=False))
        return 1 if mismatches else 0
    DEST.mkdir(parents=True, exist_ok=True)
    for name, path in files.items():
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    provenance_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"同期しました: {DEST}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="natural-japanese 上流 git リポジトリ（必須）")
    parser.add_argument("--check", action="store_true", help="差分だけ確認し、書き換えない")
    args = parser.parse_args()
    try:
        return sync(args.source, args.check)
    except (OSError, ValueError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
