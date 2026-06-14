from functools import lru_cache
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_MANIFESTS_DIR = REPO_ROOT / "target-apps" / "manifests"
TARGET_TEMPLATES_DIR = REPO_ROOT / "target-apps" / "task-templates"


class TaskTemplateError(ValueError):
    pass


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_target_manifests() -> dict[str, dict]:
    manifests: dict[str, dict] = {}
    for path in sorted(TARGET_MANIFESTS_DIR.glob("*.yaml")):
        data = _load_yaml(path)
        manifests[data["target_app_id"]] = data
    return manifests


@lru_cache(maxsize=1)
def load_task_templates() -> dict[tuple[str, str], dict]:
    templates: dict[tuple[str, str], dict] = {}
    for path in sorted(TARGET_TEMPLATES_DIR.glob("*.yaml")):
        data = _load_yaml(path)
        target_app_id = data["target_app_id"]
        for profile in data.get("profiles", []):
            key = (target_app_id, profile["target_profile_id"])
            templates[key] = {
                "target_app_id": target_app_id,
                **profile,
            }
    return templates


def get_task_template(target_app_id: str, target_profile_id: str) -> dict:
    template = load_task_templates().get((target_app_id, target_profile_id))
    if not template:
        raise TaskTemplateError(
            f"Unknown task template target_app_id={target_app_id!r}, target_profile_id={target_profile_id!r}."
        )
    return template


def list_task_templates() -> list[dict]:
    manifests = load_target_manifests()
    rows = []
    for template in load_task_templates().values():
        manifest = manifests.get(template["target_app_id"], {})
        rows.append(
            {
                "target_app_id": template["target_app_id"],
                "target_profile_id": template["target_profile_id"],
                "display_name": template["display_name"],
                "description": template["description"],
                "engine": template["engine"],
                "script_path": template["script_path"],
                "target_url": template["target_url"],
                "workload_types": manifest.get("workload_types", []),
                "safe_limits": manifest.get("safe_limits", {}),
            }
        )
    return sorted(rows, key=lambda row: (row["target_app_id"], row["target_profile_id"]))

