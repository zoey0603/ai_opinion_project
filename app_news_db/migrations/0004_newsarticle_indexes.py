from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_news_db', '0003_allow_other_tool'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='newsarticle',
            index=models.Index(fields=['tool', 'date'], name='app_news_db_tool_date_idx'),
        ),
        migrations.AddIndex(
            model_name='newsarticle',
            index=models.Index(fields=['date'], name='app_news_db_date_idx'),
        ),
        migrations.AddIndex(
            model_name='newsarticle',
            index=models.Index(fields=['sentiment'], name='app_news_db_sentiment_idx'),
        ),
    ]
