from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ClassificationRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=300)),
                ('input_text', models.TextField()),
                ('predicted_tool', models.CharField(blank=True, max_length=20)),
                ('predicted_sentiment', models.CharField(blank=True, max_length=10)),
                ('predicted_topic', models.CharField(blank=True, max_length=40)),
                ('predicted_risk_type', models.CharField(blank=True, max_length=40)),
                ('keywords', models.TextField(blank=True)),
                ('explanation', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
