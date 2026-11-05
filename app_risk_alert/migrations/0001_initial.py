from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='RiskAnalysisResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tool', models.CharField(max_length=20)),
                ('total_count', models.IntegerField(default=0)),
                ('negative_count', models.IntegerField(default=0)),
                ('risk_count', models.IntegerField(default=0)),
                ('risk_score', models.FloatField(default=0)),
                ('risk_level', models.CharField(blank=True, max_length=20)),
                ('main_risk_type', models.CharField(blank=True, max_length=50)),
                ('risk_keywords', models.TextField(blank=True)),
                ('representative_titles', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
