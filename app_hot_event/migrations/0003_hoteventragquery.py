from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app_hot_event", "0002_hotevent_reason_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="HotEventRAGQuery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=300)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("tool", models.CharField(default="ALL", max_length=20)),
                ("retrieved_context", models.TextField(blank=True)),
                ("stats_text", models.TextField(blank=True)),
                ("answer", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "pending"), ("running", "running"), ("success", "success"), ("failed", "failed")], default="pending", max_length=20)),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-updated_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["status", "updated_at"], name="app_hot_eve_status_6588d2_idx"),
                    models.Index(fields=["tool", "updated_at"], name="app_hot_eve_tool_76dcd6_idx"),
                ],
            },
        ),
    ]
