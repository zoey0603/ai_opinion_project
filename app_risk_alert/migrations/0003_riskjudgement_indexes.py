from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_risk_alert', '0002_riskarticlejudgement'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='riskarticlejudgement',
            index=models.Index(fields=['tool', 'is_risk'], name='app_risk_a_tool_is_02cd65_idx'),
        ),
        migrations.AddIndex(
            model_name='riskarticlejudgement',
            index=models.Index(fields=['judged_by'], name='app_risk_a_judged__01931f_idx'),
        ),
        migrations.AddIndex(
            model_name='riskarticlejudgement',
            index=models.Index(fields=['risk_type'], name='app_risk_a_risk_ty_9dac4a_idx'),
        ),
    ]
