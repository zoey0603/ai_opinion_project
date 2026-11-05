from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='DigestReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tool', models.CharField(max_length=20)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('report_type', models.CharField(choices=[('5_points', '5 點懶人包'), ('professional', '專業分析報告'), ('presentation', '簡報口語稿'), ('student', '給高中生看的版本'), ('social', '社群貼文版')], max_length=30)),
                ('total_count', models.IntegerField(default=0)),
                ('digest_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
