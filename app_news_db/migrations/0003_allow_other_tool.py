from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_news_db', '0002_dataupdatelog_fix_sentiment_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='newsarticle',
            name='tool',
            field=models.CharField(choices=[('ChatGPT', 'ChatGPT'), ('Gemini', 'Gemini'), ('Claude', 'Claude'), ('Other', 'Other')], max_length=20),
        ),
    ]
