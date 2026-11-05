import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from app_news_db.models import NewsArticle

class Command(BaseCommand):
    help = "Import ai_news_ready.csv into NewsArticle database"

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        df = pd.read_csv(csv_path)

        count = 0

        for _, row in df.iterrows():
            date_value = None
            if pd.notna(row.get("date")):
                raw_date = str(row["date"]).strip()
                raw_date = raw_date.replace(" 年 ", "-").replace(" 月 ", "-").replace(" 日 ", " ")
                raw_date = raw_date.replace(" 年", "-").replace(" 月", "-").replace(" 日", "")
                raw_date = raw_date.strip()
                date_value = parse_datetime(raw_date.replace(" ", "T", 1)) or None

            NewsArticle.objects.update_or_create(
                link=str(row["link"]).strip(),
                defaults={
                    "title": str(row.get("title", "")).strip(),
                    "date": date_value,
                    "source": str(row.get("source", "")).strip(),
                    "content": str(row.get("content", "")).strip(),
                    "tool": str(row.get("tool", "")).strip(),
                    "sentiment": str(row.get("sentiment", "")).strip(),
                    "keywords": str(row.get("keywords", "")).strip(),
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"成功匯入 {count} 筆新聞資料"))