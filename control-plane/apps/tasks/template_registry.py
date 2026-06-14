from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_MANIFESTS_DIR = REPO_ROOT / "target-apps" / "manifests"
TARGET_TEMPLATES_DIR = REPO_ROOT / "target-apps" / "task-templates"
NO_EXACT_EQUIVALENT_GAP = "No exact equivalent profile is currently defined."


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


def _target_coverage_key(target_app_id: str) -> str:
    key = target_app_id
    if key.endswith("-api"):
        key = key[:-4]
    if key.endswith("-flow"):
        key = key[:-5]
    return key.replace("-", "_")


def _profile_coverage_slug(template: dict) -> str:
    target_key = _target_coverage_key(template["target_app_id"]).replace("_", "-")
    profile_id = template["target_profile_id"]
    slug = profile_id
    if slug.startswith(f"{target_key}-"):
        slug = slug[len(target_key) + 1 :]
    for engine_prefix in ("k6-", "jmeter-"):
        if slug.startswith(engine_prefix):
            slug = slug[len(engine_prefix) :]
    return slug.replace("-", "_")


def _coverage_group(template: dict) -> str:
    return f"{_target_coverage_key(template['target_app_id'])}.{_profile_coverage_slug(template)}"


def _coverage_metadata(template: dict, template_index: dict[tuple[str, str], dict]) -> dict:
    equivalent_profile_id = template.get("equivalent_profile_id")
    if not equivalent_profile_id:
        return {
            "coverage_status": "gap",
            "coverage_group": _coverage_group(template),
            "coverage_gap": NO_EXACT_EQUIVALENT_GAP,
        }

    equivalent = template_index.get((template["target_app_id"], equivalent_profile_id))
    if not equivalent:
        return {
            "coverage_status": "gap",
            "coverage_group": _coverage_group(template),
            "coverage_gap": f"Equivalent profile '{equivalent_profile_id}' is not defined for this target app.",
        }
    if equivalent["engine"] == template["engine"]:
        return {
            "coverage_status": "gap",
            "coverage_group": _coverage_group(template),
            "coverage_gap": "Equivalent profile uses the same engine.",
        }
    if equivalent.get("equivalent_profile_id") != template["target_profile_id"]:
        return {
            "coverage_status": "gap",
            "coverage_group": _coverage_group(template),
            "coverage_gap": "Equivalent profile is not reciprocal.",
        }

    return {
        "coverage_status": "exact",
        "coverage_group": _coverage_group(template),
        "coverage_gap": None,
    }


def _template_row(template: dict, manifest: dict, template_index: dict[tuple[str, str], dict]) -> dict:
    return {
        "target_app_id": template["target_app_id"],
        "target_profile_id": template["target_profile_id"],
        "display_name": template["display_name"],
        "description": template["description"],
        "engine": template["engine"],
        "script_path": template["script_path"],
        "target_url": template["target_url"],
        "equivalent_profile_id": template.get("equivalent_profile_id"),
        "workload_types": manifest.get("workload_types", []),
        "safe_limits": manifest.get("safe_limits", {}),
        **_coverage_metadata(template, template_index),
    }


def list_task_templates() -> list[dict]:
    manifests = load_target_manifests()
    template_index = load_task_templates()
    rows = []
    for template in template_index.values():
        manifest = manifests.get(template["target_app_id"], {})
        rows.append(_template_row(template, manifest, template_index))
    return sorted(rows, key=lambda row: (row["target_app_id"], row["target_profile_id"]))


def get_template_coverage_export() -> dict:
    manifests = load_target_manifests()
    profiles = list_task_templates()
    targets_by_id: dict[str, dict] = {}
    grouped_profiles: dict[str, list[dict]] = defaultdict(list)

    for profile in profiles:
        grouped_profiles[profile["target_app_id"]].append(profile)

    for target_app_id, manifest in manifests.items():
        target_profiles = grouped_profiles.get(target_app_id, [])
        targets_by_id[target_app_id] = {
            "target_app_id": target_app_id,
            "display_name": manifest.get("display_name"),
            "protocol": manifest.get("protocol"),
            "base_url": manifest.get("base_url"),
            "workload_types": manifest.get("workload_types", []),
            "profile_count": len(target_profiles),
            "k6_profile_count": sum(1 for profile in target_profiles if profile["engine"] == "k6"),
            "jmeter_profile_count": sum(1 for profile in target_profiles if profile["engine"] == "jmeter"),
            "exact_coverage_profile_count": sum(
                1 for profile in target_profiles if profile["coverage_status"] == "exact"
            ),
            "gap_profile_count": sum(1 for profile in target_profiles if profile["coverage_status"] == "gap"),
        }

    gaps = [
        {
            "target_app_id": profile["target_app_id"],
            "target_profile_id": profile["target_profile_id"],
            "engine": profile["engine"],
            "coverage_group": profile["coverage_group"],
            "coverage_gap": profile["coverage_gap"],
        }
        for profile in profiles
        if profile["coverage_status"] == "gap"
    ]

    return {
        "summary": {
            "target_app_count": len(manifests),
            "profile_count": len(profiles),
            "k6_profile_count": sum(1 for profile in profiles if profile["engine"] == "k6"),
            "jmeter_profile_count": sum(1 for profile in profiles if profile["engine"] == "jmeter"),
            "exact_coverage_profile_count": sum(
                1 for profile in profiles if profile["coverage_status"] == "exact"
            ),
            "gap_profile_count": len(gaps),
        },
        "targets": sorted(targets_by_id.values(), key=lambda row: row["target_app_id"]),
        "profiles": profiles,
        "gaps": gaps,
    }
