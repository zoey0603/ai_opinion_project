from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_news_db', '0003_allow_other_tool'),
        ('app_risk_alert', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RiskArticleJudgement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tool', models.CharField(max_length=20)),
                ('matched_keywords', models.TextField(blank=True)),
                ('keyword_risk_types', models.TextField(blank=True)),
                ('is_risk', models.BooleanField(default=False)),
                ('risk_type', models.CharField(blank=True, max_length=50)),
                ('reason', models.TextField(blank=True)),
                ('judged_by', models.CharField(default='ollama', max_length=20)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='risk_judgements', to='app_news_db.newsarticle')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('article', 'tool')},
            },
        ),
    ]
