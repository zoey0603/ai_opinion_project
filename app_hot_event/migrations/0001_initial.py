from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='HotEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tool', models.CharField(max_length=20)),
                ('event_date', models.DateField()),
                ('today_count', models.IntegerField(default=0)),
                ('yesterday_count', models.IntegerField(default=0)),
                ('growth_count', models.IntegerField(default=0)),
                ('growth_rate', models.FloatField(default=0)),
                ('top_keywords', models.TextField(blank=True)),
                ('representative_titles', models.TextField(blank=True)),
                ('possible_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-event_date', '-created_at'],
            },
        ),
    ]
