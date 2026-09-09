"""Stable project purpose and local task alignment records."""
from hashlib import sha256
from importlib.resources import files


def context():
    content = files("jlangbase").joinpath("resources/project-purpose.md").read_text(encoding="utf-8")
    return {"text": content, "sha256": sha256(content.encode("utf-8")).hexdigest(),
            "scope": "bunmyaku project purpose; do not replace the user's article subject"}


def start_work(value):
    if not isinstance(value, dict):
        raise ValueError("作業の位置づけはobjectです")
    for key in ("task", "contribution", "non_goals"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError("作業記録に必要です: " + key)
    if value.get("area") not in {"generation", "editing", "explanation", "maintenance"}:
        raise ValueError("areaはgeneration/editing/explanation/maintenanceです")
    if value.get("purpose_change", False) is not False:
        raise ValueError("目的変更は通常作業に含めず、利用者に別途確認してください")
    return {"stage": "purpose_alignment", "project_purpose": context(),
            **{key: value[key] for key in ("task", "area", "contribution", "non_goals")},
            "purpose_change": False, "alignment_verified": None}
