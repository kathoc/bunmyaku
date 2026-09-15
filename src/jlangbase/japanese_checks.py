"""Isolated runner for the bundled natural-japanese checks.

The bundled scripts deliberately remain unchanged.  This module owns the
small, per-user virtual environment they need, so installing jlangbase never
changes the Python environment from which its CLI is invoked.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Iterator, Sequence


CHECK_NAMES = frozenset({"lint", "outline", "terms", "semantic"})
DEPENDENCIES = ("SudachiPy==0.6.11", "SudachiDict-core==20260723")
# These are intentionally kept out of DEPENDENCIES.  Invoking ``semantic`` is
# an explicit request for its much larger optional stack (and its model fetch).
SEMANTIC_DEPENDENCIES = (*DEPENDENCIES, "numpy==2.2.6", "sentence-transformers==3.4.1")
PREPARE_TIMEOUT_SECONDS = 180
CHECK_TIMEOUT_SECONDS = 120
LOCK_TIMEOUT_SECONDS = 180


def _cache_dir() -> Path:
    configured = os.environ.get("JLANGBASE_CHECKS_CACHE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "jlangbase" / "natural-japanese-checks"


def _venv_python(cache_dir: Path) -> Path:
    return cache_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _script_path(name: str) -> Path:
    if name not in CHECK_NAMES:
        known = ", ".join(sorted(CHECK_NAMES))
        raise ValueError(f"未知の日本語点検です: {name}（利用可能: {known}）")
    path = Path(__file__).parent / "resources" / "natural-japanese" / "scripts" / f"{name}.py"
    if not path.is_file():
        raise ValueError(f"同梱の点検スクリプトが見つかりません: {path}")
    return path


@contextmanager
def _runtime_lock(cache_dir: Path) -> Iterator[None]:
    """Serialize creation per cache directory without a third-party package."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    lock_path = cache_dir / ".prepare.lock"
    with lock_path.open("a+") as lock:
        if os.name == "nt":  # pragma: no cover - exercised on Windows
            import msvcrt
            lock.write("0")
            lock.flush()
            deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
            while True:
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise ValueError("点検環境の準備ロックを取得できませんでした") from exc
                    time.sleep(0.1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
            while True:
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise ValueError("点検環境の準備ロックを取得できませんでした") from exc
                    time.sleep(0.1)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _run(command: Sequence[str | Path], *, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [str(part) for part in command],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            env=os.environ | {"PYTHONUTF8": "1"},
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        rendered = " ".join(str(part) for part in command[:3])
        raise ValueError(f"処理時間の上限（{timeout}秒）を超えました: {rendered}") from exc
    except OSError as exc:
        raise ValueError(f"点検環境を実行できません: {exc}") from exc


def _is_ready(python: Path, *, semantic: bool = False) -> bool:
    if not python.is_file():
        return False
    imports = (
        "import sudachipy; import sudachidict_core; "
        "from importlib.metadata import version; "
        "assert version('SudachiPy') == '0.6.11'; "
        "assert version('SudachiDict-core') == '20260723'"
    )
    if semantic:
        imports += (
            "; import numpy; import sentence_transformers; "
            "assert version('numpy') == '2.2.6'; "
            "assert version('sentence-transformers') == '3.4.1'"
        )
    try:
        probe = _run(
            [python, "-c", imports],
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except ValueError:
        # A partially created venv can contain a broken interpreter.  It is
        # not ready; _prepare() will repair it with ``venv --upgrade``.
        return False
    return probe.returncode == 0


def _prepare(cache_dir: Path, dependencies: Sequence[str], *, semantic: bool) -> Path:
    """Return a healthy runtime, leaving a failed setup eligible for retry."""
    with _runtime_lock(cache_dir):
        python = _venv_python(cache_dir)
        if _is_ready(python, semantic=semantic):
            return python

        label = "意味点検の任意依存" if semantic else "natural-japanese の点検依存"
        print(f"{label}を専用環境へ導入しています…", file=sys.stderr)
        try:
            pip_ready = python.is_file() and _run(
                [python, "-m", "pip", "--version"], timeout=CHECK_TIMEOUT_SECONDS
            ).returncode == 0
        except ValueError:
            pip_ready = False
        if not pip_ready:
            created = _run(
                [sys.executable, "-m", "venv", "--upgrade", cache_dir], timeout=PREPARE_TIMEOUT_SECONDS
            )
            if created.returncode:
                raise ValueError(_failure_message("仮想環境を作成できません", created))

        installed = _run(
            [python, "-m", "pip", "install", "--disable-pip-version-check", *dependencies],
            timeout=PREPARE_TIMEOUT_SECONDS,
        )
        if installed.returncode:
            raise ValueError(_failure_message(f"{label}を導入できません", installed))
        if not _is_ready(python, semantic=semantic):
            raise ValueError("点検依存の導入後も実行環境を確認できません。次回実行時に再試行します。")
        return python


def _prepare_runtime() -> Path:
    """Prepare only the lightweight dependencies for lint, outline and terms."""
    return _prepare(_cache_dir(), DEPENDENCIES, semantic=False)


def _prepare_semantic_runtime() -> Path:
    """Prepare the explicitly requested, heavyweight semantic checker runtime."""
    return _prepare(_cache_dir() / "semantic", SEMANTIC_DEPENDENCIES, semantic=True)


def _failure_message(prefix: str, result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout).strip()
    return f"{prefix}（終了コード {result.returncode}）" + (f": {detail}" if detail else "")


def run_check(name: str, args: Sequence[str | Path]) -> int:
    """Execute one bundled check and relay its output to this process.

    ``args`` are passed to the original script unchanged.  Asking for help is
    intentionally dependency-free, which keeps shell completion and discovery
    from initiating a network download.
    """
    script = _script_path(name)
    copied_args = [str(arg) for arg in args]
    if any(arg in {"--help", "-h"} for arg in copied_args):
        python = sys.executable
    elif name == "semantic":
        python = _prepare_semantic_runtime()
    else:
        python = _prepare_runtime()
    result = _run([python, script, *copied_args], timeout=CHECK_TIMEOUT_SECONDS)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def analyze_text(text: str) -> dict[str, object]:
    """Run the three normal checks over *text* and return their JSON outputs."""
    if not isinstance(text, str):
        raise ValueError("点検する本文は文字列で指定してください")
    with tempfile.TemporaryDirectory(prefix="jlangbase-japanese-checks-") as directory:
        source = Path(directory) / "article.txt"
        source.write_text(text, encoding="utf-8")
        results: dict[str, object] = {}
        scripts = {name: _script_path(name) for name in ("lint", "outline", "terms")}
        python = _prepare_runtime()
        for name in ("lint", "outline", "terms"):
            result = _run([python, scripts[name], source, "--json"], timeout=CHECK_TIMEOUT_SECONDS)
            if result.returncode:
                raise ValueError(_failure_message(f"{name} 点検に失敗しました", result))
            try:
                results[name] = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{name} 点検のJSON出力を読めません: {exc}") from exc
        return results
