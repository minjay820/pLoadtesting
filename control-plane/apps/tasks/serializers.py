"""
apps/tasks/serializers.py
==========================
LoadTestTask 的序列化器：

  LoadTestTaskSerializer        ─ 完整讀（含巢狀 result）
  LoadTestTaskCreateSerializer  ─ 建立任務時使用，強制 status=pending
"""

from rest_framework import serializers

from apps.results.serializers import TestResultSerializer
from .distribution import build_shard_execution_plan, validate_distribution
from .execution import resolve_execution
from .models import LoadTestTask
from .template_registry import TaskTemplateError, get_task_template


class LoadTestTaskSerializer(serializers.ModelSerializer):
    """
    完整的 LoadTestTask 序列化器（GET 回應使用）。

    巢狀嵌入 result：任務尚未完成則為 null，
    完成後帶出所有 TestResult 欄位（含摘要指標）。
    duration_seconds 為唯讀計算屬性（Model property）。
    """

    # 唯讀巢狀序列化：來自 TestResult.task OneToOne related_name="result"
    result = TestResultSerializer(read_only=True, allow_null=True, default=None)

    # 唯讀計算屬性：started_at → finished_at 秒差
    duration_seconds = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model  = LoadTestTask
        fields = [
            "id",
            "name",
            "engine",
            "script_path",
            "parameters",
            "target_url",
            "scheduled_at",
            "started_at",
            "finished_at",
            "duration_seconds",
            "status",
            "worker",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
            "result",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "created_at",
            "updated_at",
            "result",
        ]


class LoadTestTaskCreateSerializer(serializers.ModelSerializer):
    """
    建立任務時使用的序列化器。

    status 強制鎖定為 PENDING，worker / started_at / finished_at
    均不在此設定（由 Control Plane 生命週期管理）。
    """

    target_app_id = serializers.CharField(write_only=True, required=False)
    target_profile_id = serializers.CharField(write_only=True, required=False)
    execution = serializers.JSONField(write_only=True, required=False)
    distribution = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model  = LoadTestTask
        fields = [
            "name",
            "engine",
            "script_path",
            "parameters",
            "target_url",
            "scheduled_at",
            "created_by",
            "target_app_id",
            "target_profile_id",
            "execution",
            "distribution",
        ]
        extra_kwargs = {
            "name":         {"required": False},
            "engine":       {"required": False},
            "script_path":  {"required": False},
            "target_url":   {"required": False},
            "parameters":   {"required": False},
            "scheduled_at": {"required": False},
            "created_by":   {"required": False},
        }

    def validate(self, attrs: dict) -> dict:
        target_app_id = attrs.get("target_app_id")
        target_profile_id = attrs.get("target_profile_id")
        request_execution = attrs.pop("execution", None)
        request_distribution = attrs.pop("distribution", None)
        template_execution = None
        attrs["_target_app_id"] = target_app_id
        attrs["_target_profile_id"] = target_profile_id

        if target_app_id or target_profile_id:
            if not target_app_id or not target_profile_id:
                raise serializers.ValidationError(
                    "target_app_id and target_profile_id must be provided together."
                )
            try:
                template = get_task_template(target_app_id, target_profile_id)
            except TaskTemplateError as exc:
                raise serializers.ValidationError(str(exc)) from exc

            attrs["_resolved_template"] = template
            template_execution = template.get("execution")
            attrs.setdefault("name", template["display_name"])
            attrs.setdefault("engine", template["engine"])
            attrs.setdefault("script_path", template["script_path"])
            attrs.setdefault("target_url", template["target_url"])
            merged_parameters = dict(template.get("parameters", {}))
            merged_parameters.update(attrs.get("parameters") or {})
            merged_parameters["target_url"] = attrs["target_url"]
            attrs["parameters"] = merged_parameters

        required_fields = ("name", "engine", "script_path", "target_url")
        missing = [field for field in required_fields if not attrs.get(field)]
        if missing:
            raise serializers.ValidationError(
                f"Missing required task fields: {', '.join(missing)}."
            )
        parameters = dict(attrs.get("parameters") or {})
        if target_app_id:
            parameters["target_app_id"] = target_app_id
        if target_profile_id:
            parameters["target_profile_id"] = target_profile_id
        execution = resolve_execution(attrs["engine"], template_execution, request_execution)
        if execution is not None:
            parameters["execution"] = execution
        distribution = validate_distribution(request_distribution)
        if distribution is not None:
            parameters["distribution"] = distribution
        attrs["parameters"] = parameters
        return attrs

    def create(self, validated_data: dict) -> LoadTestTask:
        """強制 status=PENDING，確保狀態機從正確起點出發。"""
        validated_data.pop("_resolved_template", None)
        target_app_id = validated_data.pop("_target_app_id", None)
        target_profile_id = validated_data.pop("_target_profile_id", None)
        validated_data.pop("target_app_id", None)
        validated_data.pop("target_profile_id", None)
        validated_data["status"] = LoadTestTask.Status.PENDING
        task = super().create(validated_data)

        parameters = dict(task.parameters or {})
        distribution = parameters.get("distribution")
        if distribution:
            parameters["shard_execution_plan"] = build_shard_execution_plan(
                task_id=str(task.id),
                distribution=distribution,
                execution=parameters.get("execution"),
                engine=task.engine,
                script_path=task.script_path,
                target_url=task.target_url,
                target_app_id=target_app_id,
                target_profile_id=target_profile_id,
            )
            task.parameters = parameters
            task.save(update_fields=["parameters", "updated_at"])
        return task
