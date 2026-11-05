from django.db import migrations, models


def mark_existing_reason_sources(apps, schema_editor):
    HotEvent = apps.get_model("app_hot_event", "HotEvent")
    fallback_prefix = "此日聲量上升可能與代表新聞中出現的主題有關"
    for event in HotEvent.objects.all():
        if event.possible_reason.startswith(fallback_prefix):
            event.reason_source = "fallback 已儲存"
        elif event.possible_reason:
            event.reason_source = "Ollama 已儲存"
        else:
            event.reason_source = ""
        event.save(update_fields=["reason_source"])


class Migration(migrations.Migration):

    dependencies = [
        ("app_hot_event", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="hotevent",
            name="reason_source",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.RunPython(mark_existing_reason_sources, migrations.RunPython.noop),
    ]
