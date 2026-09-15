import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

import scripts.vendor_natural_japanese as vendor
from jlangbase.distribution import package_files

ROOT = Path(__file__).resolve().parents[1]
VENDORED = ROOT / "src/jlangbase/resources/natural-japanese"


def make_source(tmp_path, monkeypatch, *, symlink=False):
    source = tmp_path / "source"
    skill = source / "skills/natural-japanese"
    shutil.copytree(VENDORED, skill, ignore=shutil.ignore_patterns("provenance.json"))
    (skill / "LICENSE.md").rename(source / "LICENSE")
    if symlink:
        target = skill / "scripts/outline.py"
        target.unlink()
        try:
            target.symlink_to("lint.py")
        except OSError as exc:
            pytest.skip(f"symlink権限がありません: {exc}")
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "initial"], check=True)
    subprocess.run(["git", "-C", str(source), "remote", "add", "origin",
                    "https://github.com/example/natural-japanese.git"], check=True)
    destination = tmp_path / "destination"
    monkeypatch.setattr(vendor, "DEST", destination)
    return source, destination


def run(source, check=False):
    return vendor.sync(source, check)


def hashes(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


def test_idempotence_and_provenance_hashes(tmp_path, monkeypatch):
    source, destination = make_source(tmp_path, monkeypatch)
    assert run(source) == 0
    first = hashes(destination)
    provenance = json.loads((destination / "provenance.json").read_text(encoding="utf-8"))
    assert set(provenance["files"]) == set(first) - {"provenance.json"}
    assert all(provenance["files"][name] == first[name] for name in provenance["files"])
    assert run(source) == 0
    assert hashes(destination) == first


def test_initial_collision_requires_byte_match(tmp_path, monkeypatch):
    source, destination = make_source(tmp_path, monkeypatch)
    destination.mkdir()
    (destination / "SKILL.md").write_text("独自内容", encoding="utf-8")
    with pytest.raises(ValueError, match="同名ファイル"):
        run(source)
    assert (destination / "SKILL.md").read_text(encoding="utf-8") == "独自内容"


def test_pycache_is_ignored(tmp_path, monkeypatch):
    source, destination = make_source(tmp_path, monkeypatch)
    assert run(source) == 0
    cache = destination / "scripts/__pycache__"
    cache.mkdir()
    (cache / "generated.pyc").write_bytes(b"generated")
    assert run(source, check=True) == 0
    assert (cache / "generated.pyc").exists()


def test_dirty_source_is_rejected_without_destination_change(tmp_path, monkeypatch):
    source, destination = make_source(tmp_path, monkeypatch)
    assert run(source) == 0
    before = hashes(destination)
    (source / "LICENSE").write_text("dirty", encoding="utf-8")
    with pytest.raises(ValueError, match="dirty"):
        run(source)
    assert hashes(destination) == before


def test_source_and_destination_symlinks_are_rejected(tmp_path, monkeypatch):
    source, destination = make_source(tmp_path, monkeypatch, symlink=True)
    with pytest.raises(ValueError, match="シンボリックリンク"):
        run(source)
    source, destination = make_source(tmp_path / "dest", monkeypatch)
    assert run(source) == 0
    link = destination / "outside-link"
    try:
        link.symlink_to(destination / "SKILL.md")
    except OSError as exc:
        pytest.skip(f"symlink権限がありません: {exc}")
    try:
        with pytest.raises(ValueError, match="シンボリックリンク"):
            run(source, check=True)
    finally:
        link.unlink()


def test_package_includes_nested_material_and_license(tmp_path):
    package_root = tmp_path / "src/jlangbase"
    resources = package_root / "resources"
    shutil.copytree(VENDORED, resources / "natural-japanese")
    package = package_files(package_root)
    assert "resources/natural-japanese/SKILL.md" in package
    assert "resources/natural-japanese/references/doctypes/report.md" in package
    assert "resources/natural-japanese/LICENSE.md" in package
