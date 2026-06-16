from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_alter_loadtesttask_target_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskArtifact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("artifact_id", models.CharField(max_length=128)),
                ("kind", models.CharField(choices=[("engine_output", "engine_output"), ("html_report", "html_report"), ("jtl", "jtl"), ("raw_log", "raw_log"), ("stderr", "stderr"), ("stdout", "stdout"), ("summary_json", "summary_json"), ("unknown", "unknown")], max_length=32)),
                ("name", models.CharField(max_length=256)),
                ("state", models.CharField(choices=[("available", "available"), ("expired", "expired"), ("external", "external"), ("missing", "missing"), ("planned", "planned")], max_length=16)),
                ("size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("content_type", models.CharField(blank=True, max_length=128, null=True)),
                ("object_ref", models.CharField(blank=True, max_length=512, null=True)),
                ("storage_backend", models.CharField(blank=True, default="", max_length=64)),
                ("checksum_sha256", models.CharField(blank=True, default="", max_length=128)),
                ("provenance_engine", models.CharField(max_length=16)),
                ("provenance_source", models.CharField(max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("task", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="artifacts", to="tasks.loadtesttask")),
            ],
            options={
                "verbose_name": "任務 Artifact",
                "verbose_name_plural": "任務 Artifacts",
                "ordering": ["artifact_id"],
                "constraints": [models.UniqueConstraint(fields=("task", "artifact_id"), name="unique_task_artifact_id")],
            },
        ),
    ]
