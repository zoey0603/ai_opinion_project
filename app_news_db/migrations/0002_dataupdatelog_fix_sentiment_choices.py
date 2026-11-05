from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_news_db', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='newsarticle',
            name='sentiment',
            field=models.CharField(blank=True, choices=[('正面', '正面'), ('中性', '中性'), ('負面', '負面')], max_length=10),
        ),
        migrations.CreateModel(
            name='DataUpdateLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='technews_ai', max_length=80)),
                ('last_updated', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('success', 'success'), ('failed', 'failed'), ('skipped', 'skipped')], default='success', max_length=20)),
                ('message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
